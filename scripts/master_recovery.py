"""Real process-kill/resume check on a synthetic corpus; not a scale/quality claim."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from science_platform.jobs import Worker
from science_platform.store import Store
from science_platform.models import Paper
from science_platform.parsing import digest

def child(root):Worker(Store(Path(root)/'state.db'),root,lease_seconds=5).serve()
def main():
 import pymupdf as fitz
 with tempfile.TemporaryDirectory() as tmp:
  s=Store(Path(tmp)/'state.db');pdf=fitz.open();p=pdf.new_page();p.insert_text((72,72),'Methods',fontsize=16);p.insert_text((72,100),'The solver checks all constraints using a proof certificate.');path=Path(tmp)/'fixture.pdf';pdf.save(path);pdf.close();sha=digest(path)
  ids=['fixture:'+str(i) for i in range(12)]
  for pid in ids:s.upsert_paper(Paper(paper_id=pid,doi=None,title='Synthetic recovery '+pid,source_url=''));s.save_document(pid,sha,path,'pdf')
  jid=s.enqueue('batch',{'paper_ids':ids,'action':'parse'},total=len(ids));env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parents[1]/'src')
  proc=subprocess.Popen([sys.executable,__file__,'--child',tmp],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   deadline=time.monotonic()+50
   while time.monotonic()<deadline:
    j=s.job(jid)
    if j['progress']>=2:break
    if proc.poll() is not None:raise AssertionError('worker exited before kill')
    time.sleep(.05)
   else:raise AssertionError('no checkpoint')
   proc.kill();proc.wait(timeout=5);before=json.loads(s.job(jid)['result_json'])['items'];lease=s.job(jid)['lease_until']
   while time.time()<=lease+.1:time.sleep(.1)
   recovered=Worker(s,tmp,lease_seconds=5);assert recovered.one();j=s.job(jid);after=json.loads(j['result_json'])
   assert j['status']=='COMPLETED',j;assert len(after['items'])==12;assert all(after['items'][k]==v for k,v in before.items())
   with s.connection() as c:parse_count=c.execute('SELECT COUNT(*) FROM parses').fetchone()[0]
   assert parse_count==12,parse_count
   receipt={'corpus':'SYNTHETIC_ENGINEERING_FIXTURE','kill_returncode':proc.returncode,'checkpoint_papers':len(before),'completed':after['processed'],'attempts':j['attempts'],'parse_rows':parse_count,'duplicate_completed_work':0,'status':'PASS'}
   print(json.dumps(receipt,indent=2));out=Path(__file__).resolve().parents[1]/'docs/master/RECOVERY.json';out.write_text(json.dumps(receipt,indent=2)+'\n')
  finally:
   if proc.poll() is None:proc.kill();proc.wait(timeout=5)
if __name__=='__main__':
 if '--child' in sys.argv:child(sys.argv[-1])
 else:main()
