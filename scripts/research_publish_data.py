"""Build the website's immutable scientific corpus from verified local records."""
from pathlib import Path
import hashlib, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from research.library import Library
from research.extraction import record_summary, validate_scientific_record
SITE = ROOT.parent/'sites/matterlens'
target = ROOT/'work/research/publish'; target.mkdir(parents=True,exist_ok=True)
records = list(Library(ROOT/'work/research/library').records())
assert len(records)==20
index=[]
for r in records:
    validate_scientific_record(r)
    path=target/(r['id'].replace('/','_')+'.json')
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    s=record_summary(r);s['artifact_bytes']=path.stat().st_size;s['artifact_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    index.append(s)
export=Library(ROOT/'work/research/library').export(ROOT/'work/research/export')
artifacts={}
for p in Path(export['directory']).iterdir():
    if not p.is_file() or p.name=='manifest.json':continue
    name='research20-'+p.name
    shutil.copyfile(p,SITE/'downloads'/name)
    artifacts[name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'filename':p.name}
from research.analysis import graph
extras = {
    'index.json': (SITE/'web_assets/phase1-index.json').read_text(),
    'README.md': (ROOT/'docs/RESEARCH_DELIVERY.md').read_text(),
    'knowledge_graph.json': json.dumps(graph(records),ensure_ascii=False,indent=2)+'\n',
}
for filename,content in extras.items():
    path=SITE/'downloads'/('research20-'+filename);path.write_text(content)
    artifacts[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'filename':filename}
pdfs=json.loads((SITE/'web_assets/phase1-index.json').read_text())['papers']
sums=[p['sha256']+'  '+p['file'] for p in pdfs]
sums += [a['sha256']+'  '+a['filename'] for a in artifacts.values()]
path=SITE/'downloads/research20-SHA256SUMS';path.write_text('\n'.join(sums)+'\n')
artifacts[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'filename':'SHA256SUMS'}
output={'schema_version':'research-index-1','records':index,'artifacts':artifacts}
(SITE/'web_assets/research-index.json').write_text(json.dumps(output,ensure_ascii=False)+'\n')
(target/'index.json').write_text(json.dumps(output,ensure_ascii=False)+'\n')
(SITE/'fixtures/research-sample.json').write_text(json.dumps(records[0],ensure_ascii=False)+'\n')
report={'papers':len(records),'with_materials':sum(bool(r['materials']) for r in records),
    'with_methods':sum(bool(r['methods']) for r in records),
    'methods_200_3000':sum(200<=len(r['methods'])<=3000 for r in records),
    'with_conclusions':sum(bool(r['conclusions']) for r in records),'with_findings':sum(bool(r['findings']) for r in records),
    'with_algorithms':sum(bool(r['algorithms']) for r in records),'with_formulas':sum(bool(r['formulas']) for r in records),
    'with_data_candidates':sum(bool(r['experimental_data']) for r in records),
    'evidence':sum(len(r['source_snippets']) for r in records),
    'unknown_section_snippets':sum(s['section_kind']=='unknown' for r in records for s in r['source_snippets']),
    'reviewed':0,'accuracy_independently_evaluated':False}
(ROOT/'docs/RESEARCH_METRICS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
