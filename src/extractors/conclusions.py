"""Extract author conclusion passages without inventing scientific implications."""
import re
from contracts import *
from .common import result,snippet,eligible_blocks,section_for

SUMMARY=re.compile(r'\b(?:in conclusion|in summary|we conclude|these results (?:show|suggest|indicate|demonstrate)|our findings|these findings)\b',re.I)
PURPOSE=re.compile(r'\b(?:aims? to|objective|purpose|we investigate|we aim)\b',re.I)


class ConclusionExtractor(BaseExtractor):
    def __init__(self,*,view=None):self.view=view
    def with_view(self,view):return type(self)(view=view)
    @property
    def version(self):return 'conclusions-sections-v1'
    def extract(self,parsed_paper):
        blocks=eligible_blocks(parsed_paper,self.view)
        selected=[b for b in blocks if b.kind==SectionKind.CONCLUSIONS and len(b.text)>20 and not PURPOSE.search(b.text)]
        warnings=[]
        if not selected:
            selected=[b for b in blocks if len(b.text)>20 and SUMMARY.search(b.text) and not PURPOSE.search(b.text)]
            if selected:warnings.append('conclusions_fallback')
        return result(conclusions='\n\n'.join(b.text for b in selected),snippets=tuple(snippet(parsed_paper,b,ExtractionField.CONCLUSIONS,self.version) for b in selected),method=self.version,warnings=warnings)
