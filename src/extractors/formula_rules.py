"""Conservative formula screening, not a chemistry ontology or structure validator."""
from itertools import product
import re

KNOWN_FORMULAS=frozenset('H2 O2 N2 F2 Cl2 H2O CO2 NH3 CH4 NaCl TiO2 MoS2 CuZr CuZrAl ZrCuAl'.split())
OXIDATION={
 'H':(-1,1),'Li':(1,),'Na':(1,),'K':(1,),'Mg':(2,),'Ca':(2,),'Ba':(2,),
 'Al':(3,),'Ga':(3,),'B':(3,),'C':(-4,2,4),'Si':(-4,4),'N':(-3,3,5),
 'P':(-3,3,5),'O':(-2,),'F':(-1,),'Cl':(-1,),'Br':(-1,),'I':(-1,),
 'S':(-2,4,6),'Se':(-2,4,6),'Te':(-2,4,6),'Ti':(2,3,4),'Zr':(4,),
 'Hf':(4,),'Nb':(3,4,5),'Ta':(5,),'Mo':(2,3,4,5,6),'W':(4,6),
 'Cr':(2,3,4,6),'Mn':(2,3,4,6,7),'Fe':(2,3),'Co':(2,3),
 'Ni':(2,3),'Cu':(1,2),'Zn':(2,),'Ag':(1,),'Bi':(3,5),'Sn':(2,4),
 'Pb':(2,4),'Ge':(2,4),'As':(-3,3,5),'Sb':(-3,3,5),'In':(3,),
}
CRYSTAL_CONTEXT=re.compile(r'\b(?:planes?|reflections?|peaks?|facets?|orientations?|precession|indices)\b',re.I)


def is_formula(value,context=''):
    if re.fullmatch(r'[HKL]{2,}\d*',value) and CRYSTAL_CONTEXT.search(context):return False
    if value in KNOWN_FORMULAS:return True
    if not any(c.isdigit() or c.islower() for c in value):return False
    parts=re.findall(r'([A-Z][a-z]?)(\d*)',value)
    if ''.join(a+b for a,b in parts)!=value or not 2<=len(parts)<=8:return False
    counts=[int(n or 1) for _,n in parts]
    if any(not 1<=n<=999 for n in counts) or any(a not in OXIDATION for a,_ in parts):return False
    # A single species or an unbalanced metal combination needs a dictionary entry.
    return any(min(states)<0<max(states) and sum(n*s for n,s in zip(counts,states))==0
        for states in product(*(OXIDATION[a] for a,_ in parts)))
