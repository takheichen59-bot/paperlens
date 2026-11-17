"""Re-run local legal PDFs; compare original fields and inspect delivery files.

This checks source spans, known handoff examples and file consistency. It does
not estimate precision/recall or treat the assistant's inspection as human gold.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pymupdf as fitz
from research.__main__ import manifest
from research.extraction import validate_scientific_record
from research.library import Library, checksum


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--workdir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--baseline-jsonl', type=Path)
    args = p.parse_args()
    baseline = {r['paper_id']: r for r in (json.loads(line) for line in args.baseline_jsonl.read_text().splitlines())} if args.baseline_jsonl else {}
    items = list(manifest(args.manifest)); library = Library(args.workdir)
    sources = {}
    for item in items:
        meta = item['meta']; digest = checksum(item['pdf'])
        if meta.get('sha256') and meta['sha256'] != digest:
            raise ValueError('Source checksum mismatch: ' + meta['id'])
        with fitz.open(item['pdf']) as pdf:
            sources[meta['paper_id']] = {'pages': len(pdf), 'bytes': Path(item['pdf']).stat().st_size, 'sha256': digest,
                'url': meta.get('pdf_url'), 'license': meta.get('license_url')}
    batch = library.run(items, workers=1)
    exported = library.export(args.output); folder = Path(exported['directory'])
    records = list(library.records()); summaries = []
    unchanged_fields = ['materials', 'methods', 'findings', 'conclusions', 'algorithms', 'formulas', 'experimental_data', 'limitations', 'legacy_record']
    for r in records:
        validate_scientific_record(r)
        old = baseline.get(r['paper_id']); unchanged = None
        if old:
            unchanged = all(old[k] == r[k] for k in unchanged_fields)
            def span_identity(snippet):
                return {k: v for k, v in snippet.items() if k != 'strategy'}
            if not unchanged or [span_identity(s) for s in r['source_snippets'][:len(old['source_snippets'])]] != [span_identity(s) for s in old['source_snippets']]:
                raise ValueError('Original candidates or evidence changed: ' + r['id'])
        by_id = {s['evidence_id']: s for s in r['source_snippets']}
        numeric = [{**n, 'text': r['experimental_data'][n['candidate_index']]['text'],
            'pages': [by_id[eid]['page_start'] for eid in n['evidence_ids']]} for n in r['attribution']['numeric']]
        # These two assertions are from the user's supplied handoff example,
        # not an independently annotated scientific evaluation dataset.
        if r['id'] == '2501.00680v1':
            if {m['name']: m['role'] for m in r['attribution']['materials']} != {'BiFeO3': 'study_subject', 'MoS2': 'background', 'Bi4Ti3O12': 'background'}:
                raise ValueError('Known material ownership regression')
            if not any('97%' in n['text'] and n['role'] == 'cited_result' for n in numeric):
                raise ValueError('Known cited numeric regression')
        summaries.append({'id': r['id'], 'source': sources[r['paper_id']], 'status': r['status'], 'review_status': r['review_status'],
            'original_fields_unchanged': unchanged, 'field_lengths': {f: len(r[f]) for f in ['methods', 'findings', 'conclusions']},
            'materials': [{k: m[k] for k in ['name', 'role']} for m in r['attribution']['materials']],
            'numeric_roles': dict(Counter(n['role'] for n in numeric)), 'numeric_candidates': numeric,
            'exact_slices_verified': len(r['source_snippets']),
            'missing_core_fields': [f for f in ['materials', 'methods', 'findings', 'conclusions'] if not r[f]]})
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(folder / 'research.xlsx') as book:
        sheet = ET.fromstring(book.read('xl/worksheets/sheet1.xml')); rows = sheet.findall('s:sheetData/s:row', ns)[1:]
        if len(rows) != len(records): raise ValueError('Spreadsheet row count mismatch')
        for row, record in zip(rows, records):
            cells = [c.find('s:is/s:t', ns).text or '' for c in row.findall('s:c', ns)]
            for field, column in [('methods', 3), ('findings', 4), ('conclusions', 5)]:
                if cells[column] != record[field]: raise ValueError('Spreadsheet field mismatch')
    with fitz.open(folder / 'processing-report.pdf') as report: report_pages = len(report)
    result = {'status': 'PASS' if batch['failed'] == 0 and len(records) == len(items) else 'FAIL',
        'scope': 'REAL_PDFS_SOURCE_SPAN_AND_DELIVERY_CONSISTENCY', 'batch': batch,
        'scientific_accuracy': 'NOT_EVALUATED_NO_INDEPENDENT_GOLD', 'real_llm': 'NOT_EXECUTED',
        'report_pages': report_pages, 'records': summaries}
    receipt = args.output / 'real-validation.json'; receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'papers': len(records), 'receipt': str(receipt), 'report_pages': report_pages}))
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
