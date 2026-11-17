import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
from extractors import ChemicalExtractor
from _text_fixtures import paper,extract_with_view

def case_names():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','Titanium dioxide and ethanol were used.']))
    assert r.chemicals==('Titanium dioxide','ethanol') and len(r.source_snippets)==1
def case_formulas():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','TiO2, H2O and NaCl were mixed.']))
    assert r.chemicals==('TiO2','H2O','NaCl')
def case_polymer():
    r=extract_with_view(ChemicalExtractor(),paper(['Polyethylene glycol was used.']))
    assert r.chemicals==('Polyethylene glycol',)
def case_units_and_references():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','SEM and TEM at 20 C and 4 mA.','References','Lithium chloride was reported.']))
    assert r.chemicals==() and not r.source_snippets
def case_deduplicate():
    p=paper(['Titanium dioxide was used.','TITANIUM DIOXIDE and graphene.']);r=extract_with_view(ChemicalExtractor(),p)
    assert r.chemicals==('Titanium dioxide','graphene')
    for s in r.source_snippets:
        b=next(b for b in p.raw_blocks if b.block_id==s.block_id)
        assert b.text[s.start_offset:s.end_offset]==s.text

def case_crystal_context():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','Precession images along HK0 and HK1 planes show (100) and (002) reflections.']))
    assert r.chemicals==() and not r.source_snippets

def case_valid_formulas_retained():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','TiO2 facets and MoS2 peaks were measured alongside BiFeO3 and MgSiO3.']))
    assert r.chemicals==('TiO2','MoS2','BiFeO3','MgSiO3')

def case_unbalanced_and_single_symbol_rejected():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','NaCl2, H0, K1 and CrGa are labels; H2O and NaCl were mixed.']))
    assert r.chemicals==('H2O','NaCl')

def case_uppercase_labels_rejected():
    r=extract_with_view(ChemicalExtractor(),paper(['Methods','HH domain walls and the HPCC cluster use CO notation. TiO2 was prepared.']))
    assert r.chemicals==('TiO2',)

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_names', 'case_formulas', 'case_polymer', 'case_units_and_references', 'case_deduplicate','case_crystal_context','case_valid_formulas_retained','case_unbalanced_and_single_symbol_rejected','case_uppercase_labels_rejected'], globals()))
