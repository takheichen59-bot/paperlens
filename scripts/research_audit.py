"""All-field source-location audit; unknown sections remain explicitly unresolved."""
from pathlib import Path
import argparse, json, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from research.extraction import validate_scientific_record

parser=argparse.ArgumentParser();parser.add_argument('--records',type=Path,required=True)
parser.add_argument('--output',type=Path);args=parser.parse_args();report=[]
for line in args.records.read_text().splitlines():
    r=json.loads(line);validate_scientific_record(r);leaks=[];unknown=[];decided=0
    for s in r['source_snippets']:
        if s['section_kind'] in {'references','supplement'}:
            leaks.append({'field':s['field'],'page':s['page_start'],'text':s['text']})
        elif s['section_kind']=='unknown':
            unknown.append({'field':s['field'],'page':s['page_start'],'section':s['section'],
                            'reason':'section_attribution_unknown','evidence_id':s['evidence_id']})
        else:decided+=1
    report.append({'id':r['id'],'decided_snippets':decided,'unresolved_snippets':len(unknown),
                   'leaks':leaks,'unresolved':unknown})
summary={'papers':len(report),'fully_decided_papers':sum(not p['unresolved'] for p in report),
 'unresolved_papers':sum(bool(p['unresolved']) for p in report),'known_view_leaks':sum(len(p['leaks']) for p in report),
 'unresolved_snippets':sum(p['unresolved_snippets'] for p in report),
 'note':'Known-view checks are not independent layout ground truth; unknown sections remain unresolved.'}
if args.output:args.output.write_text(json.dumps({'summary':summary,'papers':report},ensure_ascii=False,indent=2)+'\n')
for p in report:print(p['id'],'decided='+str(p['decided_snippets']),'unresolved='+str(p['unresolved_snippets']),'known_view_leaks='+str(len(p['leaks'])))
print(json.dumps(summary,ensure_ascii=False));raise SystemExit(int(bool(summary['known_view_leaks'])))
