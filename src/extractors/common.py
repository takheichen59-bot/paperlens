"""Unified raw-span evidence generation; views are injected, never reconstructed."""
from contracts import *
from parsers.sections import eligible_blocks


def section_for(paper,block_id,*,view=None,start=0,end=None):
    if view is None:raise ContractError(Stage.PARSE,ErrorKind.VALIDATION_FAILED,False)
    return next((s for s in view.sections for bid,a,b in s.spans if bid==block_id and a<=start and (end is None or end<=b)),None)


def snippet(paper,block,field,strategy,start=0,end=None):
    end=len(block.text) if end is None else end
    raw=next(b for b in paper.raw_blocks if b.block_id==block.block_id)
    a=getattr(block,'raw_start',0)+start;b=getattr(block,'raw_start',0)+end
    return SourceSnippet(field=field,text=raw.text[a:b],page_start=raw.page_number,page_end=raw.page_number,
        section=getattr(block,'section_title',None),block_id=raw.block_id,start_offset=a,end_offset=b,strategy=strategy)


def snippets_from_clean(paper,cleaned,field,strategy,start=0,end=None,*,section=None):
    raw=next(b for b in paper.raw_blocks if b.block_id==cleaned.block_id)
    end=len(cleaned.text) if end is None else end
    return tuple(SourceSnippet(field=field,text=raw.text[a:b],page_start=raw.page_number,page_end=raw.page_number,
        section=section,block_id=raw.block_id,start_offset=a,end_offset=b,strategy=strategy) for a,b in cleaned.raw_ranges(start,end))


def result(*,chemicals=(),conclusions='',methods='',snippets=(),method,warnings=()):
    present=(bool(chemicals),bool(conclusions.strip()),bool(methods.strip()))
    return ExtractionResult(chemicals=tuple(chemicals),conclusions=conclusions,methods=methods,extraction_method=method,
        source_snippets=tuple(snippets),field_status=tuple((f,FieldStatus.FOUND if ok else FieldStatus.MISSING) for f,ok in zip(ExtractionField,present)),warnings=tuple(warnings))
