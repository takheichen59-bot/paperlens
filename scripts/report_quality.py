"""Frozen ten-paper regression: counts, actual evidence, unknowns and limitations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse,json
from exports import *
from audit_leakage import load_cache,audit,render
from extractors.methods import MethodExtractor

def rows(root):
    with open_current_snapshot(root/'results') as s:
        values=read_current_results(root/'results',snapshot=s)
        return {identity[0]:r for identity,r in zip(s.results_index,values)}

def main(stage,previous):
    root=Path(f'work/stage_{stage}/real');docs=Path(f'docs/stage_{stage}');docs.mkdir(parents=True,exist_ok=True)
    current=rows(root);before=rows(Path(f'work/stage_{previous}/real'));parsed,invalid=load_cache(root/'cache')
    with open_current_snapshot(root/'results') as s:
        severity=read_current_warnings_by_severity(root/'results',snapshot=s)
        failures=read_current_failures(root/'results',snapshot=s)
        skipped={r.paper_id:r for r in failures if r.status==FailureStatus.SKIPPED}
        internal={r.paper_id for r in failures if is_warning_classification_error(r)}
        counts={'submitted':len(current)+len(skipped),'success':sum(r.status.value=='success' for r in current.values()),'partial':sum(r.status.value=='partial' for r in current.values()),'failed':sum(r.status.value=='failed' for r in current.values()),'skipped':len(skipped)}
        counts['failed_internal_classification']=len({pid for pid,r in current.items() if r.status.value=='failed'} & internal)
        counts['failed_content_or_processing']=counts['failed']-counts['failed_internal_classification']
        report={'counts':counts,'version_id':s.version_id,'published_at':s.published_at,'methods_200_3000':sum(200<=len(r.methods)<=3000 for r in current.values()),
            'sections_contain_unknown_papers':sum(any(sec.kind.value=='unknown' for sec in p.sections) for p,v in parsed.values()),
            'parsed_papers':len(parsed),'parser_unavailable':invalid,'informational':sum(len(w.informational) for w in severity),'blocking':sum(len(w.blocking) for w in severity)}
    leak=audit(root/'results',root/'cache');report['audit']={k:v for k,v in leak.items() if k not in ('papers','published_at','version_id')}
    report['papers']=[]
    for pid,r in current.items():
        p,v=parsed[pid];candidate=MethodExtractor(view=v).extract(p);old=before[pid]
        report['papers'].append({'paper_id':pid,'before_status':old.status.value,'status':r.status.value,'chemicals':list(r.chemicals),
            'methods_chars':len(r.methods),'conclusions_chars':len(r.conclusions),'methods_before_first':old.methods[:500],
            'methods_after_first':r.methods[:500],'methods_candidate_chars':len(candidate.methods),'methods_candidate_first':candidate.methods[:500],
            'conclusions_before_first':old.conclusions[:500],'conclusions_after_first':r.conclusions[:500],
            'unknown_sections':[sec.title or '(untitled)' for sec in p.sections if sec.kind.value=='unknown'],
            'captions':sum(w.startswith('caption_block:') for w in p.warnings),
            'status_only_change':all(getattr(old,f)==getattr(r,f) for f in ('chemicals','methods','conclusions')),
            'warnings':next({'informational':list(w.informational),'blocking':list(w.blocking)} for w in severity if w.paper_id==pid)})
    assert counts['submitted']==10 and len(current)==9
    (docs/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (docs/'LEAKAGE.md').write_text(render(leak));(docs/'leakage.json').write_text(json.dumps(leak,ensure_ascii=False,indent=2)+'\n')
    lines=[f'# {stage.upper()}阶段真实语料回归','',json.dumps(counts,ensure_ascii=False),'',
        f"methods长度200–3000：{report['methods_200_3000']}/10（长度不等于语义可用）；sections含UNKNOWN：{report['sections_contain_unknown_papers']}/10，解析成功{report['parsed_papers']}篇；未解析篇不记作已判定无UNKNOWN。",
        f"P1为5篇unresolved；本次{leak['unresolved_papers']}篇unresolved。UNKNOWN同时承载Introduction和无标题前置文本，不等于全部都是标题漏识别。",'',
        'C项需优先处理标题识别，而非仅多栏排序。' if leak['unresolved_papers']>=4 else '本次unresolved少于4篇；仍逐篇核对未识别范围。','',
        '| paper_id | 原→新状态 | methods长度 | conclusions长度 | UNKNOWN标题 | caption标记数 |','|---|---|---:|---:|---|---:|']
    for p in report['papers']:lines.append(f"| {p['paper_id']} | {p['before_status']}→{p['status']} | {p['methods_chars']} | {p['conclusions_chars']} | {', '.join(p['unknown_sections'])} | {p['captions']} |")
    for p in report['papers']:
        if not p['paper_id'].endswith('00589'):continue
        lines+=['','## 00589锚点对照','', '修复前methods开头：','```text',p['methods_before_first'] or '(空)','```',
            '修复后methods开头：','```text',p['methods_after_first'] or '(空；见M14前候选及长度)','```',
            f"M14前methods候选 {p['methods_candidate_chars']}字符，开头：",'```text',p['methods_candidate_first'],'```',
            '修复前conclusions开头：','```text',p['conclusions_before_first'],'```',
            '修复后conclusions开头：','```text',p['conclusions_after_first'],'```']
    lines+=['','## 泄漏与范围','',f"{leak['decided_papers']}篇全部片段可判定、{leak['unresolved_papers']}篇unresolved、{leak['not_applicable_papers']}篇不适用；已判定范围检出{leak['leaks']}条泄漏。详见LEAKAGE.md，不覆盖未判定区间。",'',
        '内容和状态变化分别记录在comparison.json；状态改善不能替代语义质量评估。']
    (docs/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='papers'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--stage',required=True);a.add_argument('--previous',required=True);v=a.parse_args();main(v.stage,v.previous)
