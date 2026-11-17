"""Read-only 00589 regression anchors; requires an explicit real-corpus cache."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from audit_leakage import load_cache
from exports import open_current_snapshot,read_current_results
from extractors.methods import MethodExtractor

def main(root):
    papers,_=load_cache(root/'cache');pid='arxiv:2501.00589';p,v=papers[pid]
    with open_current_snapshot(root/'results') as s:
        rows=read_current_results(root/'results',snapshot=s)
        r=next(r for (identity,r) in zip(s.results_index,rows) if identity[0]==pid)
    candidate=MethodExtractor(view=v).extract(p)
    caption=next(b for b in p.raw_blocks if b.block_id=='p6-b20')
    assert caption.text.startswith('FIG. 6.')
    assert any(bid==caption.block_id and a==0 and b==len(caption.text) for bid,a,b in v.excluded)
    assert all(ref.block_id!=caption.block_id for ref in candidate.source_snippets+r.source_snippets)
    assert not any(ref.block_id=='p6-b31' for ref in r.source_snippets if ref.field.value=='conclusions')
    assert any(bid=='p6-b31' for sec in v.sections if sec.kind=='methods' for bid,_,_ in sec.spans)
    assert r.conclusions.startswith('This work introduces')
    print('PASS 00589: FIG.6 excluded before M14; p6-b31 belongs to methods, absent from conclusions; conclusion begins with actual author summary')
    return 0
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);v=a.parse_args();raise SystemExit(main(v.root))
