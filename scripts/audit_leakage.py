"""Read-only section/range leakage audit. This is not a full semantic gold set."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import argparse
from hashlib import sha256
import json
import re
from contracts import ParsedPaper
from parsers.sections import SectionView, StructuredPDFParser
from exports import open_current_snapshot, read_current_results, read_current_failures, FailureStatus

DEFAULT_TRUTH = Path(__file__).with_name('audit_ground_truth.json')
EXCLUDED = re.compile(r'references|bibliography|acknowledg(?:e)?ments?|funding', re.I)
KNOWN_BODY_TITLES=frozenset({'introduction','theory','application','background','results','discussion'})


def known_body_title(title):
    return re.sub(r'^(?:[IVXLCDM]+\.|\d+(?:\.\d+)*[.)]?|[A-Z]\.)\s+','',title.strip(),flags=re.I).lower().rstrip(':.') in KNOWN_BODY_TITLES


def load_ground_truth(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict) or not value:
        raise ValueError('Invalid ground truth')
    for pid, entries in value.items():
        if not isinstance(pid, str) or not isinstance(entries, list) or not entries:
            raise ValueError('Invalid ground truth')
        for e in entries:
            if set(e) != {'block_id', 'start', 'end', 'actual_section', 'note'}:
                raise ValueError('Invalid ground truth keys')
            if not all(isinstance(e[k], str) and e[k] for k in ('block_id', 'actual_section', 'note')):
                raise ValueError('Invalid ground truth strings')
            if type(e['start']) is not int or type(e['end']) is not int or not 0 <= e['start'] < e['end']:
                raise ValueError('Invalid ground truth interval')
    return value


def load_cache(cache):
    papers, artifacts, invalid = {}, {}, {}
    for path in (Path(cache) / 'checkpoints').glob('*.json'):
        try:
            env = json.loads(path.read_text(encoding='utf-8')); data = json.loads(env['payload'])
            if sha256(env['payload'].encode()).hexdigest() != env['checksum']:
                if 'paper_id' in data: invalid[data['paper_id']] = '缺哈希或缓存校验失败'
                continue
            if 'pdf_path' in data:
                artifacts[data['content_hash']] = data
            if 'raw_blocks' in data:
                papers[data['paper_id']] = (data, env)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    loaded = {}
    for pid, (data, env) in papers.items():
        try:
            paper = ParsedPaper.model_validate_json(env['payload'])
            if not paper.pdf_hash: raise ValueError('缺哈希')
            payload = env.get('section_view')
            if not payload: raise ValueError('视图不可用：缓存无SectionView')
            if sha256(payload.encode()).hexdigest() != env.get('section_view_checksum'):
                raise ValueError('视图不可用：校验不匹配')
            view = SectionView.from_dict(json.loads(payload)).validate(paper)
            if view.parser_version != StructuredPDFParser().version:
                raise ValueError('视图不可用：解析版本不匹配')
            artifact = artifacts.get(paper.pdf_hash)
            if artifact is None: raise ValueError('缺哈希：无匹配下载产物')
            pdf = Path(artifact['pdf_path'])
            if not pdf.is_file(): raise ValueError('缺缓存：原始PDF不可用')
            if pdf.stat().st_size != artifact['bytes'] or sha256(pdf.read_bytes()).hexdigest() != paper.pdf_hash:
                raise ValueError('缺哈希或PDF哈希不匹配')
            loaded[pid] = (paper, view)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            invalid[pid] = str(exc) if type(exc) is ValueError and str(exc).startswith(('缺', '视图')) else '视图不可用：缓存无效'
    return loaded, invalid


def verify_truth(paper, entries):
    blocks = {b.block_id: b for b in paper.raw_blocks}
    for e in entries:
        block = blocks.get(e['block_id'])
        if block is None or e['end'] > len(block.text):
            raise ValueError('Ground truth raw interval unavailable')
        for key, actual in [('pdf_sha256', paper.pdf_hash), ('raw_sha256', sha256(block.text.encode()).hexdigest())]:
            expected = re.search(key + r'=([0-9a-f]{64})', e['note'])
            if expected and expected[1] != actual:
                raise ValueError('Ground truth hash mismatch')


def audit_paper(pid, record, cached, truth, unavailable):
    snippets = record.source_snippets
    report = {'paper_id': pid, 'status': record.status.value, 'snippets': len(snippets),
              'decided': 0, 'unresolved': 0, 'leaks': [], 'unresolved_reasons': []}
    if not snippets:
        report['audit_status'] = 'not_applicable'
        return report
    if cached is None:
        report.update(audit_status='unresolved', unresolved=len(snippets),
                      unresolved_reasons=[unavailable or '缺缓存'])
        return report
    paper, view = cached; blocks = {b.block_id: b for b in paper.raw_blocks}
    try:
        verify_truth(paper, truth)
    except ValueError:
        report.update(audit_status='unresolved', unresolved=len(snippets),
                      unresolved_reasons=['区间无法判定：ground truth与缓存不匹配'])
        return report
    for s in snippets:
        block = blocks.get(s.block_id)
        sections = [sec for sec in view.sections if any(bid == s.block_id and a <= s.start_offset < s.end_offset <= z for bid, a, z in sec.spans)]
        known = [e for e in truth if e['block_id'] == s.block_id and max(e['start'], s.start_offset) < min(e['end'], s.end_offset)]
        if block is None or block.text[s.start_offset:s.end_offset] != s.text or len(sections) != 1:
            report['unresolved'] += 1; report['unresolved_reasons'].append('区间无法判定：raw切片或章节覆盖异常')
            continue
        section = sections[0]
        known_leak = [e for e in known if EXCLUDED.search(e['actual_section'])]
        if section.kind == 'unknown' and not known_leak and not known_body_title(section.title):
            report['unresolved'] += 1
            report['unresolved_reasons'].append('区间无法判定：无独立标题的前置/正文区' if not section.title else '区间无法判定：未登记的章节标题 '+section.title)
            continue
        report['decided'] += 1
        if section.kind == 'references' or EXCLUDED.search(section.title) or known_leak:
            report['leaks'].append({'field': s.field.value, 'block_id': s.block_id,
                'start': s.start_offset, 'end': s.end_offset, 'section': section.title,
                'actual_section': known_leak[0]['actual_section'] if known_leak else section.title,
                'basis': 'external_ground_truth' if known_leak else 'section_view', 'text': s.text})
    report['unresolved_reasons'] = list(dict.fromkeys(report['unresolved_reasons']))
    report['audit_status'] = 'unresolved' if report['unresolved'] else 'decided'
    return report


def audit(output, cache, ground_truth=DEFAULT_TRUTH):
    truth = load_ground_truth(ground_truth); cached, unavailable = load_cache(cache)
    with open_current_snapshot(output) as snapshot:
        records = read_current_results(output, snapshot=snapshot)
        failures = read_current_failures(output, snapshot=snapshot)
        reports = [audit_paper(identity[0], r, cached.get(identity[0]), truth.get(identity[0], []), unavailable.get(identity[0]))
                   for identity, r in zip(snapshot.results_index, records)]
        for pid in sorted({r.paper_id for r in failures if r.status == FailureStatus.SKIPPED}):
            reports.append({'paper_id': pid, 'status': 'skipped', 'audit_status': 'not_applicable', 'snippets': 0,
                            'decided': 0, 'unresolved': 0, 'leaks': [], 'unresolved_reasons': []})
        summary = {'version_id': snapshot.version_id, 'published_at': snapshot.published_at,
            'decided_papers': sum(r['audit_status'] == 'decided' for r in reports),
            'unresolved_papers': sum(r['audit_status'] == 'unresolved' for r in reports),
            'not_applicable_papers': sum(r['audit_status'] == 'not_applicable' for r in reports),
            'decided_snippets': sum(r['decided'] for r in reports), 'unresolved_snippets': sum(r['unresolved'] for r in reports),
            'leaks': sum(len(r['leaks']) for r in reports), 'papers': sorted(reports, key=lambda r:r['paper_id'])}
    return summary


def render(report):
    lines = ['# 全字段泄漏审计', '', f"读取版本：{report['version_id']}；发布时间：{report['published_at']}", '',
        '判定依据限于匹配PDF哈希/解析版本的章节视图及外部确证区间，不等于完整人工语义标注。', '',
        '| paper_id | 状态 | 审计 | 已判定片段 | unresolved片段 | 泄漏条数 | unresolved原因 |', '|---|---|---|---:|---:|---:|---|']
    for r in report['papers']:
        lines.append(f"| {r['paper_id']} | {r['status']} | {r['audit_status']} | {r['decided']} | {r['unresolved']} | {len(r['leaks'])} | {'；'.join(r['unresolved_reasons'])} |")
    lines += ['', f"范围限定：{report['decided_papers']}篇全部片段可判定，{report['unresolved_papers']}篇存在unresolved，{report['not_applicable_papers']}篇无抽取片段、不适用。已判定范围共发现{report['leaks']}条泄漏；不覆盖未判定区间。", '']
    for r in report['papers']:
        for leak in r['leaks']:
            lines += [f"## {r['paper_id']} / {leak['field']} / {leak['block_id']} [{leak['start']}:{leak['end']}]", '',
                f"当前归属：{leak['section']}；实际归属：{leak['actual_section']}；依据：{leak['basis']}", '', '```text', leak['text'], '```', '']
    return '\n'.join(lines) + '\n'


def self_check(output, cache, ground_truth=DEFAULT_TRUTH):
    try:
        truth = load_ground_truth(ground_truth)
        if not any(EXCLUDED.search(e['actual_section']) for entries in truth.values() for e in entries):
            raise ValueError('No known leak configured')
    except (OSError, ValueError, TypeError):
        print('FAIL: invalid ground truth'); return 1
    loaded, _ = load_cache(cache)
    for pid, entries in truth.items():
        if pid not in loaded:
            print('SKIP: cache unavailable'); return 2
        try:
            verify_truth(loaded[pid][0], entries)
        except ValueError:
            print('SKIP: cache unavailable'); return 2
    try:
        report = audit(output, cache, ground_truth)
    except (OSError, ValueError, KeyError):
        print('SKIP: cache unavailable'); return 2
    hits = [leak for r in report['papers'] for leak in r['leaks'] if leak['basis'] == 'external_ground_truth']
    if not hits:
        print('FAIL: leak not detected'); return 1
    print(f'PASS: known leak detected ({len(hits)} snippets)'); return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--ground-truth', type=Path, default=DEFAULT_TRUTH)
    parser.add_argument('--report', type=Path); parser.add_argument('--json-report', type=Path)
    args = parser.parse_args(); report = audit(args.output, args.cache, args.ground_truth)
    text = render(report)
    if args.report: args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text(text,encoding='utf-8')
    if args.json_report: args.json_report.parent.mkdir(parents=True,exist_ok=True); args.json_report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(text); return 0

if __name__ == '__main__': raise SystemExit(main())
