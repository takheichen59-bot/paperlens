"""Bounded methods passages; fallback requires adjacent keyword-rich body spans."""
import re
from contracts import *
from .common import result,snippet,eligible_blocks

METHOD_KEYWORDS={
 'preparation':r'\bprepar\w*\b','synthesis':r'\bsynthesi[sz]\w*\b',
 'fabrication':r'\bfabricat\w*\b','deposition':r'\bdeposit\w*\b',
 'annealing':r'\banneal\w*\b','hydrothermal':r'\bhydrothermal\b',
 'solvothermal':r'\bsolvothermal\b','heating':r'\bheated\b','stirring':r'\bstirred\b',
 'washing':r'\bwashed\b','drying':r'\bdried\b','measurement':r'\bmeasur\w*\b',
 'microscopy':r'\bmicroscop\w*\b','spectroscopy':r'\bspectroscop\w*\b',
 'diffraction':r'\bdiffraction\b','dft':r'\b(?:DFT|density functional)\b',
 'molecular_dynamics':r'\bmolecular dynamics\b','simulation':r'\bsimulat\w*\b',
 'spin_coating':r'\bspin.coat\w*\b','centrifugation':r'\bcentrifug\w*\b',
}

class MethodExtractor(BaseExtractor):
    def __init__(self,*,view=None,max_chars=3000,keywords=None):
        if type(max_chars)is not int or max_chars<1:raise ValueError('Positive method limit required')
        self.view=view;self.max_chars=max_chars;self.keywords=dict(METHOD_KEYWORDS if keywords is None else keywords)
    def with_view(self,view):return type(self)(view=view,max_chars=self.max_chars,keywords=self.keywords)
    @property
    def version(self):
        from hashlib import sha256
        import json
        return 'methods-primary-v4-'+str(self.max_chars)+'-'+sha256(json.dumps(self.keywords,sort_keys=True).encode()).hexdigest()[:10]
    def hits(self,text):return sum(bool(re.search(pattern,text,re.I)) for pattern in self.keywords.values())
    def extract(self,parsed_paper):
        blocks=eligible_blocks(parsed_paper,self.view)
        primary=any(s.kind=='methods' for s in self.view.sections)
        selected=[]
        warnings=[]
        if primary:
            # Select a continuous passage from the first available named methods
            # region, in original reading order; no global keyword fallback.
            candidates=[b for b in blocks if b.kind==SectionKind.METHODS and len(b.text.strip())>25]
            for sid in dict.fromkeys(b.section_id for b in candidates):
                region=[b for b in candidates if b.section_id==sid]
                size=0
                for b in region:
                    added=len(b.text)+(2 if selected else 0)
                    if size+added>self.max_chars:break
                    selected.append(b);size+=added
                if selected:
                    if len(selected)<len(region) or any(b.section_id!=sid for b in candidates):warnings.append('methods_primary_bounded')
                    break
            if not selected:warnings.append('missing_field:methods')
        else:
            groups=[];current=[]
            for b in blocks:
                # Abstract is not body; terminal/heading ranges were excluded by the view.
                allowed=b.kind not in {SectionKind.ABSTRACT,SectionKind.REFERENCES,SectionKind.SUPPLEMENT}
                candidate=allowed and self.hits(b.text)>=2 and not re.search(r'\b(?:aims?|objective|future work)\b',b.text,re.I)
                if not candidate or (current and current[-1].section_id!=b.section_id):
                    if len(current)>=2:groups.append(current)
                    current=[]
                if candidate:current.append(b)
            if len(current)>=2:groups.append(current)
            valid=[g for g in groups if len('\n\n'.join(b.text for b in g))<=self.max_chars]
            if valid:
                selected=valid[0];warnings.append('methods_fallback:'+selected[0].kind.value)
            elif groups:warnings.append('methods_fallback_truncated')
            else:warnings.append('methods_fallback_rejected')
        refs=tuple(snippet(parsed_paper,b,ExtractionField.METHODS,self.version) for b in selected)
        return result(methods='\n\n'.join(s.text for s in refs),snippets=refs,method=self.version,warnings=warnings)
