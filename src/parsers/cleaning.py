"""Run-length cleaning spans; evidence always maps back to original raw blocks."""
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
import re
from contracts import ParsedPaper
from .pdf import is_page_number

@dataclass(frozen=True)
class CleanedBlock:
    block_id: str
    text: str
    spans: list[tuple[int,int,int,int]]

    def raw_ranges(self,start,end):
        if not 0<=start<end<=len(self.text):raise ValueError('Invalid clean interval')
        i=bisect_right(self.spans,start,key=lambda s:s[1]);ranges=[]
        while i<len(self.spans):
            cs,ce,rs,re=self.spans[i]
            if cs>=end:break
            lo,hi=max(start,cs),min(end,ce)
            if lo<hi:
                if ce-cs==re-rs:a,b=rs+lo-cs,rs+hi-cs
                else:a,b=rs,re  # one normalized whitespace char maps to its full raw run
                if ranges and ranges[-1][1]==a:ranges[-1]=(ranges[-1][0],b)
                else:ranges.append((a,b))
            i+=1
        return tuple(ranges)

@dataclass(frozen=True)
class CleanedView:
    blocks: tuple[CleanedBlock,...]
    removed: tuple[str,...]
    logs: tuple[str,...]


def clean_block(block_id,text,*,raw_start=0):
    joins=LayoutCleaner.joins
    deletions=[(m.end(1),m.start(2)) for m in re.finditer(r'([A-Za-z]+)-\s*\n\s*([A-Za-z]+)',text) if (m[1]+m[2]).lower() in joins]
    kept=[];cursor=0
    for a,b in deletions:kept.append((cursor,a));cursor=b
    kept.append((cursor,len(text)))
    parts=[];spans=[];length=0
    def emit(value,a,b):
        nonlocal length
        if not value:return
        if spans and len(value)==b-a and spans[-1][1]-spans[-1][0]==spans[-1][3]-spans[-1][2] and spans[-1][3]==a+raw_start:
            cs,_,rs,_=spans[-1];spans[-1]=(cs,length+len(value),rs,b+raw_start)
        else:spans.append((length,length+len(value),a+raw_start,b+raw_start))
        parts.append(value);length+=len(value)
    for a,b in kept:
        for m in re.finditer(r'\s+|\S+',text[a:b]):
            value=m.group();lo=a+m.start();hi=a+m.end()
            if value.isspace():
                if parts and not parts[-1].endswith(' '):emit(' ',lo,hi)
            else:emit(value,lo,hi)
    result=''.join(parts)
    if result.endswith(' '):
        result=result[:-1];cs,ce,rs,raw_end=spans[-1]
        if ce-cs==1:spans.pop()
        else:spans[-1]=(cs,ce-1,rs,raw_end-1)
    return CleanedBlock(block_id,result,spans)


class LayoutCleaner:
    version='layout-spans-margins-v3'
    joins={'characterization','preparation','synthesis','measurement'}
    def clean(self,paper:ParsedPaper,*,layout=None):
        def geometry(b):
            hint=(layout or {}).get((b.block_id,0),{})
            return hint.get('page_width',600.),hint.get('page_height',800.)
        candidates=[]
        for b in paper.raw_blocks:
            w,h=geometry(b)
            if b.bbox and (b.bbox[3]<=h*.08 or b.bbox[1]>=h*.92):candidates.append((b.page_number,b.text.strip()))
        count=Counter(text for _,text in set(candidates));removed=[];blocks=[];logs=[]
        for b in paper.raw_blocks:
            w,h=geometry(b)
            margin=b.bbox and (b.bbox[3]<=h*.08 or b.bbox[1]>=h*.92)
            if is_page_number(b.text,b.bbox,w,h) or (margin and count[b.text.strip()]>=2):
                removed.append(b.block_id);logs.append('removed_margin_or_page_number:'+b.block_id);continue
            block=clean_block(b.block_id,b.text)
            if block.text:blocks.append(block)
        return CleanedView(tuple(blocks),tuple(removed),tuple(logs))
    def apply(self,paper,*,layout=None):
        view=self.clean(paper,layout=layout)
        return paper.model_copy(update={'cleaned_text':'\n\n'.join(b.text for b in view.blocks),'warnings':paper.warnings+tuple('removed_block:'+bid for bid in view.removed)})
