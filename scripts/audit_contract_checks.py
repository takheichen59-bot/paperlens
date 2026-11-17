"""Additional offline audit checks; no contracts or implementation changes."""
import sys,sqlite3,tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'acceptance'))
from _support import run_cases
from m02_storage import meta,task
from m14_extraction_validation import fixture
from storage import Database,PaperRepository,TaskRepository
from contracts import *
from extractors.composite import CompositeExtractor,validate_evidence
from parsers.sections import SectionIdentifier

def check_error(operation):
    try:operation()
    except ContractError as e:
        assert e.stage==Stage.STORAGE and e.error_kind==ErrorKind.VALIDATION_FAILED and e.retryable is False
        assert isinstance(e.cause,sqlite3.IntegrityError)
    else:raise AssertionError('IntegrityError was not wrapped')

def primary_key_wrapping():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'s.db') as db:
        repo=PaperRepository(db);repo.upsert(meta(),source=Source.ARXIV)
        other=meta().model_copy(update={'source_id':'2401.11111'})
        check_error(lambda:repo.upsert(other,source=Source.ARXIV))
        assert repo.get('p1')[0].source_id=='1234.56789'

def foreign_key_wrapping():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'s.db') as db:
        check_error(lambda:TaskRepository(db).upsert_task(task('missing')))
        assert db.connection.execute('SELECT count(*) FROM tasks').fetchone()[0]==0

def check_constraint_wrapping():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'s.db') as db:
        PaperRepository(db).upsert(meta(),source=Source.ARXIV)
        # Deliberately bypass Pydantic to exercise the database constraint boundary.
        invalid=task().model_copy(update={'stage_status':SimpleNamespace(value='illegal_status')})
        check_error(lambda:TaskRepository(db).upsert_task(invalid))
        assert db.connection.execute('SELECT count(*) FROM tasks').fetchone()[0]==0

def same_block_wrong_offsets_rejected():
    p,v=SectionIdentifier().identify_with_view(fixture());r=CompositeExtractor(view=v).extract(p)
    original=next(s for s in r.source_snippets if s.field==ExtractionField.CHEMICALS)
    narrow=original.model_copy(update={'text':'Titanium dioxide','start_offset':1,'end_offset':17})
    replacement=tuple(narrow if s.field==ExtractionField.CHEMICALS else s for s in r.source_snippets)
    try:validate_evidence(p,r.model_copy(update={'source_snippets':replacement}),view=v)
    except ContractError as e:assert e.stage==Stage.VALIDATE
    else:raise AssertionError('wrong offsets accepted')

def wrong_page_rejected():
    p,v=SectionIdentifier().identify_with_view(fixture());r=CompositeExtractor(view=v).extract(p)
    bad=tuple(s.model_copy(update={'page_start':2,'page_end':2}) for s in r.source_snippets)
    try:validate_evidence(p,r.model_copy(update={'source_snippets':bad}),view=v)
    except ContractError as e:assert e.stage==Stage.VALIDATE
    else:raise AssertionError('wrong page accepted')

if __name__=='__main__':
    raise SystemExit(run_cases(['primary_key_wrapping','foreign_key_wrapping','check_constraint_wrapping','same_block_wrong_offsets_rejected','wrong_page_rejected'],globals()))
