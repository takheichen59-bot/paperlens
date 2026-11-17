import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from contracts import *
from parsers.cleaning import LayoutCleaner

def fixture(items):
    blocks=tuple(TextBlock(block_id=f'b{i}',page_number=p,text=t,bbox=(50.,float(y),500.,float(y+10))) for i,(p,y,t) in enumerate(items))
    return ParsedPaper(paper_id='fixture',pdf_hash='a'*64,pages=tuple(PageText(page_number=p,text='fixture') for p in range(1,max(x[0] for x in items)+1)),raw_blocks=blocks,cleaned_text='',sections=(),warnings=())
def case_repeated_margins():
    p=fixture([(1,20,'Journal header'),(1,100,'Body one'),(2,20,'Journal header'),(2,100,'Body two')]);v=LayoutCleaner().clean(p)
    assert v.removed==('b0','b2') and [b.text for b in v.blocks]==['Body one','Body two']
def case_page_numbers():
    p=fixture([(1,760,'1'),(1,100,'Measured 20 percent.')]);p=p.model_copy(update={'raw_blocks':(p.raw_blocks[0].model_copy(update={'bbox':(295.,760.,305.,770.)}),p.raw_blocks[1])});v=LayoutCleaner().clean(p)
    assert v.removed==('b0',) and '20' in v.blocks[0].text
def case_join_mapping():
    p=fixture([(1,100,'charac-\nterization')]);v=LayoutCleaner().clean(p);b=v.blocks[0]
    assert b.text=='characterization'
    assert b.raw_ranges(0,len(b.text))==((0,6),(8,18))
def case_chemical_hyphen():
    p=fixture([(1,100,'metal-organic framework and 2-\nmethylimidazole')]);v=LayoutCleaner().clean(p)
    assert 'metal-organic' in v.blocks[0].text and '2-' in v.blocks[0].text
    assert p.raw_blocks[0].text.endswith('methylimidazole')
def case_unique_body():
    p=fixture([(1,20,'Unique title'),(1,100,'  Titanium  dioxide\nwas used. ')]);cleaner=LayoutCleaner();v=cleaner.clean(p)
    assert not v.removed and v.blocks[1].text=='Titanium dioxide was used.'
    assert cleaner.apply(p).raw_blocks==p.raw_blocks

def case_whitespace_raw_snippets():
    from extractors.common import snippets_from_clean
    p=fixture([(1,100,'Titanium   dioxide\nwas used.')]);b=LayoutCleaner().clean(p).blocks[0]
    assert isinstance(b.spans,list) and len(b.spans)<len(b.text)
    refs=snippets_from_clean(p,b,ExtractionField.METHODS,'test')
    assert len(refs)==1 and refs[0].text==p.raw_blocks[0].text
    assert all(s.text==p.raw_blocks[0].text[s.start_offset:s.end_offset] for s in refs)
def case_dehyphenation_raw_snippets():
    from extractors.common import snippets_from_clean
    p=fixture([(1,100,'charac-\nterization')]);b=LayoutCleaner().clean(p).blocks[0]
    refs=snippets_from_clean(p,b,ExtractionField.METHODS,'test')
    assert len(refs)==2 and ''.join(s.text for s in refs)=='characterization'
    assert all(s.text==p.raw_blocks[0].text[s.start_offset:s.end_offset] for s in refs)

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_repeated_margins','case_page_numbers','case_join_mapping','case_chemical_hyphen','case_unique_body','case_whitespace_raw_snippets','case_dehyphenation_raw_snippets'], globals()))
