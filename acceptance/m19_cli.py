import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from exports import read_current_results
import json,tempfile
from unittest.mock import patch
from typer.testing import CliRunner
from paper_platform.cli import app
from _pdf_fixtures import materials_pdf
from _pipeline_fixtures import metadata,LocalFetcher
from storage import Database,TaskRepository
from contracts import Stage
runner=CliRunner()

def args(d):return ['--db',str(Path(d)/'state.db'),'--workdir',str(Path(d)/'cache'),'--output',str(Path(d)/'out')]
def manifest(d,partial=False):
    rows=[]
    for i in range(1,3 if partial else 2):
        path=materials_pdf(Path(d)/f'{i}.pdf',conclusion=not(partial and i==2))
        rows.append({'reference':metadata(i).source_id,'meta':metadata(i).model_dump(mode='json'),'pdf':path.name})
    p=Path(d)/'manifest.json';p.write_text(json.dumps(rows));return p

def case_single():
    with tempfile.TemporaryDirectory() as d:
        pdf=materials_pdf(Path(d)/'one.pdf')
        result=runner.invoke(app,['run','--arxiv-id','2401.00001','--pdf',str(pdf),*args(d)])
        assert result.exit_code==0,result.output
        assert list(read_current_results(Path(d)/'out')[0].chemicals)==['Titanium dioxide']
        assert runner.invoke(app,['status','--db',str(Path(d)/'state.db')]).exit_code==0
        assert runner.invoke(app,['export','--db',str(Path(d)/'state.db'),'--output',str(Path(d)/'other')]).exit_code==0

def case_search():
    with patch('paper_platform.cli.ArxivFetcher',return_value=LocalFetcher({1:Path('unused')})):
        result=runner.invoke(app,['search','materials','--online','--max-results','1'])
        assert result.exit_code==0 and json.loads(result.output)['source_id']=='2401.00001'
    assert runner.invoke(app,['search','materials']).exit_code==1

def case_resume():
    with tempfile.TemporaryDirectory() as d:
        m=manifest(d)
        assert runner.invoke(app,['run','--manifest',str(m),*args(d)]).exit_code==0
        assert runner.invoke(app,['resume','--manifest',str(m),*args(d)]).exit_code==0
        with Database(Path(d)/'state.db') as db:assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).attempts==1
        retry=runner.invoke(app,['retry-failed','--manifest',str(m),*args(d)])
        assert retry.exit_code==0 and '"submitted": 0' in retry.output

def case_invalid_parameters():
    with tempfile.TemporaryDirectory() as d:
        assert runner.invoke(app,['run','--concurrency','0',*args(d)]).exit_code==2
        assert not (Path(d)/'state.db').exists()
        assert runner.invoke(app,['--help']).exit_code==0
        from paper_platform.cli import limits_from_config
        config=Path(d)/'limits.toml';config.write_text('[download]\nmax_pdf_mib=20\n[extraction]\nmethods_max_chars=1200\n')
        assert limits_from_config(config,None,None)==(20,1200)
        assert limits_from_config(config,100,3000)==(100,3000)

def case_partial_batch():
    with tempfile.TemporaryDirectory() as d:
        m=manifest(d,True);result=runner.invoke(app,['run','--manifest',str(m),*args(d)])
        assert result.exit_code==3,result.output
        data=json.loads(result.output);assert data['success']==1 and data['partial']==1 and data['failed']==0

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_single', 'case_search', 'case_resume', 'case_invalid_parameters', 'case_partial_batch'], globals()))
