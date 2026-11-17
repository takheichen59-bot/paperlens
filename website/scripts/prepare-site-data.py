"""Prepare public benchmark indexes and pinned download receipts, not private data."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--records', type=Path, required=True)
p.add_argument('--exports', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
records = [json.loads(line) for line in a.records.read_text().splitlines() if line.strip()]
papers = []
for r in records:
    m = r['meta']
    if m.get('source') != 'arxiv' or m.get('license_url') != 'https://creativecommons.org/licenses/by/4.0/':
        raise ValueError('Seed indexes accept the explicitly licensed public corpus only')
    papers.append({**m, 'bytes': m['file_size'], 'sha256': r['pdf_hash'], 'file': 'PDF/' + r['id'] + '.pdf'})
files = {}
for filename in ['research.xlsx', 'research.jsonl', 'research.csv', 'evidence.csv', 'material_roles.csv', 'numeric_attribution.csv', 'processing-report.pdf']:
    data = (a.exports / filename).read_bytes()
    files[filename] = {'filename': filename, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
summary = [{k: v for k, v in r.items() if k not in {'raw_blocks', 'eligible_ranges', 'legacy_record'}} for r in records]
(a.output / 'corpus.json').write_text(json.dumps({'papers': papers, 'scope': 'five_real_cc_by_papers'}, ensure_ascii=False))
(a.output / 'research-index.json').write_text(json.dumps({'records': summary, 'artifacts': files, 'schema': 'research-1', 'seed_label': '真实论文示例 · 非实时检索结果'}, ensure_ascii=False))
print(json.dumps({'public_seed_papers': len(papers), 'download_files': len(files), 'output': str(a.output)}))
