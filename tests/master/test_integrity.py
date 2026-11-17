import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from science_platform.models import *
from science_platform.store import Store
from science_platform.parsing import digest,XMLParser
from science_platform.errors import PlatformError
from science_platform.exporting import encode_export

class IntegrityTests(unittest.TestCase):
 def test_1_external_edit_invalidates_history_and_reviews(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'new.db');p=Path(tmp)/'p.pdf';p.write_bytes(b'one');s.upsert_paper(Paper(paper_id='p',doi=None,title='test',source_url=''));did=s.save_document('p',digest(p),p,'pdf');eid=s.save_extraction(did,ScientificRecord(paper_id='p',document_sha256=digest(p),extraction_version='1',model='fixture',execution_status='EXECUTED'));s.review(eid,0,{'confirmed':True});p.write_bytes(b'changed')
   self.assertIsNone(s.current_snapshot()[0]['extraction']);self.assertEqual(s.history('p')[0]['status'],'STALE');self.assertEqual(s.current_review(eid)['status'],'STALE');self.assertIsNone(s.paper('p')['current_document'])
 def test_2_baseline_migration_idempotence_and_refuse_other_db(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as tmp:
   db=Path(tmp)/'new';Store(db);Store(db)
   with sqlite3.connect(db) as c:self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],1)
   other=Path(tmp)/'legacy'
   with sqlite3.connect(other) as c:c.execute('CREATE TABLE tasks(id TEXT)')
   with self.assertRaises(PlatformError):Store(other)
   with sqlite3.connect(other) as c:self.assertEqual({r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")},{'tasks'})
 def test_3_xml_evidence_has_no_invented_pages_or_latex(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'p.xml';p.write_text('<article><body><sec><title>Methods</title><p>Actual method.</p><disp-formula><tex-math>x=1</tex-math></disp-formula></sec></body><back><ref-list><p>Reference chemical</p></ref-list></back></article>');r=XMLParser().parse(p,'p');self.assertTrue(all(s.page is None for s in r.segments));self.assertEqual(r.equations[0].latex,'x=1');self.assertEqual(r.segments[-1].kind,'references')
 def test_4_exports_escape_spreadsheets_preserve_provenance(self):
  from zipfile import ZipFile
  from io import BytesIO
  rows=[{'paper_id':'p','title':'=RUN()','evidence':[{'page':2,'quote':'source'}]}]
  csv,_=encode_export(rows,'csv');self.assertIn("'=RUN()",csv.decode('utf-8-sig'));data,_=encode_export(rows,'xlsx')
  with ZipFile(BytesIO(data)) as z:
   from xml.etree import ElementTree as ET
   for path in z.namelist():ET.fromstring(z.read(path))
   self.assertIn(b'paper_id',z.read('xl/worksheets/sheet1.xml'));self.assertNotIn(b'<f>',z.read('xl/worksheets/sheet1.xml'))
  data,_=encode_export(rows,'jsonl');self.assertEqual(json.loads(data),rows[0])
 def test_5_frozen_legacy_contracts(self):
  import hashlib
  root=Path(__file__).resolve().parents[2];receipt=json.loads((root/'docs/master/FROZEN_CONTRACTS.json').read_text())
  for p,expected in receipt['files'].items():self.assertEqual(hashlib.sha256((root/p).read_bytes()).hexdigest(),expected,p)
if __name__=='__main__':unittest.main(verbosity=2)
