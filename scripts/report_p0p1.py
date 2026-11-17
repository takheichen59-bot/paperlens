"""Frozen-corpus before/after report, separate technical checks from field quality."""
import sys,json,sqlite3,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from contracts import ParsedPaper,ExtractionResult,Stage,ResultStatus,validate_record
from parsers.sections import SectionView,StructuredPDFParser,eligible_blocks
from extractors.chemicals import ChemicalExtractor
from extractors.methods import MethodExtractor
from extractors.conclusions import ConclusionExtractor
from exports import read_frozen_results,parse_failure_line,FailureStatus

ROOT=Path(__file__).resolve().parents[1]

def index_records(path):
    values=[r.model_dump(mode='json') for r in read_frozen_results(path)]
    return {'arxiv:'+r['source_url'].rsplit('/',1)[1].split('v')[0]:r for r in values}

def main():
    old=index_records(ROOT/'docs/audit/real_results.jsonl');base=ROOT/'work/fixes/real-final'
    new=index_records(base/'results/results.jsonl')
    queue=[parse_failure_line(json.loads(s)) for s in (base/'results/failures.jsonl').read_text().splitlines()]
    skipped={r.paper_id:r for r in queue if r.status==FailureStatus.SKIPPED}
    parsed={};artifacts=[]
    for path in (base/'cache/checkpoints').glob('*.json'):
        e=json.loads(path.read_text());d=json.loads(e['payload'])
        if 'raw_blocks' in d:
            p=ParsedPaper.model_validate_json(e['payload']);v=SectionView.from_dict(json.loads(e['section_view'])).validate(p)
            assert v.pdf_hash==p.pdf_hash and v.parser_version==StructuredPDFParser().version
            parsed[p.paper_id]=(p,v)
        if 'pdf_path' in d:artifacts.append(d)
    labels=json.loads((ROOT/'docs/audit/chemical_annotations.json').read_text())['entities']
    known_leaks={(a['paper_id'],a['entity'],a['category']) for a in labels if a['category'] in {'reference_leak','grant_identifier'}}
    candidates={};after_metadata={};traces=0
    with sqlite3.connect(base/'state.sqlite3') as db:
        for pid,payload in db.execute('SELECT paper_id,payload_json FROM extraction_results'):
            after_metadata[pid]=ExtractionResult.model_validate_json(payload)
    for pid,(p,v) in parsed.items():
        c=ChemicalExtractor(view=v).extract(p);m=MethodExtractor(view=v).extract(p);co=ConclusionExtractor(view=v).extract(p)
        candidates[pid]={'chemicals':list(c.chemicals),'methods_chars':len(m.methods),'conclusions_chars':len(co.conclusions),
            'methods_warnings':list(m.warnings),'sections':[(s.title,s.kind.value) for s in p.sections]}
        allowed=eligible_blocks(p,v);blocks={b.block_id:b for b in p.raw_blocks}
        for s in new[pid]['source_snippets']:
            b=blocks[s['block_id']]
            assert s['text']==b.text[s['start_offset']:s['end_offset']]
            assert s['page_start']==s['page_end']==b.page_number
            assert any(b.block_id==a.block_id and a.raw_start<=s['start_offset']<s['end_offset']<=a.raw_end and s['section']==a.section_title for a in allowed)
            traces+=1
        assert validate_record(new[pid]).valid
    published_leaks=[(pid,term,cat) for pid,term,cat in known_leaks if term in new.get(pid,{}).get('chemicals',[])]
    candidate_leaks=[(pid,term,cat) for pid,term,cat in known_leaks if term in candidates.get(pid,{}).get('chemicals',[])]
    before_good=[pid for pid,r in old.items() if 200<=len(r['methods'])<=3000]
    after_good=[pid for pid,r in new.items() if 200<=len(r['methods'])<=3000]
    per_paper=[]
    for pid,before in sorted(old.items()):
        after=new.get(pid);candidate=candidates.get(pid,{});warnings=list(after_metadata[pid].warnings) if pid in after_metadata else []
        old_leaks=[term for p,term,_ in known_leaks if p==pid]
        reasons=[]
        if old_leaks or 'acknowledg' in (before['methods']+before['conclusions']).lower():reasons.append('视图泄漏')
        if not before['chemicals'] or not before['methods'] or not before['conclusions']:reasons.append('字段缺失')
        if len(before['methods'])>3000:reasons.append('长度超限（按本轮上限复核）')
        reasons.append('其他：原质量告警/版面问题')
        if pid in skipped:root='默认100MiB；远端Content-Length超限，专用体积异常→skipped'
        elif after['status']=='failed' and candidate.get('methods_chars',0)>3000:root=f"M14拒绝超长methods候选（{candidate['methods_chars']}字）；整条结果failed，未保留其他候选字段"
        elif any('methods_fallback_truncated' in w for w in warnings):root='M12连续候选超限，清空methods；保留其他有证据字段，仍partial'
        elif any('methods_fallback_rejected' in w for w in warnings):root='M12正文/双块/关键词/同section条件不满足，拒绝方法回退；仍有字段缺失或告警'
        else:root='章节/边界改善；仍有版面告警，保持partial；非科学语义验收通过'
        per_paper.append({'paper_id':pid,'before_status':before['status'],'before_partial_reasons':reasons if before['status']=='partial' else [],
            'after_status':after['status'] if after else 'skipped','methods_before':len(before['methods']),'methods_after':len(after['methods']) if after else 0,
            'conclusions_before':len(before['conclusions']),'conclusions_after':len(after['conclusions']) if after else 0,
            'chemicals_before':len(before['chemicals']),'chemicals_after':len(after['chemicals']) if after else 0,
            'known_leak_terms_before':old_leaks,'warnings_after':warnings,'root_cause':root,
            'candidate_before_validation':candidate})
    download_rows=[]
    for pid in ['arxiv:2501.01468','arxiv:2501.00600']:
        if pid in skipped:
            r=skipped[pid];download_rows.append({'paper_id':pid,'status':'skipped','file_bytes':r.file_bytes,'file_bytes_source':r.file_bytes_source,'limit_bytes':r.limit_bytes,'bytes_received':r.bytes_received,'skipped_reason':r.skipped_reason})
        else:
            p,_=parsed[pid];a=next(a for a in artifacts if a['content_hash']==p.pdf_hash)
            assert Path(a['pdf_path']).stat().st_size==a['bytes']
            download_rows.append({'paper_id':pid,'status':new[pid]['status'],'download_status':'success','file_bytes':a['bytes'],'file_bytes_source':'filesystem_after_full_download','skipped_reason':None})
    run=json.loads((ROOT/'docs/fixes/real_run.json').read_text());counts=json.loads(run['stdout'])
    assert counts['submitted']==counts['success']+counts['partial']+counts['failed']+counts['skipped']+counts['duplicates']
    summary={'counts':counts,'methods_200_3000_before':len(before_good),'methods_200_3000_after':len(after_good),
        'methods_papers_before':before_good,'methods_papers_after':after_good,'parsed_papers':len(parsed),'raw_snippets_checked':traces,
        'known_leaks_baseline':{'reference_entities':8,'grant_identifiers':3},'published_known_leaks_after':published_leaks,
        'candidate_known_leaks_after':candidate_leaks,'download_outcomes':download_rows,'per_paper':per_paper,
        'limitations':['Length interval is not field correctness.','Known-leak regression is not a complete precision/recall score.','2501.00589 methods still includes a figure caption and conclusions spills into method content due to column reading order.','HK0/HK1 false chemical entities remain; no new NER/chemical ontology rules added.','2501.00591 previously body-supported NbS2 is absent after conservative boundary exclusion; recall may regress.']}
    out=ROOT/'docs/fixes';(out/'comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    lines=['# P0/P1 修复与同批真实语料重跑','',f"实际输出：`{json.dumps(counts,ensure_ascii=False)}`。退出码 {run['returncode']}；{run['elapsed_seconds']} 秒；全新数据库、全新缓存。",
        '',f"methods 长度200–3000：{len(before_good)}/10 → {len(after_good)}/10。新名单：{', '.join(after_good)}。这仅是长度指标，不代表可用方法数。",
        '',f"基线8个参考文献实体+3个基金编号：发布结果残留 {len(published_leaks)}；对9篇解析产物在M14拒绝前的chemical候选复核，残留 {len(candidate_leaks)}。因此不是仅靠清空failed结果得到0。",
        '',f"{traces} 条发布证据与原始raw_blocks切片、页码、视图范围核对一致；9篇缓存均具有匹配PDF哈希和解析版本的SectionView。",
        '', '## 原8个partial逐篇对照','', '| arXiv | 修复前问题类别 | 修复后 | methods字符前→后 | conclusions字符前→后 | 根因 |','|---|---|---|---:|---:|---|']
    for r in per_paper:
        if r['before_status']=='partial':lines.append(f"| {r['paper_id'].split(':')[1]} | {'；'.join(r['before_partial_reasons'])} | {r['after_status']} | {r['methods_before']}→{r['methods_after']} | {r['conclusions_before']}→{r['conclusions_after']} | {r['root_cause']} |")
    lines+=['','## 两篇原下载失败论文','']
    for d in download_rows:lines.append('- `'+d['paper_id']+'`：'+json.dumps(d,ensure_ascii=False))
    lines+=['','## 字段级改进和仍未解决的问题','',
        '- 2501.00680：识别 Calculation details，methods 2491→1330；conclusions 789→405，排除致谢。仍有首页版面告警，状态保持partial。',
        '- 2501.00679：识别 METHOD、SUMMARY AND OUTLOOK，methods 5306→815；不是把原5306截取前3000字符。结论166→5205，仍需检查完整性。',
        '- 2501.00589：methods 42376→925，但925字符含FIG.6图注；conclusions 467→11036并混入方法。长度通过不能称为抽取有用，多栏阅读顺序仍未解决。',
        '- 2501.00561：识别实验章节后methods候选8229字，M14按3000上限拒绝整条结果，因此partial→failed；不能把化学物清空误报成实体质量提高。',
        '- 2501.00620：原2018字单块/零散回退不满足新规则，methods清空；这是保护性收紧造成的覆盖下降。',
        '- 2501.00591：基金编号和文献化学物被排除，但HK0/HK1仍是误报，正文曾出现的NbS2也不再输出。尚未评估recall。',
        '', '没有success增长，不能宣称完成真实质量验收。当前修复证明边界、长度和状态政策执行；不证明科研字段整体正确。',
        '', '## 验收与实现边界','',
        '- 20份模块脚本125个活动场景通过；历史单块正例保留并SKIP，不计通过；3项配置开关验证另计。',
        '- contracts、schema.sql、0001_init.sql哈希保持不变；没有新模型、密钥或表结构。',
        '- SectionView不进入ParsedPaper、不挂私有属性、不使用全局字典；缺失/错PDF哈希/错版本的缓存均重解析。',
        '- M18行schema扩展：FailureStatus与ResultStatus分离，parse_failure_line统一解析failed/skipped；字节数超限使用专用异常，不吸收非体积错误。',
        '- 单栏居中页码的双列误报已修；不同高度行不得配对，仍保留其他可疑版面告警。',
        '', '复验：`python scripts/verify_all.py`、`python scripts/verify_m14_checks.py`；实际逐项输出见本目录00–06与REGRESSION.txt。',
        '重建此报告：`python scripts/report_p0p1.py`，需保留work/fixes/real-final的数据库和缓存。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'per_paper','limitations'}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
