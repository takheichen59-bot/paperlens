"""Wire values shared by contracts; no pipeline implementation."""
from enum import StrEnum


class InputType(StrEnum):
    QUERY = "query"
    ARXIV_ID = "arxiv_id"
    ARXIV_URL = "arxiv_url"
    DOI = "doi"


class Source(StrEnum):
    ARXIV = "arxiv"


class Stage(StrEnum):
    SEARCH = "search"
    METADATA = "metadata"
    DOWNLOAD = "download"
    PARSE = "parse"
    EXTRACT = "extract"
    VALIDATE = "validate"
    EXPORT = "export"
    STORAGE = "storage"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ErrorKind(StrEnum):
    NOT_FOUND = "not_found"
    AMBIGUOUS_INPUT = "ambiguous_input"
    RATE_LIMITED = "rate_limited"
    NETWORK_TIMEOUT = "network_timeout"
    INVALID_DOWNLOAD = "invalid_download"
    PDF_CORRUPTED = "pdf_corrupted"
    NEEDS_OCR = "needs_ocr"
    PARSE_FAILED = "parse_failed"
    EXTRACT_FAILED = "extract_failed"
    VALIDATION_FAILED = "validation_failed"
    UNKNOWN = "unknown"


class ExtractionField(StrEnum):
    CHEMICALS = "chemicals"
    CONCLUSIONS = "conclusions"
    METHODS = "methods"


class FieldStatus(StrEnum):
    FOUND = "found"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"


class SectionKind(StrEnum):
    ABSTRACT = "abstract"
    METHODS = "methods"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSIONS = "conclusions"
    REFERENCES = "references"
    SUPPLEMENT = "supplement"
    UNKNOWN = "unknown"
