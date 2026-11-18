"""Offset section views. Raw blocks are never rewritten or attached private state."""
from dataclasses import dataclass,asdict,replace
import json,re
from contracts import *
from .pdf import PDFParser
from .cleaning import LayoutCleaner
from .reading_order import ordered_blocks,role_key

from .heading_config import HEADINGS,ROMAN_SINGLE_WORDS,ROMAN_NUMBER,HEADING_PATTERNS

@dataclass(frozen=True)
class ViewSection:
    section_id:str
    title:str
    kind:str
    spans:list[tuple[str,int,int]]

@dataclass(frozen=True)
class SectionView:
    pdf_hash:str
    parser_version:str
    sections:tuple[ViewSection,...]
    excluded:tuple[tuple[str,int,int],...]
    def to_dict(self):return asdict(self)
    @classmethod
    def from_dict(cls,value):
        if set(value)!={'pdf_hash','parser_version','sections','excluded'}:raise ValueError('Invalid section view')
        sections=tuple(ViewSection(s['section_id'],s['title'],s['kind'],[tuple(r) for r in s['spans']]) for s in value['sections'])
        return cls(value['pdf_hash'],value['parser_version'],sections,tuple(tuple(r) for r in value['excluded']))
    def validate(self,paper):
        if self.pdf_hash!=paper.pdf_hash or not self.parser_version:raise ValueError('Section view identity mismatch')
        raw={b.block_id:b for b in paper.raw_blocks};coverage={bid:[] for bid in raw}
        if tuple(s.section_id for s in self.sections)!=tuple(s.section_id for s in paper.sections):raise ValueError('Section IDs mismatch')
        for sec,contract in zip(self.sections,paper.sections):
            if (sec.title,sec.kind)!=(contract.title,contract.kind.value):raise ValueError('Section metadata mismatch')
            for bid,a,b in sec.spans:
                if bid not in raw or type(a)is not int or type(b)is not int or not 0<=a<b<=len(raw[bid].text):raise ValueError('Invalid section range')
                coverage[bid].append((a,b))
        for bid,ranges in coverage.items():
            cursor=0
            for a,b in sorted(ranges):
                if a!=cursor:raise ValueError('Section coverage gap or overlap')
                cursor=b
            if cursor!=len(raw[bid].text):raise ValueError('Section coverage incomplete')
        for bid,a,b in self.excluded:
            if bid not in raw or not 0<=a<b<=len(raw[bid].text):raise ValueError('Invalid exclusion')
        return self

@dataclass(frozen=True)
class BodySpan:
    block_id:str
    page_number:int
    text:str
    raw_start:int
    raw_end:int
    section_id:str
    kind:SectionKind
    section_title:str|None
    bbox:object=None

class SectionIdentifier:
    version='section-method-backmatter-v6'
    def heading(self,text,*,hint=None):
        original=text.strip()
        if not original or len(original)>=80:return None
        if hint is not None:
            if not hint.get('line_start') or not hint.get('independent'):return None
            if not (hint.get('bold') or hint.get('size',0)>=hint.get('body_size',10)*1.08):return None
        roman=re.fullmatch(r'([IVXLCDM]+)\.\s+(.+)',original,re.I)
        if roman:
            if not re.fullmatch(ROMAN_NUMBER,roman[1],re.I) or original.endswith('.'):return None
            candidate=roman[2].strip().lower()
            if len(candidate.split())<2 and candidate not in ROMAN_SINGLE_WORDS:return None
        else:candidate=re.sub(r'^(?:\d+(?:\.\d+)*[.)]?|[A-Z][.)])\s+','',original).lower().rstrip(':.')
        if candidate in HEADINGS:return HEADINGS[candidate]
        matched=next((kind for pattern,kind in HEADING_PATTERNS if re.fullmatch(pattern,candidate)),None)
        if matched is not None:return matched
        # A structurally strong numbered heading still terminates a candidate region
        # when its vocabulary is unknown. Ordinary sentences cannot do so.
        if (hint and hint.get('bold') and not original.endswith(('.',',',';'))
            and re.match(r'^(?:\d+(?:\.\d+)*[.)]?|[IVXLCDM]+\.|[A-Z]\.)\s+',original)
            and 1<=len(candidate.split())<=8 and not re.search(r'[=∑∂]',candidate)):
            return SectionKind.UNKNOWN
        return None
    def identify_with_view(self,paper,layout=None):
        records=[];excluded=[];current={'title':'','kind':SectionKind.UNKNOWN,'spans':[],'body':False};terminal=False
        removed={w.removeprefix('removed_block:') for w in paper.warnings if w.startswith('removed_block:')}
        raw_by_id={b.block_id:b for b in paper.raw_blocks}
        def finish():
            if current['spans']:records.append((current['title'],current['kind'],tuple(current['spans'])))
        ordered,roles=ordered_blocks(paper,layout)
        captions=[]
        for block_index,block in enumerate(ordered):
            if role_key(block) in roles:
                current['spans'].append((block.block_id,block.raw_start,block.raw_end))
                excluded.append((block.block_id,block.raw_start,block.raw_end))
                if roles[role_key(block)]=='caption':captions.append('caption_block:'+block.block_id)
                continue
            offset=block.raw_start
            for line in block.text.splitlines(keepends=True):
                end=offset+len(line);kind=self.heading(line,hint=(layout or {}).get((block.block_id,offset)))
                # Citation lists without a printed heading: require the first numbered entry
                # plus a following numbered entry, not an inline citation occurrence.
                inferred=False
                if kind is None and not terminal and re.match(r'^\s*\[1\]\s+[A-Z]',line):
                    following='\n'.join(b.text for b in ordered[block_index:])
                    if re.search(r'(?m)^\s*\[2\]\s+[A-Z]',following):kind=SectionKind.REFERENCES;inferred=True
                if kind is not None and (not terminal or kind in {SectionKind.REFERENCES,SectionKind.SUPPLEMENT}):
                    alias_only=current['spans'] and not current['body'] and current['kind']==kind
                    if not alias_only:
                        finish();current={'title':'References (inferred)' if inferred else line.strip(),'kind':kind,'spans':[],'body':False}
                    if kind in {SectionKind.REFERENCES,SectionKind.SUPPLEMENT}:terminal=True
                    excluded.append((block.block_id,offset,end))
                elif line.strip():current['body']=True
                spans=current['spans']
                if spans and spans[-1][0]==block.block_id and spans[-1][2]==offset:
                    spans[-1]=(block.block_id,spans[-1][1],end)
                else:spans.append((block.block_id,offset,end))
                offset=end
            if block.block_id in removed and block.text:excluded.append((block.block_id,0,len(block.text)))
        finish();sections=[];views=[]
        for i,(title,kind,spans) in enumerate(records,1):
            sid=f's{i}';ids=tuple(dict.fromkeys(bid for bid,_,_ in spans))
            sections.append(Section(section_id=sid,title=title,kind=kind,value=ids,page_start=raw_by_id[ids[0]].page_number,page_end=raw_by_id[ids[-1]].page_number))
            views.append(ViewSection(sid,title,kind.value,list(spans)))
        warnings=tuple(w for w in paper.warnings if w!='sections_unknown' and not w.startswith('caption_block:'))+tuple(dict.fromkeys(captions))
        if not any(s.kind!=SectionKind.UNKNOWN for s in sections):warnings+=('sections_unknown',)
        output=paper.model_copy(update={'sections':tuple(sections),'warnings':warnings})
        view=SectionView(paper.pdf_hash,self.version,tuple(views),tuple(excluded)).validate(output)
        return output,view
    def identify(self,paper):return self.identify_with_view(paper)[0]


def eligible_blocks(paper,view=None):
    if view is None:raise ContractError(Stage.PARSE,ErrorKind.VALIDATION_FAILED,False)
    view.validate(paper);blocks={b.block_id:b for b in paper.raw_blocks};result=[]
    for section in view.sections:
        if SectionKind(section.kind) in {SectionKind.REFERENCES,SectionKind.SUPPLEMENT}:continue
        for bid,start,end in section.spans:
            intervals=[(start,end)]
            for eid,a,b in view.excluded:
                if eid!=bid:continue
                intervals=[(lo,hi) for x,y in intervals for lo,hi in ((x,min(y,a)),(max(x,b),y)) if lo<hi]
            for a,b in intervals:
                raw=blocks[bid];text=raw.text[a:b]
                if text.strip():result.append(BodySpan(bid,raw.page_number,text,a,b,section.section_id,SectionKind(section.kind),section.title or None,raw.bbox))
    return tuple(result)

class StructuredPDFParser(BaseParser):
    def __init__(self):self.reader=PDFParser();self.cleaner=LayoutCleaner();self.identifier=SectionIdentifier()
    @property
    def version(self):return self.reader.version+'+'+self.cleaner.version+'+'+self.identifier.version+'+sparse-columns-v1'
    def parse_with_view(self,pdf_path):
        raw=self.reader.parse(pdf_path);layout=self.reader.layout_hints(pdf_path)
        paper,view=self.identifier.identify_with_view(self.cleaner.apply(raw,layout=layout),layout)
        return paper,replace(view,parser_version=self.version)
    def parse(self,pdf_path):return self.parse_with_view(pdf_path)[0]
