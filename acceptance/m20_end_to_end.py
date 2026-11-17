import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,json,tempfile,httpx
from contracts import *
from storage import Database,TaskRepository
from fetchers import ArxivFetcher
from fetchers.http_policy import HttpPolicy
from pipeline import PaperPipeline
from pipeline.batch import BatchRunner,BatchItem
from exports import (export_results,FailureStatus,open_current_snapshot,read_current_results,
    read_current_warnings_by_severity,read_current_failures,read_current_review,is_warning_classification_error)
from _pipeline_fixtures import metadata,LocalFetcher
from _pdf_fixtures import materials_pdf,make_pdf
from m03_arxiv_metadata import atom

def results(out):
    with open_current_snapshot(out) as snapshot:
        rows=read_current_results(out,snapshot=snapshot)
        warnings=read_current_warnings_by_severity(out,snapshot=snapshot)
        failures=read_current_failures(out,snapshot=snapshot)
        internal={r.paper_id for r in failures if is_warning_classification_error(r)}
        failed={pid for (pid,_,_,_),r in zip(snapshot.results_index,rows) if r.status==ResultStatus.FAILED}
        print(f'M20 output: version={snapshot.version_id} published_at={snapshot.published_at} informational={sum(len(w.informational) for w in warnings)} blocking={sum(len(w.blocking) for w in warnings)} failed_internal_classification={len(failed & internal)} failed_content_or_processing={len(failed-internal)} skipped={len({f.paper_id for f in failures if f.status==FailureStatus.SKIPPED})}')
        return [r.model_dump(mode='json') for r in rows]

def test_standard_source_to_jsonl():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'state.db') as db:
        pdf=materials_pdf(Path(d)/'source.pdf').read_bytes()
        def source(request):
            if request.url.path=='/api/query':return httpx.Response(200,text=atom([('2401.00001v1','Synthetic source fixture',None)]))
            if request.url.path=='/pdf/2401.00001v1':return httpx.Response(200,content=pdf)
            raise AssertionError('unexpected HTTP request')
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(source)) as client:
                fetcher=ArxivFetcher(client,policy=HttpPolicy(interval=0,retries=0))
                result=await BatchRunner(PaperPipeline(db,Path(d)/'cache',fetcher)).run([BatchItem('2401.00001v1')])
                assert result.succeeded==1 and result.failed==0
        asyncio.run(run());s=export_results(db,Path(d)/'out');r=results(Path(d)/'out')[0]
        assert validate_record(r).valid and r['doi'] is None and r['chemicals']==['Titanium dioxide'] and '180 C' in r['methods']
        assert r['conclusions']=='The coating improved corrosion resistance.'

def test_multicolumn_pdf():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'state.db') as db:
        path=make_pdf(Path(d)/'two.pdf',[[(40,70,'Methods'),(40,110,'Graphene was prepared by deposition.'),(330,70,'Conclusions'),(330,110,'The coating improved resistance.')]])
        p=PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path}))
        r=asyncio.run(p.run('2401.00001'));s=export_results(db,Path(d)/'out')
        assert r.status==ResultStatus.SUCCESS and r.chemicals==('Graphene',) and s.review==1
        assert r.methods.strip()=='Graphene was prepared by deposition.'
        assert r.conclusions.strip()=='The coating improved resistance.'
        assert any('multicolumn' in reason for reason in read_current_review(Path(d)/'out')[0]['reasons'])
        assert results(Path(d)/'out')[0]['status']=='success'
        severity=read_current_warnings_by_severity(Path(d)/'out')[0]
        assert 'page_1_possible_multicolumn' in severity.informational
        assert not severity.blocking

def test_missing_conclusion():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'state.db') as db:
        path=materials_pdf(Path(d)/'partial.pdf',conclusion=False)
        r=asyncio.run(PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path})).run('2401.00001'))
        s=export_results(db,Path(d)/'out');assert r.status==ResultStatus.PARTIAL and r.conclusions=='' and r.methods
        assert read_current_review(Path(d)/'out')[0]['reasons']==['missing_field:conclusions']

def test_image_only_pdf():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'state.db') as db:
        path=make_pdf(Path(d)/'scan.pdf',[[]]);r=asyncio.run(PaperPipeline(db,Path(d)/'cache',LocalFetcher({1:path})).run('2401.00001'))
        s=export_results(db,Path(d)/'out');assert r.status==ResultStatus.FAILED
        assert any(v.error_kind==ErrorKind.NEEDS_OCR for v in read_current_failures(Path(d)/'out'))
        assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).stage_status==StageStatus.FAILED

def test_mixed_failure_and_restart():
    with tempfile.TemporaryDirectory() as d:
        good=materials_pdf(Path(d)/'good.pdf');bad=Path(d)/'bad.pdf';bad.write_bytes(b'bad')
        items=[BatchItem('2401.00001',metadata(1),good),BatchItem('2401.00002',metadata(2),bad)]
        with Database(Path(d)/'state.db') as db:
            report=asyncio.run(BatchRunner(PaperPipeline(db,Path(d)/'cache',LocalFetcher())).run(items))
            assert report.succeeded==1 and report.failed==1 and report.skipped==0
            print(f"M20 mixed: submitted={report.submitted} success={report.succeeded} partial={report.partial} failed={report.failed} skipped={report.skipped}")
            first=export_results(db,Path(d)/'out');assert len(results(Path(d)/'out'))==2
        bad.unlink();materials_pdf(bad,material='Graphene')
        with Database(Path(d)/'state.db') as db:
            report=asyncio.run(BatchRunner(PaperPipeline(db,Path(d)/'cache',LocalFetcher())).run(items))
            assert report.succeeded==2 and report.failed==0
            assert TaskRepository(db).get_current(metadata(1).paper_id,Stage.PARSE).attempts==1
            assert TaskRepository(db).get_current(metadata(2).paper_id,Stage.PARSE).attempts==2
            final=export_results(db,Path(d)/'out');rows=results(Path(d)/'out')
            assert len(rows)==2 and all(validate_record(r).valid for r in rows)
            before=results(Path(d)/'out');export_results(db,Path(d)/'out');assert results(Path(d)/'out')==before

if __name__ == "__main__":
    raise SystemExit(run_cases(['test_standard_source_to_jsonl', 'test_multicolumn_pdf', 'test_missing_conclusion', 'test_image_only_pdf', 'test_mixed_failure_and_restart'], globals()))
