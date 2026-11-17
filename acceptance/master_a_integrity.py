from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research.library import Library
from _research_fixture import synthetic_record

def item(tmp,value='one'):
 p=Path(tmp)/'input';p.write_text(value)
 return {'pdf':p,'meta':{'paper_id':'audit:1','id':'audit-1','title':'Synthetic integrity fixture','url':''}}
def history():
 with TemporaryDirectory() as t:
  lib=Library(Path(t)/'lib');i=item(t);lib.run([i],extractor=synthetic_record);old=next(lib.records())
  Path(i['pdf']).write_text('replacement');lib.run([i],extractor=synthetic_record)
  assert lib.history('audit:1')[0]['record']==old
  assert next(lib.records())['pdf_hash']!=old['pdf_hash']
def failed_replacement():
 with TemporaryDirectory() as t:
  lib=Library(Path(t)/'lib');i=item(t);lib.run([i],extractor=synthetic_record);item(t,'changed')
  def fail(*a):raise ValueError('injected')
  assert lib.run([i],extractor=fail)['failed']==1
  assert not list(lib.records()) and lib.history('audit:1')
def bad_item_isolation():
 with TemporaryDirectory() as t:
  lib=Library(Path(t)/'lib');r=lib.run([{'meta':{}},item(t)],extractor=synthetic_record)
  assert r['failed']==1 and r['processed']==1

def publication_failure():
 with TemporaryDirectory() as t:
  lib=Library(Path(t)/'lib');lib.run([item(t)],extractor=synthetic_record);out=Path(t)/'out';first=lib.export(out)
  from unittest.mock import patch
  with patch('research.library.write_xlsx',side_effect=OSError('injected')):
   try:lib.export(out)
   except OSError:pass
   else:raise AssertionError()
  assert json.loads((out/'CURRENT.json').read_text())==first

def hash_bound_review():
 with TemporaryDirectory() as t:
  lib=Library(Path(t)/'lib');i=item(t);lib.run([i],extractor=synthetic_record);lib.review('audit:1',decision='reviewed')
  assert next(lib.records())['review']['decision']=='reviewed'
  item(t,'new PDF');lib.run([i],extractor=synthetic_record)
  assert 'review' not in next(lib.records()) and 'previous_review' in next(lib.records())
failed=0
for fn in [history,failed_replacement,bad_item_isolation,publication_failure,hash_bound_review]:
 try:fn();print('PASS',fn.__name__)
 except Exception as e:failed+=1;print('FAIL',fn.__name__,type(e).__name__)
print(f'PHASE A PYTHON: {5-failed} passed, {failed} failed');raise SystemExit(int(bool(failed)))
