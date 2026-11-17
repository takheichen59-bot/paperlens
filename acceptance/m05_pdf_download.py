import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,tempfile,httpx
from datetime import datetime,timezone
from fetchers import ArxivFetcher
from fetchers.http_policy import HttpPolicy
from contracts import *
PDF=b'%PDF-1.4\nfixture\n%%EOF'
def meta():return PaperMeta(paper_id='arxiv:../../evil',source_id='2401.00001',doi=None,title='Fixture',page_url='https://arxiv.org/abs/2401.00001',pdf_url='https://arxiv.org/pdf/2401.00001',version='v1',fetched_at=datetime.now(timezone.utc))
async def download(directory,handler,limit=10000):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        return await ArxivFetcher(c,policy=HttpPolicy(interval=0,retries=0),max_pdf_bytes=limit).download(meta(),Path(directory))
def case_valid():
    with tempfile.TemporaryDirectory() as d:
        a=asyncio.run(download(d,lambda r:httpx.Response(200,content=PDF)))
        assert a.pdf_path.parent==Path(d) and a.pdf_path.read_bytes()==PDF and a.bytes==len(PDF)
def case_html():
    with tempfile.TemporaryDirectory() as d:
        try:asyncio.run(download(d,lambda r:httpx.Response(200,content=b'<html>not a pdf</html>')))
        except ContractError as e:assert e.error_kind==ErrorKind.INVALID_DOWNLOAD
        else:raise AssertionError('HTML accepted')
        assert not list(Path(d).glob('*.pdf')) and not list(Path(d).glob('*.part'))
def case_interrupted():
    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'%PDF-1.4';raise httpx.ReadError('interrupted')
    with tempfile.TemporaryDirectory() as d:
        try:asyncio.run(download(d,lambda r:httpx.Response(200,stream=Broken())))
        except ContractError:pass
        else:raise AssertionError('interruption accepted')
        assert not list(Path(d).iterdir())
def case_cache():
    with tempfile.TemporaryDirectory() as d:
        a=asyncio.run(download(d,lambda r:httpx.Response(200,content=PDF)))
        def no_network(r):raise AssertionError('cache requested network')
        b=asyncio.run(download(d,no_network));assert a.content_hash==b.content_hash
        a.pdf_path.write_bytes(b'corrupt')
        c=asyncio.run(download(d,lambda r:httpx.Response(200,content=PDF)));assert c.content_hash==a.content_hash
def case_limit():
    with tempfile.TemporaryDirectory() as d:
        try:asyncio.run(download(d,lambda r:httpx.Response(200,content=PDF),limit=10))
        except ContractError as e:assert e.error_kind==ErrorKind.INVALID_DOWNLOAD
        else:raise AssertionError('oversized accepted')
        assert not list(Path(d).glob('*.pdf'))

def run_size_case(response,limit):
    from storage import Database,TaskRepository
    from pipeline import PaperPipeline
    from pipeline.batch import BatchRunner,BatchItem
    from exports import export_results,read_current_failures,FailureStatus
    from _pipeline_fixtures import metadata
    import json
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:response())) as client:
                fetcher=ArxivFetcher(client,policy=HttpPolicy(interval=0,retries=0),max_pdf_bytes=limit)
                return await BatchRunner(PaperPipeline(db,Path(d)/'cache',fetcher)).run([BatchItem('2401.00001',metadata())])
        report=asyncio.run(run());export=export_results(db,Path(d)/'out')
        records=read_current_failures(Path(d)/'out')
        task=TaskRepository(db).get_current(metadata().paper_id,Stage.DOWNLOAD)
        return report,records,task

def case_size_is_skipped():
    from exports import FailureStatus
    report,records,task=run_size_case(lambda:httpx.Response(200,content=PDF),10)
    assert report.skipped==1 and report.failed==0 and not report.records
    assert task.stage_status==StageStatus.SKIPPED
    assert len(records)==1 and records[0].status==FailureStatus.SKIPPED and records[0].skipped_reason=='size_limit'
    assert records[0].file_bytes==len(PDF)
def case_non_size_stays_failed():
    from exports import FailureStatus
    report,records,task=run_size_case(lambda:httpx.Response(200,content=b'<html>not PDF</html>'),10000)
    assert report.skipped==0 and report.failed==1 and task.stage_status==StageStatus.FAILED
    assert records and all(r.status==FailureStatus.FAILED and r.skipped_reason is None for r in records)

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_valid', 'case_html', 'case_interrupted', 'case_cache', 'case_limit','case_size_is_skipped','case_non_size_stays_failed'], globals()))
