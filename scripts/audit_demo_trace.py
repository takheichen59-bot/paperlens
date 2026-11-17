"""Verify current demo cache and raw evidence, with mandatory SectionView."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from contracts import ParsedPaper,validate_record
from parsers.sections import SectionView,StructuredPDFParser,eligible_blocks
from exports import read_current_results,read_current_failures,read_current_review

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path('work/fixes/demo'));args=parser.parse_args()
    root=args.root;parsed={}
    for path in (root/'cache/checkpoints').glob('*.json'):
        env=json.loads(path.read_text());data=json.loads(env['payload'])
        if 'raw_blocks' in data:
            p=ParsedPaper.model_validate_json(env['payload'])
            v=SectionView.from_dict(json.loads(env['section_view'])).validate(p)
            assert v.pdf_hash==p.pdf_hash and v.parser_version==StructuredPDFParser().version
            parsed[p.paper_id]=(p,v)
    reports=[];total=0
    for value in read_current_results(root/'results'):
        r=value.model_dump(mode='json');sid=r['source_url'].split('/abs/')[1].split('v')[0];p,v=parsed['arxiv:'+sid]
        blocks={b.block_id:b for b in p.raw_blocks};allowed=eligible_blocks(p,v)
        for s in r['source_snippets']:
            b=blocks[s['block_id']]
            assert s['text']==b.text[s['start_offset']:s['end_offset']] and s['page_start']==s['page_end']==b.page_number
            assert any(a.block_id==s['block_id'] and a.raw_start<=s['start_offset']<s['end_offset']<=a.raw_end and a.section_title==s['section'] for a in allowed)
            total+=1
        assert validate_record(r).valid and r['status']=='success'
        for field in ['methods','conclusions']:
            refs=[s for s in r['source_snippets'] if s['field']==field]
            assert r[field]=='\n\n'.join(dict.fromkeys(s['text'] for s in refs))
        reports.append({'paper_id':p.paper_id,'chemicals':r['chemicals'],'methods':r['methods'],'conclusions':r['conclusions'],'status':r['status']})
    failures=read_current_failures(root/'results')
    assert not failures and not read_current_review(root/'results')
    Path('docs/fixes/demo_trace_check.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    print(f'PASS {len(reports)} demo papers; {total} raw snippet slices; mandatory SectionView; queues empty.')
if __name__=='__main__':main()
