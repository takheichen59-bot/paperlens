"""Re-run actual PDFs listed in a licensed manifest; never downloads or substitutes fixtures.

Usage: python scripts/validate_reading_corpus.py --manifest ... --output ... [--before research.jsonl]
The assistant source review is not an independent scientific gold standard.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from research.library import Library
from research.reading import validate_reading

p=argparse.ArgumentParser()
p.add_argument('--manifest',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--before',type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
items=json.loads(a.manifest.read_text())
for item in items:
    item['pdf']=str(a.manifest.parent/item['pdf'])
    if not Path(item['pdf']).is_file():raise FileNotFoundError(item['pdf'])
    if item['meta'].get('license_url')!='https://creativecommons.org/licenses/by/4.0/':raise ValueError('Expected pinned licensed public corpus')
    if hashlib.sha256(Path(item['pdf']).read_bytes()).hexdigest()!=item['meta']['sha256']:raise ValueError('Source changed')
library=Library(a.output/'library');stats=library.run(items,workers=1)
if stats['failed']:raise RuntimeError(stats)
manifest=library.export(a.output/'release');records=list(library.records())
old={r['id']:r for r in map(json.loads,a.before.read_text().splitlines())} if a.before else {}
checks=[]
for r in records:
    validate_reading(r);c=r['reading_card'];g=c.get('source_review',{})
    row={'id':r['id'],'pdf_hash':r['pdf_hash'],'automatic_status':r['status'],'type':c['article_type'],'source_review':g.get('status'),'user_review':r['review_status'],'reading_evidence':len(c['evidence']),'exact_source_parts':sum(len(e['parts']) for e in c['evidence']),'key_numbers':len(g.get('numbers',[])),'fields':{}}
    for f in ['methods','findings','conclusions']:
        row['fields'][f]={'before_chars':len(old.get(r['id'],{}).get(f,'')),'current_automatic_chars':len(r[f]),'reading_status':c['fields'][f]['status'],'source_review_points':len(g.get('conclusion' if f=='conclusions' else f,[]))}
    checks.append(row)
summary={'scope':'ACTUAL_FIVE_LICENSED_PDFS','stats':stats,'records':checks,'export':manifest,'scientific_accuracy':'NOT_INDEPENDENTLY_EVALUATED','reader_timed_study':'NOT_EXECUTED','llm':'NOT_CONFIGURED_NOT_EXECUTED'}
(a.output/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))
