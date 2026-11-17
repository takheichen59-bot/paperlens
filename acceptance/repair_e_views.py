"""Five offline repair scenarios; no real-paper ground truth enters acceptance."""
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parents[1]/'scripts')]
from _support import run_cases
from _text_fixtures import paper
from parsers.sections import SectionIdentifier
from extractors.composite import CompositeExtractor,status_for
from contracts import validate_record
from audit_leakage import audit_paper

def extract(lines):
    p,v=SectionIdentifier().identify_with_view(paper(lines));r=CompositeExtractor(view=v).extract(p)
    return p,v,r

def record(r):
    value={'doi':None,'title':'Fixture','source_url':'https://arxiv.org/abs/2401.00001',
        **{k:r.model_dump(mode='json')[k] for k in ('chemicals','conclusions','methods','extraction_method','source_snippets')},'status':status_for(r).value}
    checked=validate_record(value);assert checked.valid;return checked.record

def case_data_availability_excluded():
    p,v,r=extract(['Conclusions','The coating improved resistance.','Data availability statement','Graphene and TiO2 datasets are available.'])
    assert not r.chemicals and r.conclusions=='The coating improved resistance.'
    assert p.raw_blocks[-1].text=='Graphene and TiO2 datasets are available.'

def case_author_contributions_excluded():
    p,v,r=extract(['Methods','Samples were prepared at 180 C.','Author contributions','Graphene was prepared by the project administrator.'])
    assert not r.chemicals and 'administrator' not in r.methods+r.conclusions

def case_conflicts_boundary():
    p,v,r=extract(['Methods','Titanium dioxide was prepared at 180 C.','Conflicts of interest','Ethanol was supplied by the sponsor.','References','Methanol was cited.'])
    assert r.chemicals==('Titanium dioxide',) and p.sections[-1].title=='References'

def case_known_introduction_auditable():
    p,v,r=extract(['Introduction','Graphene is a protective coating material.'])
    audit=audit_paper(p.paper_id,record(r),(p,v),[],None)
    assert audit['audit_status']=='decided' and audit['decided']>=1 and not audit['leaks']

def case_unlabelled_stays_unresolved():
    p,v,r=extract(['Graphene is discussed in this unlabelled passage.'])
    audit=audit_paper(p.paper_id,record(r),(p,v),[],None)
    assert audit['audit_status']=='unresolved' and audit['unresolved']>=1 and audit['unresolved_reasons']

if __name__=='__main__':
    raise SystemExit(run_cases(['case_data_availability_excluded','case_author_contributions_excluded',
        'case_conflicts_boundary','case_known_introduction_auditable','case_unlabelled_stays_unresolved'],globals()))
