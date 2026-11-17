"""Existing task schema plus atomic versioned sidecar artifacts, no new tables."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
from contracts import *
from storage import TaskRepository
from fetchers.pdf_download import digest_file


def fingerprint(*values):
    return sha256(json.dumps(values,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class ResumeStore:
    def __init__(self,db,root):
        self.db=db;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.tasks=TaskRepository(db)
    def path(self,paper_id,stage):return self.root/(fingerprint(paper_id,stage.value)+'.json')
    def start(self,paper_id,stage,config):
        now=datetime.now(timezone.utc)
        task=TaskRecord(task_id=str(uuid4()),paper_id=paper_id,stage=stage,stage_status=StageStatus.RUNNING,attempts=0,config_fingerprint=config,error=None)
        task=self.tasks.upsert_task(task,started_at=now)
        self.tasks.append_stage_run(run_id=str(uuid4()),task_id=task.task_id,stage=stage,status=StageStatus.RUNNING,started_at=now)
        return task
    def finish(self,paper_id,stage,*,error=None,skipped=False):
        task=self.tasks.get_current(paper_id,stage)
        if task is None:raise ValueError('Stage was not started')
        state=StageStatus.SKIPPED if skipped else StageStatus.FAILED if error else StageStatus.SUCCESS
        now=datetime.now(timezone.utc).isoformat()
        with self.db.transaction():
            self.db.connection.execute('UPDATE tasks SET stage_status=?,finished_at=?,error_kind=?,error_safe_message=? WHERE task_id=?',
                (state.value,now,error.error_kind.value if error else None,error.safe_message if error else None,task.task_id))
            self.tasks.append_stage_run(run_id=str(uuid4()),task_id=task.task_id,stage=stage,status=state,finished_at=datetime.fromisoformat(now))
    def save(self,paper_id,stage,config,value):
        payload=value.model_dump_json()
        envelope={'config':config,'payload':payload,'checksum':sha256(payload.encode()).hexdigest()}
        path=self.path(paper_id,stage);tmp=path.with_suffix('.'+uuid4().hex+'.part')
        try:tmp.write_text(json.dumps(envelope),encoding='utf-8');tmp.replace(path)
        finally:tmp.unlink(missing_ok=True)
    def load(self,paper_id,stage,config,model):
        task=self.tasks.get_current(paper_id,stage)
        if not task or task.stage_status!=StageStatus.SUCCESS or task.config_fingerprint!=config:return None
        try:
            envelope=json.loads(self.path(paper_id,stage).read_text())
            if envelope['config']!=config or sha256(envelope['payload'].encode()).hexdigest()!=envelope['checksum']:return None
            value=model.model_validate_json(envelope['payload'])
            if isinstance(value,DownloadArtifact):
                if not value.pdf_path.is_file() or value.pdf_path.stat().st_size!=value.bytes or digest_file(value.pdf_path)!=value.content_hash:return None
            return value
        except (OSError,ValueError,KeyError,TypeError):return None
    def recover(self,*,before):
        if before.tzinfo is None:raise ValueError('Recovery cutoff requires timezone')
        with self.db.transaction():
            cursor=self.db.connection.execute("UPDATE tasks SET stage_status='pending',finished_at=NULL WHERE stage_status='running' AND (started_at IS NULL OR started_at < ?)",(before.astimezone(timezone.utc).isoformat(),))
        return cursor.rowcount

    def save_parse(self,paper_id,config,paper,view):
        view.validate(paper)
        self.save(paper_id,Stage.PARSE,config,paper)
        path=self.path(paper_id,Stage.PARSE);envelope=json.loads(path.read_text())
        payload=json.dumps(view.to_dict(),sort_keys=True)
        envelope['section_view']=payload;envelope['section_view_checksum']=sha256(payload.encode()).hexdigest()
        tmp=path.with_suffix('.'+uuid4().hex+'.part')
        try:tmp.write_text(json.dumps(envelope));tmp.replace(path)
        finally:tmp.unlink(missing_ok=True)

    def load_parse(self,paper_id,config,*,pdf_hash,parser_version):
        from parsers.sections import SectionView
        paper=self.load(paper_id,Stage.PARSE,config,ParsedPaper)
        if paper is None:return None
        try:
            env=json.loads(self.path(paper_id,Stage.PARSE).read_text())
            payload=env['section_view']
            if sha256(payload.encode()).hexdigest()!=env['section_view_checksum']:return None
            view=SectionView.from_dict(json.loads(payload))
            if view.pdf_hash!=pdf_hash or view.parser_version!=parser_version:return None
            return paper,view.validate(paper)
        except (OSError,ValueError,KeyError,TypeError,AttributeError):return None
