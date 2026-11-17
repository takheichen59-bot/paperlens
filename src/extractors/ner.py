"""Optional NER protocol and deterministic mock; never downloads a model."""
from abc import ABC,abstractmethod
from dataclasses import dataclass
from contracts import *
from .chemicals import ChemicalExtractor
from .common import snippet,eligible_blocks


@dataclass(frozen=True)
class Entity:
    text:str
    start:int
    end:int


class NERAdapter(ABC):
    @abstractmethod
    def recognize(self,block)->tuple[Entity,...]:raise NotImplementedError


class MockNER(NERAdapter):
    def __init__(self,entities=None,*,fail=False):self.entities=entities or {};self.fail=fail
    def recognize(self,block):
        if self.fail:raise RuntimeError('mock NER failure')
        return tuple(self.entities.get(block.block_id,()))


class NERChemicalExtractor(BaseExtractor):
    def __init__(self,adapter=None,baseline=None,*,view=None):
        self.adapter=adapter;self.view=view;self.baseline=(baseline or ChemicalExtractor()).with_view(view)
    def with_view(self,view):return type(self)(self.adapter,self.baseline,view=view)
    @property
    def version(self):return self.baseline.version+'+ner-mock-v1' if self.adapter else self.baseline.version+'+ner-off'
    def extract(self,parsed_paper):
        base=self.baseline.extract(parsed_paper)
        if self.adapter is None:return base.model_copy(update={'extraction_method':self.version})
        names=list(base.chemicals);snippets=list(base.source_snippets);warnings=list(base.warnings)
        seen={n.casefold() for n in names}
        for block in eligible_blocks(parsed_paper,self.view):
            try:entities=self.adapter.recognize(block)
            except Exception:warnings.append('ner_failed:'+block.block_id);continue
            for entity in entities:
                if type(entity.start) is not int or type(entity.end) is not int or not 0<=entity.start<entity.end<=len(block.text) or block.text[entity.start:entity.end]!=entity.text or not entity.text.strip():
                    warnings.append('ner_invalid_offset:'+block.block_id);continue
                if entity.text.casefold() in seen:continue
                overlap=False
                for old in names:
                    start=block.text.casefold().find(old.casefold())
                    if start>=0 and max(start,entity.start)<min(start+len(old),entity.end):overlap=True
                if overlap:warnings.append('ner_overlap:'+block.block_id);continue
                names.append(entity.text);seen.add(entity.text.casefold())
                snippets.append(snippet(parsed_paper,block,ExtractionField.CHEMICALS,self.version,entity.start,entity.end))
        statuses=tuple((f,FieldStatus.FOUND if f==ExtractionField.CHEMICALS and names else FieldStatus.MISSING) for f in ExtractionField)
        return base.model_copy(update={'chemicals':tuple(names),'source_snippets':tuple(snippets),'warnings':tuple(warnings),'field_status':statuses,'extraction_method':self.version})
