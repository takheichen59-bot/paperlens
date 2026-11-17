"""Evidence validation policy. Production construction keeps every check enabled."""
from contracts import *
from .ner import NERChemicalExtractor
from .methods import MethodExtractor
from .conclusions import ConclusionExtractor
from .common import result,eligible_blocks
from .warning_policy import classify_warnings


def status_for(value):
    severity=classify_warnings(value)
    count=sum((bool(value.chemicals),bool(value.conclusions.strip()),bool(value.methods.strip())))
    if not count:return ResultStatus.FAILED
    evidence=all(any(s.field==field for s in value.source_snippets) for field in ExtractionField)
    return ResultStatus.SUCCESS if count==3 and evidence and not severity.blocking else ResultStatus.PARTIAL


def validate_evidence(paper,value,*,view=None,max_methods_chars=3000,enable_slice_check=True,enable_evidence_check=True,enable_length_check=True):
    blocks={b.block_id:b for b in paper.raw_blocks};allowed=eligible_blocks(paper,view)
    valid=[];seen=set()
    def reject():raise ContractError(Stage.VALIDATE,ErrorKind.VALIDATION_FAILED,False)
    for s in value.source_snippets:
        if enable_slice_check:
            b=blocks.get(s.block_id)
            if (b is None or s.page_start!=b.page_number or s.page_end!=b.page_number
                or not 0<=s.start_offset<s.end_offset<=len(b.text)
                or b.text[s.start_offset:s.end_offset]!=s.text
                or not any(a.block_id==s.block_id and a.raw_start<=s.start_offset<s.end_offset<=a.raw_end for a in allowed)):
                reject()
        key=(s.field,s.block_id,s.start_offset,s.end_offset,s.text)
        if key not in seen:valid.append(s);seen.add(key)
    if enable_evidence_check:
        for field in ExtractionField:
            snippets=[s for s in valid if s.field==field]
            content=getattr(value,field.value)
            present=bool(content) if field==ExtractionField.CHEMICALS else bool(content.strip())
            if present!=bool(snippets):reject()
            if field==ExtractionField.CHEMICALS:
                if any(not any(c.casefold() in s.text.casefold() for s in snippets) for c in content):reject()
            elif content!='\n\n'.join(dict.fromkeys(s.text for s in snippets)):reject()
    warnings=list(value.warnings)
    methods=value.methods
    if enable_length_check and len(methods)>max_methods_chars:
        methods=''
        valid=[s for s in valid if s.field!=ExtractionField.METHODS]
        warnings.append('methods_fallback_truncated')
    for field in ExtractionField:
        content=methods if field==ExtractionField.METHODS else getattr(value,field.value)
        if not content:warnings.append('missing_field:'+field.value)
    checked=result(chemicals=value.chemicals,conclusions=value.conclusions,methods=methods,snippets=valid,
        method=value.extraction_method,warnings=tuple(dict.fromkeys(warnings)))
    classify_warnings(checked)
    return checked


class CompositeExtractor(BaseExtractor):
    def __init__(self,chemical=None,methods=None,conclusions=None,*,view=None,max_methods_chars=3000,
                 enable_slice_check=True,enable_evidence_check=True,enable_length_check=True):
        if type(max_methods_chars)is not int or max_methods_chars<1:raise ValueError('Positive method limit required')
        if any(type(v)is not bool for v in (enable_slice_check,enable_evidence_check,enable_length_check)):raise TypeError('Checks require bool')
        self.view=view;self.max_methods_chars=max_methods_chars
        self._checks=dict(enable_slice_check=enable_slice_check,enable_evidence_check=enable_evidence_check,enable_length_check=enable_length_check)
        self.chemical=(chemical or NERChemicalExtractor()).with_view(view)
        self.methods=(methods or MethodExtractor(max_chars=max_methods_chars)).with_view(view)
        self.conclusions=(conclusions or ConclusionExtractor()).with_view(view)
    def with_view(self,view):return type(self)(self.chemical,self.methods,self.conclusions,view=view,max_methods_chars=self.max_methods_chars,**self._checks)
    @property
    def version(self):return '+'.join(x.version for x in (self.chemical,self.methods,self.conclusions))+f'+strict-evidence-v4-severity:{self.max_methods_chars}:'+''.join(str(int(v)) for v in self._checks.values())
    def validate_candidate(self,paper,value):
        return validate_evidence(paper,value,view=self.view,max_methods_chars=self.max_methods_chars,**self._checks)
    def extract(self,parsed_paper):
        c=self.chemical.extract(parsed_paper);m=self.methods.extract(parsed_paper);s=self.conclusions.extract(parsed_paper)
        warnings=tuple(w for w in parsed_paper.warnings if not w.startswith('removed_block:'))+c.warnings+m.warnings+s.warnings
        combined=result(chemicals=c.chemicals,conclusions=s.conclusions,methods=m.methods,snippets=c.source_snippets+m.source_snippets+s.source_snippets,method=self.version,warnings=warnings)
        return self.validate_candidate(parsed_paper,combined)
