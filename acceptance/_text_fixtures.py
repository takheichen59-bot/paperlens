from contracts import *
from parsers.sections import SectionIdentifier


def paper(lines):
    blocks=tuple(TextBlock(block_id=f'b{i}',page_number=1,text=t,bbox=None) for i,t in enumerate(lines))
    return SectionIdentifier().identify(ParsedPaper(paper_id='fixture',pdf_hash='a'*64,
        pages=(PageText(page_number=1,text='\n'.join(lines)),),raw_blocks=blocks,
        cleaned_text='\n\n'.join(lines),sections=(),warnings=()))


def extract_with_view(extractor,p):
    parsed,view=SectionIdentifier().identify_with_view(p)
    return extractor.with_view(view).extract(parsed)
