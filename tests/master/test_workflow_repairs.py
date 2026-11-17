"""Regression checks for observed UI workflow failures; no scientific-quality claims."""
import csv,io,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from fastapi.testclient import TestClient
import pymupdf as fitz
from science_platform.api import create_app
from science_platform.models import ScientificRecord
from science_platform.parsing import digest

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=create_app(self.tmp.name,start_worker=False);self.client=TestClient(self.app);self.store=self.app.state.store
 def tearDown(self):self.client.close();self.tmp.cleanup()
 def add(self,pid,doi=None):
  r=self.client.post('/api/v1/papers',json={'paper_id':pid,'doi':doi,'title':'Engineering fixture '+pid,'source_url':''});self.assertEqual(r.status_code,201,r.text);return r.json()
 def pdf(self,text='Engineering fixture'):
  d=fitz.open();p=d.new_page();p.insert_text((72,72),text);out=d.tobytes();d.close();return out
 def upload(self,pid,raw):return self.client.post('/api/v1/papers/'+pid+'/document',content=raw,headers={'Content-Type':'application/pdf'})
 def test_01_doi_upsert_returns_canonical_id(self):
  self.add('canonical','10.1234/example');p=self.add('new-upload','https://doi.org/10.1234/EXAMPLE');self.assertEqual(p['paper_id'],'canonical');self.assertEqual(self.upload(p['paper_id'],self.pdf()).status_code,201);self.assertEqual(self.store.count(),1)
 def test_02_invalid_doi_safe_error(self):
  r=self.client.post('/api/v1/papers',json={'paper_id':'x','doi':'invalid DOI','title':'x','source_url':''});self.assertEqual(r.status_code,422);self.assertEqual(self.store.count(),0)
 def test_03_failed_batch_retry_keeps_success_checkpoint(self):
  self.add('good');self.upload('good',self.pdf());jid=self.client.post('/api/v1/batch',json={'paper_ids':['good','later'],'action':'parse'}).json()['job_id'];self.app.state.worker.one()
  first=json.loads(self.store.job(jid)['result_json']);self.assertEqual(first['items']['later']['status'],'FAILED');self.assertEqual(first['items']['good']['status'],'PARSED')
  self.add('later');self.upload('later',self.pdf('Second fixture'));r=self.client.post('/api/v1/jobs/'+jid+'/resume');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['progress'],1);self.assertNotIn('later',r.json()['result_json']['items'])
  self.app.state.worker.one();after=json.loads(self.store.job(jid)['result_json']);self.assertEqual(after['items']['good'],first['items']['good']);self.assertEqual(after['counts'],{'PARSED':2})
  with self.store.connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM parses').fetchone()[0],2)
 def test_04_completed_good_job_not_requeued(self):
  self.add('p');self.upload('p',self.pdf());jid=self.client.post('/api/v1/batch',json={'paper_ids':['p'],'action':'acquire'}).json()['job_id'];self.app.state.worker.one();self.assertEqual(self.client.post('/api/v1/jobs/'+jid+'/resume').status_code,422)
 def test_05_export_selection_and_default_all(self):
  for pid in ['p1','p2','p3']:self.add(pid)
  one=self.client.get('/api/v1/export',params={'paper_id':'p2'});self.assertEqual(one.status_code,200);self.assertEqual([json.loads(x)['paper']['paper_id'] for x in one.text.splitlines()],['p2']);self.assertEqual(len(self.client.get('/api/v1/export').text.splitlines()),3)
 def test_06_unknown_or_empty_selection_not_entire_library(self):
  self.add('p');self.assertEqual(self.client.get('/api/v1/export',params={'paper_id':'missing'}).status_code,422);self.assertEqual(self.client.get('/api/v1/export',params={'paper_id':''}).status_code,422)
 def test_07_review_survives_all_export_formats(self):
  self.add('p');self.upload('p',self.pdf());doc=self.store.document(self.store.paper('p')['current_document']);eid=self.store.save_extraction(doc['document_id'],ScientificRecord(paper_id='p',document_sha256=doc['sha256'],extraction_version='fixture',model='NO_MODEL',execution_status='NOT_EXECUTED'));self.client.post('/api/v1/extractions/'+eid+'/review',json={'revision':0,'confirmed':True,'notes':'Manual engineering note'})
  row=json.loads(self.client.get('/api/v1/export').text);self.assertTrue(row['review']['payload']['confirmed']);self.assertEqual(row['review']['revision'],1)
  data=self.client.get('/api/v1/export?format=csv');rows=list(csv.DictReader(io.StringIO(data.content.decode('utf-8-sig'))));self.assertEqual(rows[0]['extraction_status'],'NOT_EXECUTED');self.assertIn('Manual engineering note',rows[0]['review']);self.assertIn('methodology',rows[0])
 def test_08_corrupt_source_can_be_replaced(self):
  self.add('p');first=self.upload('p',self.pdf());doc=self.store.document(first.json()['document_id']);Path(doc['path']).write_text('corrupt');self.assertEqual(self.upload('p',self.pdf('Replacement')).status_code,201)
 def test_09_pdf_selection_does_not_include_other_metadata(self):
  import zipfile
  for p in ['p1','p2']:self.add(p)
  r=self.client.get('/api/v1/export/pdf?paper_id=p1');self.assertEqual(r.status_code,200)
  with zipfile.ZipFile(io.BytesIO(r.content)) as z:self.assertEqual([x['paper_id'] for x in json.loads(z.read('manifest.json'))],['p1'])
 def test_10_favicon_and_security_policy(self):
  r=self.client.get('/');self.assertNotIn("'unsafe-inline'",r.headers['Content-Security-Policy']);self.assertEqual(self.client.get('/favicon.svg').status_code,200)
 def test_11_comparison_export_and_gap_do_not_silently_drop_missing_paper(self):
  for pid in ['p1','p2','missing']:
   self.add(pid)
   if pid=='missing':continue
   self.upload(pid,self.pdf(pid));d=self.store.document(self.store.paper(pid)['current_document']);self.store.save_extraction(d['document_id'],ScientificRecord(paper_id=pid,document_sha256=d['sha256'],extraction_version='fixture',model='NO_MODEL',execution_status='NOT_EXECUTED'))
  body={'paper_ids':['p1','p2','missing']}
  for route in ['/api/v1/compare','/api/v1/compare/export','/api/v1/gaps']:
   self.assertEqual(self.client.post(route,json=body).status_code,422,route)
 def test_12_flat_spreadsheet_columns_guard_whitespace_formula(self):
  from science_platform.exporting import encode_export
  row={'paper':{'paper_id':'p','title':'  =RUN()','doi':None},'extraction':None};data,_=encode_export([row],'csv');r=next(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))));self.assertEqual(r['title'],"'  =RUN()");self.assertEqual(r['doi'],'')
if __name__=='__main__':unittest.main(verbosity=2)
