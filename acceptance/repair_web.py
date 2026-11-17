"""Five offline HTTP scenarios for the installed Python browser adapter."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
import json,tempfile
from urllib.parse import urlencode
from paper_platform.web import WebEngine,handler_for
from contracts import *
from storage import Database,TaskRepository
from exports import read_current_results,read_current_warnings_by_severity,read_current_failures,FailureStatus
from _support import run_cases
from _pdf_fixtures import materials_pdf
from _pipeline_fixtures import LocalFetcher,metadata

@contextmanager
def app(root):
    engine=WebEngine(root);server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(engine))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield engine,server.server_port
    finally:server.shutdown();server.server_close();thread.join()

def call(port,path,method='GET',body=None,headers=None):
    c=HTTPConnection('127.0.0.1',port,timeout=20)
    try:
        c.request(method,path,body=body,headers=headers or {})
        r=c.getresponse();return r.status,r.read()
    finally:c.close()

def upload(port,data,sid='2401.00001'):
    return call(port,'/api/extract?'+urlencode({'arxiv_id':sid,'title':'Synthetic web fixture'}),'POST',data,{'Content-Type':'application/pdf'})

def case_assets_and_status():
    with tempfile.TemporaryDirectory() as d,app(Path(d)/'app') as (e,p):
        status,body=call(p,'/');assert status==200 and 'MatterLens'.encode() in body
        assert json.loads(call(p,'/api/status')[1])['engine']=='python'
        assert len(json.loads(call(p,'/corpus.json')[1])['papers'])==10
        assert call(p,'/../pyproject.toml')[0]==404

def case_pdf_to_contract():
    with tempfile.TemporaryDirectory() as d,app(Path(d)/'app') as (e,p):
        pdf=materials_pdf(Path(d)/'source.pdf');status,body=upload(p,pdf.read_bytes())
        data=json.loads(body);r=data['record']
        assert status==200 and validate_record(r).valid and r['status']=='success'
        assert r['chemicals']==['Titanium dioxide'] and '180 C' in r['methods']
        assert data['version_id'] and not data['warnings']['blocking']
        assert len(read_current_results(e.output))==len(read_current_warnings_by_severity(e.output))==1

def case_failure_isolation_and_repeat():
    with tempfile.TemporaryDirectory() as d,app(Path(d)/'app') as (e,p):
        data=materials_pdf(Path(d)/'source.pdf').read_bytes()
        assert upload(p,data)[0]==200
        failed=json.loads(upload(p,b'not a pdf','2401.00002')[1]);assert failed['record']['status']=='failed'
        assert json.loads(upload(p,data)[1])['record']['status']=='success'
        rows=json.loads(call(p,'/api/results')[1])['papers']
        assert len(rows)==2 and {r['status'] for r in rows}=={'success','failed'}
        with Database(e.root/'state.sqlite3') as db:
            assert TaskRepository(db).get_current(metadata().paper_id,Stage.PARSE).attempts==1

def case_size_skipped():
    with tempfile.TemporaryDirectory() as d,app(Path(d)/'app') as (e,p):
        status,body=call(p,'/api/extract?arxiv_id=2401.00001','POST',b'',{'Content-Type':'application/pdf','Content-Length':str(e.limit+1)})
        assert status==413 and json.loads(body)['skipped_reason']=='size_limit'
        assert not read_current_results(e.output) and not read_current_warnings_by_severity(e.output)
        errors=read_current_failures(e.output)
        assert len(errors)==1 and errors[0].status==FailureStatus.SKIPPED

def case_online_mock_and_offline_gate():
    class VersionedFetcherForTesting(LocalFetcher):
        async def fetch(self,reference):return await super().fetch(reference.split('v',1)[0])
    with tempfile.TemporaryDirectory() as d,app(Path(d)/'app') as (e,p):
        assert call(p,'/api/search?q=materials')[0]==403
        assert call(p,'/api/process?arxiv_id=2401.00001','POST')[0]==403
        e.online=True;pdf=materials_pdf(Path(d)/'source.pdf')
        with patch('paper_platform.web.ArxivFetcher',return_value=VersionedFetcherForTesting({1:pdf})):
            status,body=call(p,'/api/search?q=materials');assert status==200 and len(json.loads(body)['items'])==1
            status,body=call(p,'/api/process?arxiv_id=2401.00001','POST')
            assert status==200 and json.loads(body)['record']['status']=='success'

if __name__=='__main__':
    raise SystemExit(run_cases(['case_assets_and_status','case_pdf_to_contract','case_failure_isolation_and_repeat','case_size_skipped','case_online_mock_and_offline_gate'],globals()))
