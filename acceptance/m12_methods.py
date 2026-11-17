import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from extractors.methods import MethodExtractor
from _text_fixtures import paper,extract_with_view

def case_experimental():
    r=extract_with_view(MethodExtractor(),paper(['Methods','Samples were prepared by hydrothermal synthesis at 180 C.']))
    assert '180 C' in r.methods and not r.conclusions and not r.warnings
def case_computational():
    r=extract_with_view(MethodExtractor(),paper(['Computational Methods','We used density functional theory with a 500 eV cutoff.']))
    assert '500 eV' in r.methods
# Historical pre-tightening positive cases: retained, explicitly skipped below.
def historical_single_block_positive_skipped():
    r=extract_with_view(MethodExtractor(),paper(['Samples were heated at 500 C for two hours.']))
    assert '500 C' in r.methods and any('fallback' in w for w in r.warnings)
def historical_abstract_single_block_positive_skipped():
    r=extract_with_view(MethodExtractor(),paper(['Abstract','Films were deposited using spin-coating at 3000 rpm.']))
    assert '3000 rpm' in r.methods and 'methods_fallback:abstract' in r.warnings
# Active tightened-rule cases.
def case_references_only():
    r=extract_with_view(MethodExtractor(),paper(['Introduction','Our objective concerns coating behavior.','References','Samples were prepared by hydrothermal synthesis.']))
    assert r.methods=='' and r.source_snippets==()

def case_single_block_rejected():
    r=extract_with_view(MethodExtractor(),paper(['Samples were prepared and heated at 500 C for two hours.']))
    assert not r.methods and not r.source_snippets and 'methods_fallback_rejected' in r.warnings

def case_two_adjacent_blocks():
    r=extract_with_view(MethodExtractor(),paper(['Samples were prepared and heated at 500 C.','Films were washed and dried before measurement.']))
    assert '500 C' in r.methods and 'washed' in r.methods and 'methods_fallback:unknown' in r.warnings

def case_fallback_too_long():
    p=paper(['Samples were prepared and heated. '+('Detailed experimental context. '*8),'Films were washed and dried. '+('Additional experimental context. '*8)])
    r=extract_with_view(MethodExtractor(max_chars=120),p)
    assert not r.methods and not r.source_snippets and 'methods_fallback_truncated' in r.warnings

def case_cross_section_rejected():
    p=paper(['Introduction','Samples were prepared and heated at 500 C.','Results','Films were washed and dried before measurement.'])
    r=extract_with_view(MethodExtractor(),p)
    assert not r.methods and not r.source_snippets

def case_primary_region_without_keywords():
    text='The vessel temperature was 180 C and the pressure was held at 2 bar.'
    r=extract_with_view(MethodExtractor(),paper(['Methods',text,'Results','The resistance increased by twenty percent.']))
    assert r.methods==text and not r.warnings

def case_experimental_section_alias():
    text='The instrument voltage was 20 kV with a scan rate of 2 degrees per minute.'
    r=extract_with_view(MethodExtractor(),paper(['II. Experimental Section',text,'III. Results','The coating remained stable.']))
    assert r.methods==text and not any('fallback' in w for w in r.warnings)

def case_no_section_fallback_unchanged():
    r=extract_with_view(MethodExtractor(),paper(['Samples were prepared and heated at 500 C.','Films were washed and dried before measurement.']))
    assert r.methods=='Samples were prepared and heated at 500 C.\n\nFilms were washed and dried before measurement.'
    assert r.warnings==('methods_fallback:unknown',)
    rejected=extract_with_view(MethodExtractor(),paper(['Samples were prepared and heated at 500 C.']))
    assert not rejected.methods

def case_primary_bounded_whole_blocks():
    one='The vessel temperature was held at 180 C and pressure at 2 bar.'
    two='The instrument voltage was 20 kV and the scan rate was fixed.'
    r=extract_with_view(MethodExtractor(max_chars=100),paper(['Methods',one,two,'Conclusions','The material remained stable.']))
    assert r.methods==one and len(r.methods)<=100
    assert r.warnings==('methods_primary_bounded',) and len(r.source_snippets)==1

if __name__ == "__main__":
    print('SKIP historical_single_block_positive_skipped: rule tightened; original assertion retained')
    print('SKIP historical_abstract_single_block_positive_skipped: abstract is not fallback body')
    raise SystemExit(run_cases(['case_experimental','case_computational','case_single_block_rejected','case_two_adjacent_blocks','case_references_only','case_fallback_too_long','case_cross_section_rejected','case_primary_region_without_keywords','case_experimental_section_alias','case_no_section_fallback_unchanged','case_primary_bounded_whole_blocks'],globals()))
