import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,tempfile
from contracts import *
from storage import Database,TaskRepository
from pipeline import PaperPipeline
from _pipeline_fixtures import metadata,LocalFetcher
from _pdf_fixtures import materials_pdf,make_pdf
from unittest.mock import patch
from extractors.composite import CompositeExtractor
from extractors.warning_policy import WarningClassificationError
from exports import export_results,read_current_failures,is_warning_classification_error


class _ForTestingExtractor:
    def __init__(self,exc):self.exc=exc
    version='classification-identity-for-testing'
    def with_view(self,view):return self
    def extract(self,paper):raise self.exc


def case_classification_identity():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'state.db') as db:
        path=materials_pdf(Path(d)/'one.pdf');thrown_exc=WarningClassificationError()
        pipeline=PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path}),extractor=_ForTestingExtractor(thrown_exc))
        with patch.object(pipeline,'_handle_warning_classification_error',wraps=pipeline._handle_warning_classification_error) as spy:
            record=asyncio.run(pipeline.run('2401.00001'))
        assert record.status==ResultStatus.FAILED and spy.call_count==1
        args=spy.call_args.args
        assert id(args[1])==id(thrown_exc) and type(args[1]) is WarningClassificationError
        pid=metadata().paper_id;current=TaskRepository(db).get_current(pid,Stage.EXTRACT)
        assert args[0].task_id==current.task_id and args[0].paper_id==pid and args[0].stage==Stage.EXTRACT
        assert current.stage_status==StageStatus.FAILED and current.error==ErrorKind.VALIDATION_FAILED
        export_results(db,Path(d)/'out')
        failures=[r for r in read_current_failures(Path(d)/'out') if r.paper_id==pid]
        assert len(failures)==1
        assert failures[0].error_kind==ErrorKind.VALIDATION_FAILED and failures[0].reason=='warning_classification_error'
        assert is_warning_classification_error(failures[0])

def case_complete():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'state.db') as db:
        path=materials_pdf(Path(d)/'one.pdf');f=LocalFetcher({1:path})
        r=asyncio.run(PaperPipeline(db,Path(d)/'cache',f).run('2401.00001'))
        assert r.status==ResultStatus.SUCCESS and r.chemicals==('Titanium dioxide',)
        stages=[r[0] for r in db.connection.execute('SELECT stage FROM tasks ORDER BY rowid')]
        assert stages==['download','parse','extract']
def case_download_failure():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'state.db') as db:
        r=asyncio.run(PaperPipeline(db,Path(d)/'cache',LocalFetcher(fail=True)).run('2401.00001'))
        assert r.status==ResultStatus.FAILED and TaskRepository(db).get_current(metadata().paper_id,Stage.DOWNLOAD).stage_status==StageStatus.FAILED
        assert db.connection.execute('SELECT count(*) FROM error_events').fetchone()[0]==1
def case_parse_failure():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'state.db') as db:
        path=Path(d)/'bad.pdf';path.write_bytes(b'corrupt')
        r=asyncio.run(PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path})).run('2401.00001'))
        assert r.status==ResultStatus.FAILED and TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).error==ErrorKind.PDF_CORRUPTED
def case_partial():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'state.db') as db:
        path=materials_pdf(Path(d)/'partial.pdf',conclusion=False)
        r=asyncio.run(PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path})).run('2401.00001'))
        assert r.status==ResultStatus.PARTIAL and not r.conclusions and r.methods
def case_resume():
    with tempfile.TemporaryDirectory() as d:
        path=materials_pdf(Path(d)/'one.pdf');f=LocalFetcher({1:path})
        with Database(Path(d)/'state.db') as db:assert asyncio.run(PaperPipeline(db,Path(d)/'cache',f).run('2401.00001')).status==ResultStatus.SUCCESS
        with Database(Path(d)/'state.db') as db:
            assert asyncio.run(PaperPipeline(db,Path(d)/'cache',f).run('2401.00001')).status==ResultStatus.SUCCESS
            assert f.downloads==1 and TaskRepository(db).get_current(metadata().paper_id,Stage.EXTRACT).attempts==1

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_complete', 'case_download_failure', 'case_parse_failure', 'case_partial', 'case_resume','case_classification_identity'], globals()))
