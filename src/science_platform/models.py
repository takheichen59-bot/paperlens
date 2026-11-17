from __future__ import annotations
from datetime import datetime,timezone
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class StrictModel(BaseModel):
 model_config=ConfigDict(frozen=True,extra='forbid',strict=True)
class ValidationStatus(StrEnum):
 VERIFIED='VERIFIED'; NEEDS_REVIEW='NEEDS_REVIEW'; UNSUPPORTED='UNSUPPORTED'; SOURCE_NOT_AVAILABLE='SOURCE_NOT_AVAILABLE'; STALE='STALE'
class Author(StrictModel):
 name:str;orcid:str|None=None
class FullTextLink(StrictModel):
 url:str;kind:Literal['pdf','xml'];access:Literal['OPEN_ACCESS','AUTHORIZED_API','UNKNOWN']='UNKNOWN';license:str|None=None
class SourceFact(StrictModel):
 provider:str;source_id:str;retrieved_at:str;citation_count:int|None=None;venue:str|None=None;year:int|None=None
class Paper(StrictModel):
 paper_id:str;doi:str|None;title:str;authors:tuple[Author,...]=();venue:str|None=None;year:int|None=None
 citation_count:int|None=None;is_open_access:bool|None=None;abstract:str='';source_url:str
 fulltext_links:tuple[FullTextLink,...]=();references:tuple[str,...]=();sources:tuple[SourceFact,...]=()
 conflicts:tuple[str,...]=();access_status:str='METADATA_ONLY'
class SearchQuery(StrictModel):
 query:str='';doi:str|None=None;author:str|None=None;venue:str|None=None
 year_from:int|None=None;year_to:int|None=None;min_citations:int|None=None;open_access:bool|None=None
 target:int=Field(default=20,ge=1,le=5000);providers:tuple[str,...]=('crossref','openalex','semantic_scholar')
 @model_validator(mode='after')
 def bounds(self):
  if self.year_from and self.year_to and self.year_from>self.year_to:raise ValueError('Reversed year range')
  if not any((self.query.strip(),self.doi,self.author,self.venue)):raise ValueError('Search criteria required')
  return self
class SearchPage(StrictModel):
 papers:tuple[Paper,...];next_cursor:str|None=None;total:int|None=None
class Segment(StrictModel):
 segment_id:str;text:str;page:int|None;section:str|None;kind:str='paragraph';bbox:tuple[float,float,float,float]|None=None
 source_path:str|None=None
class Equation(StrictModel):
 text:str;latex:str|None=None;number:str|None=None;context_segment_ids:tuple[str,...]=()
 validation_status:ValidationStatus=ValidationStatus.NEEDS_REVIEW;parse_status:Literal['PARSED','PARSE_UNCERTAIN']='PARSE_UNCERTAIN'
class ParsedDocument(StrictModel):
 paper_id:str;document_sha256:str;parser:str;parser_version:str;segments:tuple[Segment,...]
 equations:tuple[Equation,...]=();warnings:tuple[str,...]=();alignment_conflicts:tuple[str,...]=()
class Evidence(StrictModel):
 evidence_id:str;paper_id:str;document_sha256:str;segment_id:str;page:int|None;section:str|None
 quote:str;start:int;end:int;extraction_model:str;extraction_version:str
 validation_status:ValidationStatus;validation_scope:Literal['SOURCE_SPAN_ONLY']='SOURCE_SPAN_ONLY'
class Measurement(StrictModel):
 metric:str;value:str;unit:str|None=None;dataset:str|None=None;conditions:str|None=None
class Claim(StrictModel):
 claim_id:str;text:str;evidence_ids:tuple[str,...]
 slot:Literal['general','dataset','dataset_size','baseline','metric','hyperparameter','hardware','condition','objective','constraint','theorem','proof_condition','symbol_definition','method_name']='general'
 measurements:tuple[Measurement,...]=()
 provenance:Literal['AUTHOR_CLAIM','EXPERIMENT_REPORTED','CROSS_PAPER_OBSERVATION','RESEARCH_HYPOTHESIS']='AUTHOR_CLAIM'
 support_status:ValidationStatus=ValidationStatus.NEEDS_REVIEW
class Algorithm(StrictModel):
 name:str;algorithm_type:Literal['LLM','RAG','GNN','CONSTRAINT_SOLVER','SAT_SMT','MAXSAT','MIP','FORMAL_VERIFICATION','OPTIMIZATION','PLANNING','PROOF_CHECKING','OTHER']
 novelty:Literal['AUTHOR_PROPOSED','EXISTING','NO_NEW_ALGORITHM_PROPOSED','NOT_REPORTED']
 inputs:tuple[Claim,...]=();outputs:tuple[Claim,...]=();components:tuple[Claim,...]=();procedure:tuple[Claim,...]=()
 pseudocode:tuple[Claim,...]=();objective:tuple[Claim,...]=();constraints:tuple[Claim,...]=();optimization:tuple[Claim,...]=()
 complexity:tuple[Claim,...]=();assumptions:tuple[Claim,...]=();failure_conditions:tuple[Claim,...]=();evidence_ids:tuple[str,...]=()
 analysis_depth:Literal['DEEP_STRUCTURED','MENTION_ONLY']='DEEP_STRUCTURED'
class ScientificRecord(StrictModel):
 paper_id:str;document_sha256:str;extraction_version:str;model:str;execution_status:Literal['EXECUTED','NOT_EXECUTED']
 research_problem:tuple[Claim,...]=();motivation:tuple[Claim,...]=();contributions:tuple[Claim,...]=()
 algorithms:tuple[Algorithm,...]=();mathematical_formulation:tuple[Claim,...]=();methodology:tuple[Claim,...]=()
 experimental_design:tuple[Claim,...]=();results:tuple[Claim,...]=();author_limitations:tuple[Claim,...]=()
 observed_limitations:tuple[Claim,...]=();ai_inferred_limitations:tuple[Claim,...]=();conclusions:tuple[Claim,...]=();future_work:tuple[Claim,...]=()
 evidence:tuple[Evidence,...]=();conflicts:tuple[str,...]=();missing_fields:tuple[str,...]=()
 validation_status:ValidationStatus=ValidationStatus.NEEDS_REVIEW
