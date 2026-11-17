import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import json, sqlite3, tempfile
from datetime import datetime, timezone
from storage import Database, PaperRepository, TaskRepository, ResultRepository, ErrorRepository
from contracts import *

def meta(pid='p1',title='First'):
    return PaperMeta(paper_id=pid,source_id='1234.56789',doi=None,title=title,page_url='https://arxiv.org/abs/1234.56789',pdf_url='https://arxiv.org/pdf/1234.56789',version='v1',fetched_at=datetime.now(timezone.utc))
def task(pid='p1',tid='t1'):
    return TaskRecord(task_id=tid,paper_id=pid,stage=Stage.PARSE,stage_status=StageStatus.RUNNING,attempts=0,config_fingerprint='a'*64,error=None)
def case_first_write():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'a.db') as db:
        p,s=PaperRepository(db).upsert(meta(),source=Source.ARXIV)
        assert p==PaperRepository(db).get('p1')[0] and s==Source.ARXIV
        t=TaskRepository(db).upsert_task(task());assert t.attempts==1
        assert TaskRepository(db).get_current('p1',Stage.PARSE)==t
        TaskRepository(db).append_stage_run(run_id='r1',task_id=t.task_id,stage=t.stage,status=t.stage_status)
        r=ExtractionResult(chemicals=(),conclusions='',methods='',extraction_method='test-v1',source_snippets=(),field_status=tuple((f,FieldStatus.MISSING) for f in ExtractionField),warnings=())
        ResultRepository(db).upsert('p1',r,status=ResultStatus.FAILED)
        assert ResultRepository(db).get('p1','test-v1')==(r,ResultStatus.FAILED)
        e=ContractError(Stage.PARSE,ErrorKind.PARSE_FAILED,False,cause=ValueError('secret'))
        er=ErrorRepository(db);a=er.append(e,paper_id='p1');b=er.append(e,paper_id='p1')
        assert a!=b and er.get(a).cause is None and 'secret' not in json.dumps(er.get(a).to_dict())
def case_upserts():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'a.db') as db:
        repo=PaperRepository(db);repo.upsert(meta(),source=Source.ARXIV)
        p,_=repo.upsert(meta('different','Updated'),source=Source.ARXIV)
        assert p.paper_id=='p1' and p.title=='Updated' and db.connection.execute('SELECT count(*) FROM papers').fetchone()[0]==1
        tr=TaskRepository(db);tr.upsert_task(task());t=tr.upsert_task(task(tid='new'))
        assert t.task_id=='t1' and t.attempts==2
        r=ExtractionResult(chemicals=(),conclusions='',methods='',extraction_method='test',source_snippets=(),field_status=tuple((f,FieldStatus.MISSING) for f in ExtractionField),warnings=())
        rr=ResultRepository(db);rid=rr.upsert('p1',r,status=ResultStatus.FAILED)
        newer=r.model_copy(update={'warnings':('updated',)})
        assert rr.upsert('p1',newer,status=ResultStatus.FAILED)==rid and rr.get('p1','test')[0]==newer
        tr.append_stage_run(run_id='r',task_id='t1',stage=Stage.PARSE,status=StageStatus.SUCCESS)
        try:tr.append_stage_run(run_id='r',task_id='t1',stage=Stage.PARSE,status=StageStatus.SUCCESS)
        except ContractError as e:assert e.stage==Stage.STORAGE
        else:raise AssertionError('duplicate run accepted')
def case_rollback():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'a.db') as db:
        marker=RuntimeError('caller')
        try:
            with db.transaction():
                PaperRepository(db).upsert(meta(),source=Source.ARXIV)
                TaskRepository(db).upsert_task(task())
                raise marker
        except RuntimeError as e:assert e is marker
        assert PaperRepository(db).get('p1') is None
        assert db.connection.execute('SELECT count(*) FROM tasks').fetchone()[0]==0
        with db.transaction():
            PaperRepository(db).upsert(meta(),source=Source.ARXIV)
            try:
                with db.transaction():
                    TaskRepository(db).upsert_task(task());raise ValueError('inner')
            except ValueError:pass
        assert PaperRepository(db).get('p1') is not None
        assert TaskRepository(db).get_current('p1',Stage.PARSE) is None
        try:TaskRepository(db).upsert_task(task('missing'))
        except ContractError as e:assert e.stage==Stage.STORAGE and e.error_kind==ErrorKind.VALIDATION_FAILED and not e.retryable
        else:raise AssertionError('FK accepted')
def case_reopen():
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'a.db'
        with Database(path) as db:
            PaperRepository(db).upsert(meta(),source=Source.ARXIV);TaskRepository(db).upsert_task(task())
        with Database(path) as db:
            assert db.user_version==1 and TaskRepository(db).get_current('p1',Stage.PARSE).attempts==1
            assert db.connection.execute('PRAGMA foreign_keys').fetchone()[0]==1
            assert db.connection.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
            assert db.connection.execute('PRAGMA busy_timeout').fetchone()[0]==5000
def case_migration():
    import shutil
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'old.db';sqlite3.connect(path).close()
        with Database(path,auto_migrate=False) as db:
            assert db.user_version==0;db.migrate();db.migrate();assert db.user_version==1
            scripts=Path(d)/'migrations';scripts.mkdir()
            original=Path(__file__).resolve().parents[1]/'src/storage/migrations/0001_init.sql'
            shutil.copyfile(original,scripts/original.name)
            (scripts/'0002_broken.sql').write_text('CREATE TABLE transient_test (id INTEGER);\nINSERT INTO absent_table VALUES (1);\n')
            try:db.migrate(migrations_dir=scripts)
            except ContractError as e:assert e.stage==Stage.STORAGE and e.error_kind==ErrorKind.VALIDATION_FAILED
            else:raise AssertionError('broken migration passed')
            assert db.user_version==1
            names={r[0] for r in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            assert 'papers' in names and 'transient_test' not in names
            for invalid in ("SELECT 'x;y';\n",'CREATE TRIGGER t AFTER INSERT ON papers BEGIN SELECT 1; END;\n','/* bad */ SELECT 1;\n','PRAGMA user_version=9;\n','SELECT 1;'):
                (scripts/'0002_broken.sql').write_text(invalid)
                try:db.migrate(migrations_dir=scripts)
                except ContractError:pass
                else:raise AssertionError('invalid format accepted')

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_first_write', 'case_upserts', 'case_rollback', 'case_reopen', 'case_migration'], globals()))
