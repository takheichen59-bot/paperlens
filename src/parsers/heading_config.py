"""M09 versioned heading vocabulary and structural rules."""
from contracts import SectionKind

HEADINGS={
 'abstract':SectionKind.ABSTRACT,'introduction':SectionKind.UNKNOWN,
 'method':SectionKind.METHODS,'methods':SectionKind.METHODS,
 'materials and methods':SectionKind.METHODS,'experimental':SectionKind.METHODS,
 'material and methods':SectionKind.METHODS,'synthesis':SectionKind.METHODS,
 'characterization':SectionKind.METHODS,'sample preparation':SectionKind.METHODS,
 'simulation setup':SectionKind.METHODS,'simulation methods':SectionKind.METHODS,
 'simulation details':SectionKind.METHODS,'numerical methods':SectionKind.METHODS,
 'density functional theory':SectionKind.METHODS,
 'new velocity discretization':SectionKind.METHODS,'space and time discretization':SectionKind.METHODS,
 'chapman-enskog analysis':SectionKind.METHODS,
 'experimental section':SectionKind.METHODS,'experimental methods':SectionKind.METHODS,
 'computational methods':SectionKind.METHODS,'calculation details':SectionKind.METHODS,
 'computational details':SectionKind.METHODS,'calculation methods':SectionKind.METHODS,
 'experimental details':SectionKind.METHODS,'photoluminescence spectroscopy':SectionKind.METHODS,
 'results':SectionKind.RESULTS,'discussion':SectionKind.DISCUSSION,
 'results and discussion':SectionKind.DISCUSSION,'conclusion':SectionKind.CONCLUSIONS,
 'conclusions':SectionKind.CONCLUSIONS,'summary':SectionKind.CONCLUSIONS,
 'summary and outlook':SectionKind.CONCLUSIONS,'conclusions and outlook':SectionKind.CONCLUSIONS,
 'references':SectionKind.REFERENCES,'bibliography':SectionKind.REFERENCES,
 'acknowledgments':SectionKind.REFERENCES,'acknowledgements':SectionKind.REFERENCES,
 'funding':SectionKind.REFERENCES,'supplementary information':SectionKind.SUPPLEMENT,
 'data availability':SectionKind.REFERENCES,'data availability statement':SectionKind.REFERENCES,
 'code availability':SectionKind.REFERENCES,'author contributions':SectionKind.REFERENCES,
 'conflict of interest':SectionKind.REFERENCES,'conflicts of interest':SectionKind.REFERENCES,
 'declaration of competing interest':SectionKind.REFERENCES,'competing interests':SectionKind.REFERENCES,
}
ROMAN_SINGLE_WORDS={'methods','results','discussion','conclusion','conclusions','references','acknowledgments','acknowledgements','experimental','synthesis','characterization'}
HEADING_PATTERNS=((r'growth of .+',SectionKind.METHODS),(r'numerical simulation of .+',SectionKind.METHODS))
ROMAN_NUMBER=r'M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})'
