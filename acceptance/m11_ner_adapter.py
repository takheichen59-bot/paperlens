import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from extractors.ner import Entity,MockNER,NERChemicalExtractor
from _text_fixtures import paper,extract_with_view

def case_disabled():
    r=extract_with_view(NERChemicalExtractor(),paper(['Titanium dioxide was used.']));assert r.chemicals==('Titanium dioxide',)
def case_duplicate_and_new():
    p=paper(['Titanium dioxide and quercetin were used.'])
    r=extract_with_view(NERChemicalExtractor(MockNER({'b0':(Entity('Titanium dioxide',0,16),Entity('quercetin',21,30))})),p)
    assert r.chemicals==('Titanium dioxide','quercetin')
def case_overlap():
    p=paper(['Titanium dioxide was used.'])
    r=extract_with_view(NERChemicalExtractor(MockNER({'b0':(Entity('dioxide',9,16),)})),p)
    assert r.chemicals==('Titanium dioxide',) and 'ner_overlap:b0' in r.warnings
def case_invalid_offset():
    r=extract_with_view(NERChemicalExtractor(MockNER({'b0':(Entity('fabricated',0,10),)})),paper(['Titanium dioxide was used.']))
    assert r.chemicals==('Titanium dioxide',) and 'ner_invalid_offset:b0' in r.warnings
def case_failure():
    r=extract_with_view(NERChemicalExtractor(MockNER(fail=True)),paper(['Titanium dioxide was used.']))
    assert r.chemicals==('Titanium dioxide',) and 'ner_failed:b0' in r.warnings

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_disabled', 'case_duplicate_and_new', 'case_overlap', 'case_invalid_offset', 'case_failure'], globals()))
