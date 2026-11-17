"""Public M01 contracts. Importing this package performs no business I/O."""
from .models import (PaperQuery, PaperRef, PaperMeta, DownloadArtifact,
                     ParsedPaper, ExtractionResult, TaskRecord,
                     PageText, TextBlock, Section, SourceSnippet)
from .interfaces import BaseFetcher, BaseParser, BaseExtractor
from .enums import (InputType, Source, Stage, StageStatus, ResultStatus, ErrorKind,
                    ExtractionField, FieldStatus, SectionKind)
from .errors import ContractError
from .jsonl_schema import JSONLRecord, RecordValidationResult, validate_record

__all__ = [
    "PaperQuery", "PaperRef", "PaperMeta", "DownloadArtifact", "ParsedPaper",
    "ExtractionResult", "TaskRecord", "PageText", "TextBlock", "Section",
    "SourceSnippet", "BaseFetcher", "BaseParser", "BaseExtractor", "InputType",
    "Source", "Stage", "StageStatus", "ResultStatus", "ErrorKind",
    "ExtractionField", "FieldStatus", "SectionKind", "ContractError",
    "JSONLRecord", "RecordValidationResult", "validate_record",
]
