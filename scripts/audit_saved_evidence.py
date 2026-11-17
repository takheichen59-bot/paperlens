"""Verify saved real-corpus evidence locations; this is not semantic evaluation."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from exports import read_frozen_results
root=Path(__file__).resolve().parents[1]/'docs/audit'
papers=json.loads((root/'source_blocks.json').read_text());total=0
for value in read_frozen_results(root/'real_results.jsonl'):
    r=value.model_dump(mode='json')
    if r['status']=='failed':continue
    pid='arxiv:'+r['source_url'].rsplit('/',1)[1].split('v')[0];blocks=papers[pid]['blocks']
    for s in r['source_snippets']:
        b=blocks[s['block_id']]
        assert b['text'][s['start_offset']:s['end_offset']]==s['text']
        assert s['page_start']==s['page_end']==b['page']
        assert s['section']==b['section']
        total+=1
    for field in ('methods','conclusions'):
        snippets=[s for s in r['source_snippets'] if s['field']==field]
        positions=[blocks[s['block_id']]['order'] for s in snippets]
        assert positions==sorted(positions)
        assert r[field]=='\n\n'.join(dict.fromkeys(s['text'] for s in snippets))
    assert r['status']!='success' or (r['methods'].strip() and r['conclusions'].strip() and r['chemicals'])
print(f'PASS {total} original-block slice/page/section checks; text-field order preserved.')
print('These checks do NOT establish sentence completeness, chemical identity, or field relevance.')
