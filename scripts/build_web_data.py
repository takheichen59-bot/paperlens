"""Generate browser policy and explicitly labelled frozen Python regression data."""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from extractors.formula_rules import KNOWN_FORMULAS,OXIDATION
from extractors.chemicals import ChemicalExtractor
from parsers.heading_config import HEADINGS
from exports import *
root=Path(__file__).resolve().parents[1];assets=root/'src/paper_platform/web_assets'
policy={'terms':list(ChemicalExtractor().terms),'known_formulas':sorted(KNOWN_FORMULAS),'oxidation':OXIDATION,'headings':{k:v.value for k,v in HEADINGS.items()}}
(assets/'policy.json').write_text(json.dumps(policy,ensure_ascii=False)+'\n')
report=json.loads((root/'docs/stage_e/comparison.json').read_text());audit=json.loads((root/'docs/stage_e/leakage.json').read_text())
audit_map={r['paper_id']:r for r in audit['papers']};meta=json.loads((root/'docs/audit/real_manifest.json').read_text());out=root/'work/stage_e/real/results'
with open_current_snapshot(out) as s:
    results={identity[0]:r.model_dump(mode='json') for identity,r in zip(s.results_index,read_current_results(out,snapshot=s))}
    warnings={w.paper_id:{'informational':list(w.informational),'blocking':list(w.blocking)} for w in read_current_warnings_by_severity(out,snapshot=s)}
    papers=[]
    for item in meta:
        m=item['meta'];pid=m['paper_id'];r=results.get(pid);a=audit_map[pid]
        papers.append({'id':item['reference'],'title':m['title'],'doi':m['doi'],'url':m['page_url'],'pdf_url':m['pdf_url'],'record':r,
            'status':r['status'] if r else 'skipped','fixture':True,'audit_status':a['audit_status'],'leaks':len(a['leaks']),'warnings':warnings.get(pid,{})})
metrics={**report['counts'],**{k:audit[k] for k in ('decided_papers','unresolved_papers','not_applicable_papers','leaks')},'methods_200_3000':report['methods_200_3000']}
(assets/'corpus.json').write_text(json.dumps({'papers':papers,'metrics':metrics,'verification':'Python 规则基线；验收输出、断点恢复记录与 SHA256 随交付包提供。无独立人工金标准，不声明生产级准确率。'},ensure_ascii=False)+'\n')
print('Web data:',len(papers),'real papers;',len(results),'Python extraction records')
