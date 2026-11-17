"""Offline SIGKILL/resume integration check; no production test hooks."""
from pathlib import Path
import sys,subprocess,tempfile,time,json,os,signal
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'acceptance')]
from _pdf_fixtures import materials_pdf
from _pipeline_fixtures import metadata
from storage import Database,TaskRepository
from contracts import Stage,StageStatus
from exports import read_current_results
CHILD='''
import sys,asyncio,time
from pathlib import Path
sys.path[:0]=[sys.argv[1]+'/src',sys.argv[1]+'/acceptance']
from parsers.sections import StructuredPDFParser
from storage import Database
from pipeline import PaperPipeline
from _pipeline_fixtures import LocalFetcher,metadata
root=Path(sys.argv[2])
class SlowParserForTesting(StructuredPDFParser):
 def parse_with_view(self,path):
  if Path(path).name=='two.pdf':
   (root/'ready').write_text('second parse running')
   while True:time.sleep(.1)
  return super().parse_with_view(path)
async def run():
 with Database(root/'db') as db:
  p=PaperPipeline(db,root/'cache',LocalFetcher(),parser=SlowParserForTesting())
  await p.run('2401.00001',meta=metadata(1),local_pdf=root/'one.pdf')
  await p.run('2401.00002',meta=metadata(2),local_pdf=root/'two.pdf')
asyncio.run(run())
'''

def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);materials_pdf(root/'one.pdf');materials_pdf(root/'two.pdf',material='Graphene')
        items=[{'reference':metadata(i).source_id,'meta':metadata(i).model_dump(mode='json'),'pdf':name} for i,name in ((1,'one.pdf'),(2,'two.pdf'))]
        manifest=root/'manifest.json';manifest.write_text(json.dumps(items))
        child=subprocess.Popen([sys.executable,'-c',CHILD,str(ROOT),str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+20
            while not (root/'ready').exists():
                if child.poll() is not None:raise AssertionError('Child ended before interruption point')
                if time.monotonic()>deadline:raise AssertionError('Child readiness timeout')
                time.sleep(.05)
            child.kill();child.communicate(timeout=5)
            assert child.returncode!=0
            with Database(root/'db') as db:
                first=TaskRepository(db).get_current(metadata(1).paper_id,Stage.PARSE)
                interrupted=TaskRepository(db).get_current(metadata(2).paper_id,Stage.PARSE)
                assert first.stage_status==StageStatus.SUCCESS and first.attempts==1
                assert interrupted.stage_status==StageStatus.RUNNING and interrupted.attempts==1
            print('PASS actual process killed during second parse; first paper committed')
            r=subprocess.run(
                [sys.executable,'-m','paper_platform','resume','--manifest',str(manifest),'--db',str(root/'db'),'--workdir',str(root/'cache'),'--output',str(root/'results')],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=30)
            assert r.returncode==0,'Resume command failed'
            with Database(root/'db') as db:
                for stage in (Stage.DOWNLOAD,Stage.PARSE,Stage.EXTRACT):
                    assert TaskRepository(db).get_current(metadata(1).paper_id,stage).attempts==1
                assert TaskRepository(db).get_current(metadata(2).paper_id,Stage.PARSE).attempts==2
            rows=read_current_results(root/'results')
            assert len(rows)==2 and all(r.status.value=='success' for r in rows)
            print('PASS resume: both papers success; completed paper download/parse/extract attempts stay 1; interrupted parse attempts 2')
            print('RESUME SUMMARY: 2 passed, 0 failed')
            return 0
        finally:
            if child.poll() is None:child.kill();child.communicate()
if __name__=='__main__':raise SystemExit(main())
