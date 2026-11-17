import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from contracts import *
from parsers.sections import SectionIdentifier
from extractors.composite import CompositeExtractor,validate_evidence,status_for
from extractors.warning_policy import WarningClassificationError,classify_warnings
from _text_fixtures import paper,extract_with_view

def fixture():return paper(['Methods','Titanium dioxide was prepared by hydrothermal synthesis at 180 C.','Conclusions','The coating improved corrosion resistance.'])
def case_complete():
    p=fixture();r=extract_with_view(CompositeExtractor(),p);assert status_for(r)==ResultStatus.SUCCESS
    assert r.chemicals==('Titanium dioxide',) and r.methods and r.conclusions
    record={'doi':None,'title':'Fixture','source_url':'https://example.org/p',**{k:r.model_dump(mode='json')[k] for k in ['chemicals','conclusions','methods','extraction_method','source_snippets']},'status':status_for(r).value}
    assert validate_record(record).valid
def case_missing_field():
    r=extract_with_view(CompositeExtractor(),paper(['Methods','Titanium dioxide was prepared by hydrothermal synthesis.']))
    assert status_for(r)==ResultStatus.PARTIAL and not r.conclusions
def case_no_evidence():
    r=extract_with_view(CompositeExtractor(),paper(['An ordinary bibliographic document without technical content.']))
    assert status_for(r)==ResultStatus.FAILED and not r.source_snippets
def case_invalid_location():
    p=fixture();r=extract_with_view(CompositeExtractor(),p)
    bad=tuple(s.model_copy(update={'block_id':'absent'}) for s in r.source_snippets)
    assert_rejected(lambda:validate_evidence(p,r.model_copy(update={'source_snippets':bad}),view=SectionIdentifier().identify_with_view(p)[1]))
def case_duplicate():
    p=fixture();r=extract_with_view(CompositeExtractor(),p)
    checked=validate_evidence(p,r.model_copy(update={'source_snippets':r.source_snippets+r.source_snippets}),view=SectionIdentifier().identify_with_view(p)[1])
    assert checked.source_snippets==r.source_snippets and checked.methods==r.methods

def assert_rejected(operation):
    try:operation()
    except ContractError as e:assert e.stage==Stage.VALIDATE and e.error_kind==ErrorKind.VALIDATION_FAILED
    else:raise AssertionError('invalid evidence accepted')

def wrong_candidates_for_testing():
    p,v=SectionIdentifier().identify_with_view(fixture());r=CompositeExtractor(view=v).extract(p)
    s=next(s for s in r.source_snippets if s.field==ExtractionField.CHEMICALS)
    corrupt=s.model_copy(update={'text':'Titanium dioxide','start_offset':1,'end_offset':17})
    wrong_slice=r.model_copy(update={'source_snippets':tuple(corrupt if x.field==ExtractionField.CHEMICALS else x for x in r.source_snippets)})
    missing=r.model_copy(update={'source_snippets':tuple(x for x in r.source_snippets if x.field!=ExtractionField.METHODS)})
    # Valid source locations and evidence for a genuinely long methods field.
    long_p,long_v=SectionIdentifier().identify_with_view(paper(['Methods','Samples were prepared. '+('Detailed experimental procedure. '*110),'Conclusions','The coating improved corrosion resistance.']))
    from extractors.conclusions import ConclusionExtractor
    from extractors.common import result,snippet,eligible_blocks
    refs=tuple(snippet(long_p,b,ExtractionField.METHODS,'unbounded-candidate-for-testing') for b in eligible_blocks(long_p,long_v) if b.kind==SectionKind.METHODS)
    c=ConclusionExtractor(view=long_v).extract(long_p)
    long_r=result(method='test',methods='\n\n'.join(s.text for s in refs),conclusions=c.conclusions,snippets=refs+c.source_snippets)
    return {'slice':(p,v,wrong_slice),'evidence':(p,v,missing),'length':(long_p,long_v,long_r)}

def case_wrong_slice():
    p,v,r=wrong_candidates_for_testing()['slice']
    assert_rejected(lambda:CompositeExtractor(view=v).validate_candidate(p,r))
def case_field_evidence_mismatch():
    p,v,r=wrong_candidates_for_testing()['evidence']
    assert_rejected(lambda:CompositeExtractor(view=v).validate_candidate(p,r))
    valid=CompositeExtractor(view=v).extract(p)
    empty=valid.model_copy(update={'methods':''})
    assert_rejected(lambda:CompositeExtractor(view=v).validate_candidate(p,empty))
def case_long_methods():
    p,v,r=wrong_candidates_for_testing()['length'];assert len(r.methods)>3000
    checked=CompositeExtractor(view=v).validate_candidate(p,r)
    assert checked.methods=='' and checked.conclusions==r.conclusions
    assert not any(s.field==ExtractionField.METHODS for s in checked.source_snippets)
    assert 'methods_fallback_truncated' in checked.warnings and status_for(checked)==ResultStatus.PARTIAL

def case_info_success():
    p,v=SectionIdentifier().identify_with_view(fixture())
    r=CompositeExtractor(view=v).extract(p).model_copy(update={'warnings':('page_1_possible_multicolumn',)})
    assert status_for(r)==ResultStatus.SUCCESS and classify_warnings(r).informational==r.warnings

def case_blocking_classification_error():
    p,v=SectionIdentifier().identify_with_view(fixture())
    r=CompositeExtractor(view=v).extract(p).model_copy(update={'warnings':('missing_field:methods',)})
    try:status_for(r)
    except WarningClassificationError:pass
    else:raise AssertionError('Contradictory blocking accepted')

def case_unknown_warning():
    r=extract_with_view(CompositeExtractor(),fixture()).model_copy(update={'warnings':('unregistered',)})
    try:status_for(r)
    except WarningClassificationError:pass
    else:raise AssertionError('Unknown warning accepted')

def case_long_methods_only():
    from extractors.common import result
    p,v,r=wrong_candidates_for_testing()['length']
    only=result(method='test',methods=r.methods,snippets=tuple(s for s in r.source_snippets if s.field==ExtractionField.METHODS))
    checked=CompositeExtractor(view=v).validate_candidate(p,only)
    assert status_for(checked)==ResultStatus.FAILED and not checked.methods and not checked.source_snippets
def case_production_checks_not_exposed():
    import re
    root=Path(__file__).resolve().parents[1]
    pattern=re.compile(r'enable_(?:slice|evidence|length)_check\s*=')
    for folder in ['src/paper_platform','src/pipeline','examples']:
        for path in (root/folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py','.json','.toml'}:
                assert not pattern.search(path.read_text()),str(path)

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_complete', 'case_missing_field', 'case_no_evidence', 'case_invalid_location', 'case_duplicate','case_wrong_slice','case_field_evidence_mismatch','case_long_methods','case_production_checks_not_exposed','case_info_success','case_blocking_classification_error','case_unknown_warning','case_long_methods_only'], globals()))
