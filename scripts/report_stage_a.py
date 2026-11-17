"""P1 report: separate status policy changes, field content, and audit coverage."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse,json
from exports import (open_current_snapshot,read_current_results,read_current_warnings_by_severity,
    read_current_failures,read_frozen_results,is_warning_classification_error,FailureStatus)
from audit_leakage import audit,render,self_check

FIELDS=('chemicals','conclusions','methods')


def build(root,docs,baseline):
    out=root/'results';docs.mkdir(parents=True,exist_ok=True)
    old={'arxiv:'+r.source_url.rsplit('/',1)[1].split('v')[0]:r for r in read_frozen_results(baseline)}
    with open_current_snapshot(out) as s:
        rows=read_current_results(out,snapshot=s);warnings=read_current_warnings_by_severity(out,snapshot=s)
        failures=read_current_failures(out,snapshot=s)
        new={identity[0]:r for identity,r in zip(s.results_index,rows)}
        severity={w.paper_id:w for w in warnings}
        internal={r.paper_id for r in failures if is_warning_classification_error(r)}
        failed={pid for pid,r in new.items() if r.status.value=='failed'}
        skipped={r.paper_id:r for r in failures if r.status==FailureStatus.SKIPPED}
        counts={'submitted':len(new)+len(skipped),'success':sum(r.status.value=='success' for r in rows),
            'partial':sum(r.status.value=='partial' for r in rows),'failed':len(failed),'skipped':len(skipped),
            'failed_internal_classification':len(failed & internal),'failed_content_or_processing':len(failed-internal)}
        assert counts['failed']==counts['failed_internal_classification']+counts['failed_content_or_processing']
        assert counts['submitted']==sum(counts[k] for k in ('success','partial','failed','skipped'))==10
        papers=[]
        for pid in sorted(set(new)|set(skipped)):
            if pid in skipped:
                f=skipped[pid]
                papers.append({'paper_id':pid,'status':'skipped','informational':None,'blocking':None,
                    'file_bytes':f.file_bytes,'file_bytes_source':f.file_bytes_source,'bytes_received':f.bytes_received,
                    'skipped_reason':f.skipped_reason,'preserved_fields':[]})
                continue
            r=new[pid];w=severity[pid];before=old.get(pid)
            unchanged={f:getattr(before,f)==getattr(r,f) if before else False for f in FIELDS}
            if before and before.status!=r.status:
                reason='M14只清空超长methods，恢复chemicals/conclusions，failed→partial' if before.status.value=='failed' else '三字段及证据原已存在；仅提示性告警不再阻断，内容未因状态变化而改善'
            else:reason='状态不变；字段缺失或已有阻断性告警仍保留'
            papers.append({'paper_id':pid,'before_status':before.status.value if before else None,'status':r.status.value,
                'informational':list(w.informational),'blocking':list(w.blocking),
                'has_multicolumn_info':any('possible_multicolumn' in code for code in w.informational),
                'preserved_fields':[f for f in FIELDS if getattr(r,f)],
                'chemicals_count':len(r.chemicals),'conclusions_chars':len(r.conclusions),'methods_chars':len(r.methods),
                'content_unchanged':unchanged,'status_change_reason':reason,
                'failure_class':'internal_classification' if pid in failed & internal else 'content_or_processing' if pid in failed else None})
        report={'counts':counts,'version_id':s.version_id,'published_at':s.published_at,
            'inventory':'docs/diagnosis/WARNINGS_INVENTORY.md','informational_messages':sum(len(w.informational) for w in warnings),
            'blocking_messages':sum(len(w.blocking) for w in warnings),'papers':papers,
            'methods_200_3000':sum(200<=len(r.methods)<=3000 for r in rows),
            'evidence_snippets':sum(len(r.source_snippets) for r in rows)}
    leak=audit(out,root/'cache');(docs/'LEAKAGE.md').write_text(render(leak),encoding='utf-8')
    (docs/'leakage.json').write_text(json.dumps(leak,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    code=self_check(out,root/'cache');report['audit_selfcheck_exit']=code
    assert code==0,'Known leak self-check did not pass'
    report['audit']={k:leak[k] for k in ('decided_papers','unresolved_papers','not_applicable_papers','decided_snippets','unresolved_snippets','leaks')}
    (docs/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# P1：告警分级、M14字段降级、泄漏审计','',f"实际统计：`{json.dumps(counts,ensure_ascii=False)}`",'',
        f"读取版本 `{report['version_id']}`；发布时间 `{report['published_at']}`。分类依据：`{report['inventory']}`。",
        f"告警消息：informational {report['informational_messages']}，blocking {report['blocking_messages']}；原始证据 {report['evidence_snippets']} 条。",'',
        'failed_internal_classification属于程序内部告警分类遗漏/矛盾，标注为“待下一轮排查的分类遗漏”，排除于内容质量统计；其余failed为内容/处理失败。', '',
        '## 逐篇状态与告警','', '| paper_id | 原→新状态 | informational | blocking | methods字符 | success含多栏提示 |', '|---|---|---|---|---:|---|']
    for p in papers:
        if p['status']=='skipped':lines.append(f"| {p['paper_id']} | skipped | N/A | N/A | N/A | N/A |");continue
        lines.append(f"| {p['paper_id']} | {p['before_status']}→{p['status']} | {', '.join(p['informational']) or '无'} | {', '.join(p['blocking']) or '无'} | {p['methods_chars']} | {str(p['has_multicolumn_info']) if p['status']=='success' else 'N/A'} |")
    lines+=['','## 状态变化与内容变化分开说明','']
    for p in papers:
        if p['status']=='skipped':continue
        same=', '.join(f'{k}={v}' for k,v in p['content_unchanged'].items())
        lines.append(f"- {p['paper_id']}：状态原因：{p['status_change_reason']}。字段与修复前相同：{same}。保留字段：{', '.join(p['preserved_fields']) or '无'}。")
    lines += ['',f"methods长度200–3000：{report['methods_200_3000']}/10；这是长度统计，仍含图注和错序，不能解释为可用方法篇数。",'',
        '00561的chemicals/conclusions恢复属于输出内容恢复，不证明实体识别或结论语义改善。三篇success只改变状态政策，字段内容与A前一致。', '',
        '## 全字段泄漏审计','',
        f"{leak['decided_papers']}篇全部片段可判定；{leak['unresolved_papers']}篇有unresolved；{leak['not_applicable_papers']}篇不适用。已判定片段{leak['decided_snippets']}，未判定片段{leak['unresolved_snippets']}，已发现泄漏{leak['leaks']}条。完整片段见LEAKAGE.md。",'',
        '| paper_id | 审计状态 | 已判定/未判定片段 | 泄漏条数 | unresolved原因 |','|---|---|---|---:|---|']
    for p in leak['papers']:lines.append(f"| {p['paper_id']} | {p['audit_status']} | {p['decided']}/{p['unresolved']} | {len(p['leaks'])} | {'；'.join(p['unresolved_reasons']) or '无'} |")
    lines += ['',f"独立自检：`PASS: known leak detected`，退出码{code}。范围只涵盖有效章节视图和已确证区间，不是全部真实章节的人工标注，不覆盖unresolved范围。",'',
        '## 下载与已知限制','']
    for p in papers:
        if p['status']=='skipped':lines.append('- '+json.dumps(p,ensure_ascii=False))
    lines += ['', '- M09多栏顺序、图注/方法串入结论、HK0/HK1误报保持原样；本轮不改抽取规则。',
        '- 00589虽成为结构success，已确证的致谢续段泄漏仍存在，不能用状态提升解释内容改善。',
        '- parser_summary调试字段暂缓；解析清洗统计未进入分级文件。',
        '- exports使用CURRENT单点发布及共享读取快照；已改消费方与README。',
        '- contracts、表结构、M09、M12、化学物规则的哈希比对见UNCHANGED.json。',
        '', '验收：`python scripts/verify_all.py --results work/stage_a/real/results`。本阶段停在P1，尚未开始B–F及网站成品交付。']
    (docs/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='papers'},ensure_ascii=False,indent=2))
    for p in papers:print(p['paper_id'],p['status'],'info=',p.get('informational'),'block=',p.get('blocking'))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('work/stage_a/real'))
    parser.add_argument('--docs',type=Path,default=Path('docs/stage_a'))
    parser.add_argument('--baseline',type=Path,default=Path('docs/fixes/real_results.jsonl'))
    args=parser.parse_args();build(args.root,args.docs,args.baseline)
