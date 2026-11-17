from pathlib import Path
import json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from science_platform.parsing import ParserRouter
from science_platform.extraction import DeepExtractor
root=Path('/workspace/sites/matterlens/work/phase1/corpus');papers=json.loads((root/'index.json').read_text())['papers'][:10];reports=[]
out=Path('work/master-platform/parses');out.mkdir(parents=True,exist_ok=True)
for p in papers:
 start=time.monotonic()
 try:
  doc,external=ParserRouter().parse(root/p['file'],p['paper_id']);record=DeepExtractor().extract(doc)
  (out/(p['id']+'.json')).write_text(doc.model_dump_json())
  row={'id':p['id'],'status':'PARSED','segments':len(doc.segments),'equation_candidates':len(doc.equations),'tables':sum(s.kind=='table' for s in doc.segments),'figures':sum(s.kind=='figure' for s in doc.segments),'external':external,'deep_ai':record.execution_status,'seconds':round(time.monotonic()-start,2)}
 except Exception as e:row={'id':p['id'],'status':'FAILED','error':getattr(e,'code',type(e).__name__)}
 reports.append(row);print(json.dumps(row),flush=True)
Path('docs/master/REAL_PARSING.json').write_text(json.dumps({'papers':reports,'parsed':sum(r['status']=='PARSED' for r in reports),'total':len(reports),'human_gold':'NOT EXECUTED_NO_HUMAN_GOLD','real_llm':'NOT EXECUTED_NO_CREDENTIALS'},indent=2)+'\n')
raise SystemExit(int(any(r['status']!='PARSED' for r in reports)))
