"""Validated latest-result snapshots and safe failure/review queues."""
from dataclasses import dataclass
from pathlib import Path
import json,os
from enum import StrEnum
from contracts import *
from extractors.warning_policy import classify_warnings
from .snapshots import publish_generation,record_digest


class FailureStatus(StrEnum):
    FAILED='failed'
    SKIPPED='skipped'

@dataclass(frozen=True)
class FailureRecord:
    status:FailureStatus
    paper_id:str|None
    stage:Stage
    error_kind:ErrorKind
    attempts:int
    skipped_reason:str|None=None
    file_bytes:int|None=None
    file_bytes_source:str|None=None
    event_id:str|None=None
    retryable:bool|None=None
    safe_message:str|None=None
    reason:str|None=None
    limit_bytes:int|None=None
    bytes_received:int|None=None


def parse_failure_line(value:dict)->FailureRecord:
    if type(value)is not dict:raise ValueError('Failure line must be an object')
    status=FailureStatus(value.get('status','failed'))
    pid=value.get('paper_id')
    if pid is not None and not isinstance(pid,str):raise ValueError('Invalid paper ID')
    attempts=value.get('attempts',0)
    if type(attempts)is not int or attempts<0:raise ValueError('Invalid attempts')
    reason=value.get('skipped_reason')
    if status==FailureStatus.SKIPPED and reason!='size_limit':raise ValueError('Skipped reason required')
    if status==FailureStatus.FAILED and reason is not None:raise ValueError('Failed record cannot have skipped reason')
    size=value.get('file_bytes')
    if size is not None and (type(size)is not int or size<0):raise ValueError('Invalid file size')
    stage=Stage(value['stage']);kind=ErrorKind(value.get('error_kind','invalid_download' if status==FailureStatus.SKIPPED else 'unknown'))
    retryable=value.get('retryable')
    if retryable is not None and type(retryable)is not bool:raise ValueError('Invalid retryable')
    message=value.get('safe_message')
    if message is not None and message!=ContractError(stage,kind,False).safe_message:raise ValueError('Uncontrolled error message')
    for key in ('limit_bytes','bytes_received'):
        if value.get(key) is not None and (type(value[key])is not int or value[key]<0):raise ValueError('Invalid byte count')
    if value.get('reason') is not None and type(value['reason']) is not str:raise ValueError('Invalid failure reason')
    return FailureRecord(status,pid,stage,kind,attempts,reason,size,value.get('file_bytes_source'),value.get('event_id'),retryable,message,value.get('reason'),value.get('limit_bytes'),value.get('bytes_received'))


def is_warning_classification_error(record:FailureRecord)->bool:
    return (record.status==FailureStatus.FAILED and record.error_kind==ErrorKind.VALIDATION_FAILED
            and record.reason=='warning_classification_error')


def skip_info_path(db):
    file=db.connection.execute('PRAGMA database_list').fetchone()[2]
    return Path(file+'.skips.json') if file else None


def save_skip_info(db,paper_id,info):
    path=skip_info_path(db)
    if path is None:return
    try:data=json.loads(path.read_text())
    except (OSError,ValueError):data={}
    data[paper_id]=info
    temp=path.with_suffix('.tmp')
    try:temp.write_text(json.dumps(data));os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)


def load_skip_info(db):
    path=skip_info_path(db)
    try:return json.loads(path.read_text()) if path else {}
    except (OSError,ValueError):return {}


@dataclass(frozen=True)
class ExportSummary:
    records:int
    failed:int
    review:int
    results_path:Path
    failures_path:Path
    review_path:Path
    skipped:int=0


def export_results(db,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    records=[];failures=[];reviews=[];seen=set();severity={};classification_ids=set()
    with db.transaction():
        skipped_rows=db.connection.execute("SELECT * FROM tasks WHERE stage='download' AND stage_status='skipped' AND error_kind='invalid_download'").fetchall()
        skipped_ids={r['paper_id'] for r in skipped_rows};skip_info=load_skip_info(db)
        for row in skipped_rows:
            info=skip_info.get(row['paper_id'],{'status':'skipped','skipped_reason':'size_limit','file_bytes':None,'file_bytes_source':'unknown'})
            failures.append({'paper_id':row['paper_id'],'stage':'download','error_kind':'invalid_download','attempts':row['attempts'],**info})
        rows=db.connection.execute('''SELECT r.*,p.doi,p.title,p.page_url FROM extraction_results r
            JOIN papers p ON p.paper_id=r.paper_id ORDER BY r.updated_at DESC,r.rowid DESC''').fetchall()
        for row in rows:
            if row['paper_id'] in seen or row['paper_id'] in skipped_ids:continue
            seen.add(row['paper_id'])
            try:
                value=ExtractionResult.model_validate_json(row['payload_json'])
                record={'doi':row['doi'],'title':row['title'],'source_url':row['page_url'],
                    **{k:value.model_dump(mode='json')[k] for k in ('chemicals','conclusions','methods','extraction_method','source_snippets')},'status':row['status']}
                checked=validate_record(record)
                if not checked.valid:raise ValueError('Invalid stored record')
            except (ValueError,TypeError):
                failures.append({'paper_id':row['paper_id'],'stage':'validate','error_kind':'validation_failed','reason':'invalid_stored_result','attempts':0})
                continue
            records.append((row['paper_id'],checked.record.model_dump(mode='json')))
            severity[row['paper_id']]=classify_warnings(value)
            classification='warning_classification_error' in value.warnings
            if classification:classification_ids.add(row['paper_id'])
            if checked.record.status==ResultStatus.FAILED:
                attempts=db.connection.execute('SELECT COALESCE(MAX(attempts),0) FROM tasks WHERE paper_id=?',(row['paper_id'],)).fetchone()[0]
                if not classification:failures.append({'paper_id':row['paper_id'],'stage':'extract','error_kind':'extract_failed','reason':'no_valid_result','attempts':attempts})
            if checked.record.status==ResultStatus.PARTIAL or value.warnings:
                reviews.append({'paper_id':row['paper_id'],'status':row['status'],'reasons':list(value.warnings) or ['partial_result']})
        events=db.connection.execute('SELECT * FROM error_events ORDER BY created_at,event_id').fetchall()
        last_classification={r['paper_id']:r['event_id'] for r in events if r['paper_id'] in classification_ids and r['stage']=='validate' and r['error_kind']=='validation_failed'}
        for row in events:
            if row['paper_id'] in skipped_ids:continue
            safe=ContractError(Stage(row['stage']),ErrorKind(row['error_kind']),bool(row['retryable'])).to_dict()
            count=db.connection.execute('SELECT COALESCE(MAX(attempts),0) FROM tasks WHERE paper_id=? AND stage=?',(row['paper_id'],row['stage'])).fetchone()[0]
            entry={'event_id':row['event_id'],'paper_id':row['paper_id'],**safe,'attempts':count}
            if last_classification.get(row['paper_id'])==row['event_id']:entry['reason']='warning_classification_error'
            failures.append(entry)
        for pid in classification_ids-set(last_classification):
            failures.append({'paper_id':pid,'stage':'validate','error_kind':'validation_failed','reason':'warning_classification_error','attempts':0})
    for row in failures:
        row.setdefault('status','failed');parse_failure_line(row)
    ordered=sorted(records);identities=[];severity_rows=[]
    for i,(pid,value) in enumerate(ordered):
        digest=record_digest(value);messages=severity[pid]
        identities.append([pid,i,digest,value['status']])
        severity_rows.append({'paper_id':pid,'result_index':i,'result_sha256':digest,'status':value['status'],
            'informational':list(messages.informational),'blocking':list(messages.blocking)})
    generation=publish_generation(destination,{'results.jsonl':[value for _,value in ordered],
        'failures.jsonl':failures,'review.jsonl':sorted(reviews,key=lambda r:r['paper_id']),
        'warnings_by_severity.jsonl':severity_rows},identities)
    paths=[generation/'results.jsonl',generation/'failures.jsonl',generation/'review.jsonl']
    return ExportSummary(len(records),sum(parse_failure_line(r).status==FailureStatus.FAILED for r in failures),len(reviews),*paths,skipped=len(skipped_rows))
