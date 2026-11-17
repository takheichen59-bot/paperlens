"""Serial repositories. No scheduling, extraction or export logic."""
from functools import wraps
from uuid import uuid4
import sqlite3
from contracts import *
from .db import storage_error,timestamp,_paper,_task,_result,_error


def guarded(method):
    @wraps(method)
    def call(*args,**kwargs):
        try:return method(*args,**kwargs)
        except sqlite3.Error as exc:raise storage_error(exc) from exc
    return call


class PaperRepository:
    def __init__(self,db):self.db=db
    @guarded
    def upsert(self,meta:PaperMeta,*,source:Source):
        with self.db.transaction():
            self.db.connection.execute('''INSERT INTO papers VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source,source_id) DO UPDATE SET doi=excluded.doi,title=excluded.title,
            page_url=excluded.page_url,pdf_url=excluded.pdf_url,version=excluded.version,fetched_at=excluded.fetched_at''',
            (meta.paper_id,source.value,meta.source_id,meta.doi,meta.title,meta.page_url,meta.pdf_url,meta.version,timestamp(meta.fetched_at)))
            return self.get_by_source(source,meta.source_id)
    @guarded
    def get(self,paper_id):return _paper(self.db.connection.execute('SELECT * FROM papers WHERE paper_id=?',(paper_id,)).fetchone())
    @guarded
    def get_by_source(self,source,source_id):return _paper(self.db.connection.execute('SELECT * FROM papers WHERE source=? AND source_id=?',(source.value,source_id)).fetchone())


class TaskRepository:
    def __init__(self,db):self.db=db
    @guarded
    def upsert_task(self,task:TaskRecord,*,started_at=None,finished_at=None):
        msg=ContractError(task.stage,task.error,False).safe_message if task.error else None
        with self.db.transaction():
            self.db.connection.execute('''INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(paper_id,stage) DO UPDATE SET stage_status=excluded.stage_status,
            attempts=tasks.attempts+1,config_fingerprint=excluded.config_fingerprint,
            started_at=excluded.started_at,finished_at=excluded.finished_at,
            error_kind=excluded.error_kind,error_safe_message=excluded.error_safe_message''',
            (task.task_id,task.paper_id,task.stage.value,task.stage_status.value,1,task.config_fingerprint,
             timestamp(started_at) if started_at else None,timestamp(finished_at) if finished_at else None,
             task.error.value if task.error else None,msg))
            return self.get_current(task.paper_id,task.stage)
    @guarded
    def get_current(self,paper_id,stage):return _task(self.db.connection.execute('SELECT * FROM tasks WHERE paper_id=? AND stage=?',(paper_id,stage.value)).fetchone())
    @guarded
    def append_stage_run(self,*,run_id,task_id,stage,status,started_at=None,finished_at=None):
        with self.db.transaction():
            self.db.connection.execute('INSERT INTO stage_runs VALUES(?,?,?,?,?,?)',(run_id,task_id,stage.value,status.value,timestamp(started_at) if started_at else None,timestamp(finished_at) if finished_at else None))
        return run_id


class ResultRepository:
    def __init__(self,db):self.db=db
    @guarded
    def upsert(self,paper_id,result:ExtractionResult,*,status:ResultStatus):
        with self.db.transaction():
            self.db.connection.execute('''INSERT INTO extraction_results VALUES(?,?,?,?,?,?)
            ON CONFLICT(paper_id,extraction_method) DO UPDATE SET payload_json=excluded.payload_json,
            status=excluded.status,updated_at=excluded.updated_at''',(str(uuid4()),paper_id,result.extraction_method,result.model_dump_json(),status.value,timestamp()))
            return self.db.connection.execute('SELECT result_id FROM extraction_results WHERE paper_id=? AND extraction_method=?',(paper_id,result.extraction_method)).fetchone()[0]
    @guarded
    def get(self,paper_id,extraction_method):return _result(self.db.connection.execute('SELECT * FROM extraction_results WHERE paper_id=? AND extraction_method=?',(paper_id,extraction_method)).fetchone())


class ErrorRepository:
    def __init__(self,db):self.db=db
    @guarded
    def append(self,error:ContractError,*,paper_id=None):
        safe=error.to_dict();eid=str(uuid4())
        with self.db.transaction():
            self.db.connection.execute('INSERT INTO error_events VALUES(?,?,?,?,?,?,?)',(eid,paper_id,safe['stage'],safe['error_kind'],int(safe['retryable']),safe['safe_message'],timestamp()))
        return eid
    @guarded
    def get(self,event_id):return _error(self.db.connection.execute('SELECT * FROM error_events WHERE event_id=?',(event_id,)).fetchone())
