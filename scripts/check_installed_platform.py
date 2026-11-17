"""Exercise an isolated installed wheel without importing this source tree."""
import argparse,subprocess,tempfile,os
from pathlib import Path
CHECK=r'''
from tempfile import TemporaryDirectory
from importlib.metadata import version
from fastapi.testclient import TestClient
import science_platform,science_platform.api
assert 'site-packages' in science_platform.__file__
assert version('paper-extraction-contracts')=='0.3.0'
print('PASS isolated wheel 0.3.0 imports from site-packages')
with TemporaryDirectory() as root:
 with TestClient(science_platform.api.create_app(root,start_worker=False)) as c:
  assert c.get('/').status_code==200
  assert 'PaperLens' in c.get('/').text
  assert c.get('/app.js').status_code==200
  assert c.get('/style.css').status_code==200
  assert c.get('/api/v1/health').json()['version']=='0.3.0'
  r=c.post('/api/v1/papers',json={'paper_id':'install:fixture','doi':None,'title':'Installed API fixture','source_url':''})
  assert r.status_code==201,r.text
  assert c.get('/api/v1/papers?q=Installed').json()['total']==1
  assert c.get('/api/v1/export').status_code==200
print('PASS installed assets, metadata API, filter and export')
print('INSTALL CHECKS: 2 passed; browser interaction NOT EXECUTED')
'''
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--python',type=Path,required=True);args=p.parse_args()
 with tempfile.TemporaryDirectory() as tmp:
  env=os.environ.copy();env.pop('PYTHONPATH',None)
  r=subprocess.run([str(args.python.absolute()),'-c',CHECK],cwd=tmp,env=env,text=True)
 raise SystemExit(r.returncode)
