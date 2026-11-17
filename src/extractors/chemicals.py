"""Dictionary/formula candidates only; no entity normalization or inference."""
import json,re
from hashlib import sha256
from pathlib import Path
from contracts import *
from .common import result,snippet,eligible_blocks
from .formula_rules import is_formula

ELEMENTS=set('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi'.split())


class ChemicalExtractor(BaseExtractor):
    def __init__(self,terms=None,*,view=None):
        self.view=view
        self.terms=tuple(terms) if terms is not None else tuple(json.loads(Path(__file__).with_name('chemicals.json').read_text()))
    def with_view(self,view):return type(self)(self.terms,view=view)
    @property
    def version(self):return 'chemicals-valence-v3-'+sha256(json.dumps(self.terms).encode()).hexdigest()[:12]
    def extract(self,parsed_paper):
        names=[];seen=set();evidence=[]
        for block in eligible_blocks(parsed_paper,self.view):
            matches=[]
            for term in self.terms:
                for m in re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',block.text,re.I):matches.append((m.start(),m.group()))
            for m in re.finditer(r'\b(?:[A-Z][a-z]?\d*){1,}\b',block.text):
                if is_formula(m.group(),block.text[max(0,m.start()-100):m.end()+100]):
                    matches.append((m.start(),m.group()))
            if matches:evidence.append(snippet(parsed_paper,block,ExtractionField.CHEMICALS,self.version))
            for _,name in sorted(matches,key=lambda x:x[0]):
                if name.casefold() not in seen:names.append(name);seen.add(name.casefold())
        return result(chemicals=names,snippets=evidence,method=self.version)
