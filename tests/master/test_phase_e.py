import sys,json,tempfile,unittest,os
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from fastapi.testclient import TestClient
from science_platform.api import create_app
from science_platform.models import *
from science_platform.store import Store
from science_platform.parsing import digest

class APITests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.app=create_app(self.tmp.name,start_worker=False);self.client=TestClient(self.app);self.s=self.app.state.store
 def tearDown(self):self.client.close();self.tmp.cleanup()
 def paper(self,pid='p1'):
  r=self.client.post('/api/v1/papers',json={'paper_id':pid,'doi':None,'title':'Minimum cost repair','source_url':'https://example.org','authors':[{'name':'Researcher'}]});self.assertEqual(r.status_code,201,r.text)
 def test_1_upload_parse_job_and_missing_model(self):
  import pymupdf as fitz
  self.paper();pdf=fitz.open();page=pdf.new_page();page.insert_text((72,72),'Methods',fontsize=16);page.insert_text((72,100),'We used solver constraints to calculate optimal repairs.');raw=pdf.tobytes();pdf.close()
  r=self.client.post('/api/v1/papers/p1/document',content=raw,headers={'Content-Type':'application/pdf'});self.assertEqual(r.status_code,201,r.text)
  j=self.client.post('/api/v1/batch',json={'paper_ids':['p1','missing'],'action':'extract'}).json()['job_id'];self.app.state.worker.one()
  result=self.client.get('/api/v1/jobs/'+j).json();self.assertEqual(result['status'],'COMPLETED',result);self.assertEqual(result['result_json']['items']['p1']['status'],'NOT_EXECUTED');self.assertEqual(result['result_json']['items']['missing']['status'],'FAILED')
  detail=self.client.get('/api/v1/papers/p1/detail').json();self.assertTrue(detail['parsed']['segments']);self.assertEqual(detail['extraction']['payload_json']['execution_status'],'NOT_EXECUTED');self.assertEqual(self.client.get('/api/v1/papers/p1/file').status_code,200)
 def test_2_idempotence_pause_resume(self):
  payload={'query':'formal verification','providers':['crossref'],'target':20};a=self.client.post('/api/v1/discovery',json=payload,headers={'Idempotency-Key':'same'});b=self.client.post('/api/v1/discovery',json=payload,headers={'Idempotency-Key':'same'});self.assertEqual(a.json(),b.json());jid=a.json()['job_id']
  self.assertEqual(self.client.post('/api/v1/jobs/'+jid+'/pause').json()['status'],'PAUSED');self.assertEqual(self.client.post('/api/v1/jobs/'+jid+'/resume').json()['status'],'QUEUED')
 def test_3_actual_filter_export_and_venue(self):
  self.paper();self.assertEqual(self.client.get('/api/v1/papers?q=doesnotexist').json()['total'],0);self.assertEqual(self.client.get('/api/v1/papers?q=repair').json()['total'],1)
  for fmt in ['jsonl','csv','xlsx']:
   r=self.client.get('/api/v1/export?format='+fmt);self.assertEqual(r.status_code,200);self.assertTrue(r.content)
  self.assertEqual(self.client.post('/api/v1/venues',json={'name':'My Venue','domain':'AI','aliases':['MV']}).status_code,201);self.assertTrue(any(v['name']=='My Venue' for v in self.client.get('/api/v1/venues').json()))
 def test_4_auth_origin_schema_and_unsafe_upload(self):
  with patch.dict(os.environ,{'PAPERLENS_API_TOKEN':'only-test-value'}):
   self.assertEqual(self.client.get('/api/v1/papers').status_code,401);self.assertEqual(self.client.get('/api/v1/papers',headers={'Authorization':'Bearer only-test-value'}).status_code,200)
  self.assertEqual(self.client.post('/api/v1/papers',json={},headers={'Origin':'https://attacker.example'}).status_code,403);self.assertEqual(self.client.post('/api/v1/discovery',json={'query':'x','target':'20'}).status_code,422)
  self.paper();self.assertEqual(self.client.post('/api/v1/papers/p1/document',content=b'<html>bad</html>',headers={'Content-Type':'application/pdf'}).status_code,422)
 def test_5_hash_change_history_review_conflict(self):
  self.paper();p=Path(self.tmp.name)/'doc.pdf';p.write_bytes(b'a');did=self.s.save_document('p1',digest(p),p,'pdf');r=ScientificRecord(paper_id='p1',document_sha256=digest(p),extraction_version='1',model='fixture',execution_status='EXECUTED');eid=self.s.save_extraction(did,r)
  self.assertEqual(self.client.post('/api/v1/extractions/'+eid+'/review',json={'revision':0,'notes':'verified source only'}).status_code,200);self.assertEqual(self.client.post('/api/v1/extractions/'+eid+'/review',json={'revision':0}).status_code,409)
  p2=Path(self.tmp.name)/'b.pdf';p2.write_bytes(b'b');self.s.save_document('p1',digest(p2),p2,'pdf');d=self.client.get('/api/v1/papers/p1/detail').json();self.assertIsNone(d['extraction']);self.assertEqual(d['history'][0]['status'],'STALE');self.assertEqual(self.client.post('/api/v1/extractions/'+eid+'/review',json={'revision':1}).status_code,409)
if __name__=='__main__':unittest.main(verbosity=2)
