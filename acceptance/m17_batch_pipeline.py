import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,tempfile,json
from pipeline.batch import BatchRunner,BatchItem
from contracts import *
from storage import Database,TaskRepository
from pipeline import PaperPipeline
from _pipeline_fixtures import metadata,LocalFetcher
from _pdf_fixtures import materials_pdf
from extractors.composite import CompositeExtractor
from exports import export_results,read_current_failures,is_warning_classification_error


class _ForTestingClassificationExtractor:
    version='classification-batch-for-testing'
    def __init__(self,view=None):self.view=view
    def with_view(self,view):return type(self)(view)
    def extract(self,paper):
        extractor=CompositeExtractor(view=self.view)
        candidate=extractor.extract(paper)
        if paper.paper_id==metadata(2).paper_id:
            candidate=candidate.model_copy(update={'warnings':('missing_field:methods',)})
        return extractor.validate_candidate(paper,candidate)


def case_classification_isolation():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        path=materials_pdf(Path(d)/'full.pdf')
        pipeline=PaperPipeline(db,Path(d)/'cache',LocalFetcher(),extractor=_ForTestingClassificationExtractor())
        items=[BatchItem(str(i),metadata(i),path) for i in (1,2,3)]
        report=asyncio.run(BatchRunner(pipeline).run(items))
        assert report.submitted==3 and report.succeeded==2 and report.failed==1 and report.partial==0
        assert report.records[1].status==ResultStatus.FAILED
        assert report.records[0].status==report.records[2].status==ResultStatus.SUCCESS
        export_results(db,Path(d)/'out')
        failures=[r for r in read_current_failures(Path(d)/'out') if r.paper_id==metadata(2).paper_id]
        assert len(failures)==1 and is_warning_classification_error(failures[0])

class FakePipeline:
    def __init__(self,*,fail=None,delay=.001):self.fail=fail;self.delay=delay;self.active=0;self.maximum=0;self.calls=[]
    async def run(self,reference,**kwargs):
        self.active+=1;self.maximum=max(self.maximum,self.active);self.calls.append(reference)
        try:
            await asyncio.sleep(self.delay)
            if reference==self.fail:raise RuntimeError('one paper failed')
            record=json.loads((Path(__file__).resolve().parents[1]/'samples/m01/01_complete.json').read_text())['cases'][0]['record']
            record['title']=reference
            return validate_record(record).record
        finally:self.active-=1

def case_mixed():
    async def run():
        p=FakePipeline(fail='2');r=await BatchRunner(p,concurrency=2).run([BatchItem(str(i),metadata(i)) for i in range(1,4)])
        assert len(r.records)==3 and len(p.calls)==3 and r.records[1].status==ResultStatus.FAILED and r.succeeded==2 and r.failed==1
    asyncio.run(run())
def case_duplicates():
    async def run():
        p=FakePipeline();r=await BatchRunner(p).run([BatchItem('same',metadata(1)),BatchItem('alias',metadata(1))])
        assert len(p.calls)==1 and r.duplicates==1 and r.submitted==2
    asyncio.run(run())
def case_limits():
    async def run():
        p=FakePipeline(delay=.01);r=await BatchRunner(p,concurrency=2,batch_size=1).run([BatchItem(str(i),metadata(i)) for i in range(1,7)])
        assert p.maximum==2 and len(r.records)==6 and [r.title for r in r.records]==[str(i) for i in range(1,7)]
    asyncio.run(run())
def case_cancel():
    async def run():
        p=FakePipeline(delay=10);task=asyncio.create_task(BatchRunner(p).run([BatchItem('1',metadata())]))
        await asyncio.sleep(.01);task.cancel()
        try:await task
        except asyncio.CancelledError:pass
        else:raise AssertionError('cancel swallowed')
        assert p.active==0
    asyncio.run(run())
def case_restart():
    with tempfile.TemporaryDirectory() as d, Database(Path(d)/'state.db') as db:
        path=materials_pdf(Path(d)/'one.pdf');f=LocalFetcher({1:path});p=PaperPipeline(db,Path(d)/'cache',f)
        items=[BatchItem('2401.00001',metadata(),path)]
        async def run():
            first=await BatchRunner(p).run(items);second=await BatchRunner(p).run(items)
            assert first.records==second.records and first.succeeded==1
        asyncio.run(run())
        assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).attempts==1

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_mixed', 'case_duplicates', 'case_limits', 'case_cancel', 'case_restart','case_classification_isolation'], globals()))
