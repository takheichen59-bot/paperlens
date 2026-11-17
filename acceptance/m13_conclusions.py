import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from extractors.conclusions import ConclusionExtractor
from _text_fixtures import paper,extract_with_view

def case_conclusion_section():
    r=extract_with_view(ConclusionExtractor(),paper(['Conclusions','The coating improved corrosion resistance by 20 percent.']))
    assert '20 percent' in r.conclusions and not r.methods and not r.warnings
def case_summary_heading():
    r=extract_with_view(ConclusionExtractor(),paper(['Summary','The material remained stable under the tested conditions.']))
    assert 'tested conditions' in r.conclusions
def case_discussion_fallback():
    r=extract_with_view(ConclusionExtractor(),paper(['Discussion','These results suggest a useful route to stable coatings.']))
    assert r.conclusions and 'conclusions_fallback' in r.warnings
def case_purpose_only():
    r=extract_with_view(ConclusionExtractor(),paper(['Abstract','Our objective is to investigate stable coatings.','References','In conclusion, other authors found stability.']))
    assert not r.conclusions and not r.source_snippets
def case_negative_limitations():
    text='The coating did not improve resistance beyond 80 C under these conditions.'
    r=extract_with_view(ConclusionExtractor(),paper(['Conclusions',text]));assert r.conclusions==text

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_conclusion_section', 'case_summary_heading', 'case_discussion_fallback', 'case_purpose_only', 'case_negative_limitations'], globals()))
