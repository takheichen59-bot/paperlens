"""Seven top-level and four nested immutable Pydantic v2 data objects.

Python constructors require tuples and enum instances. Use model_validate_json
at JSON boundaries: strict JSON arrays become tuples, and ISO dates/times and
enum wire strings are accepted without enabling Python-side coercion.
"""
from datetime import date, datetime
from pathlib import Path
import re
from typing import Annotated, Self
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .enums import (ErrorKind, ExtractionField, FieldStatus, InputType,
                    SectionKind, Source, Stage, StageStatus)

NonEmpty = Annotated[str, Field(min_length=1, pattern=r"\S")]
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Positive = Annotated[int, Field(ge=1)]


def validate_doi(value: str | None) -> str | None:
    if value is not None and not re.fullmatch(r"10\.\d{4,9}/\S+", value, re.I):
        raise ValueError("DOI must be a DOI identifier, not a URL")
    return value.lower() if value is not None else None


def validate_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if (parts.scheme not in {"http", "https"} or not parts.hostname
                or parts.username is not None or parts.password is not None
                or any(c.isspace() for c in value)):
            raise ValueError
        _ = parts.port
    except ValueError:
        raise ValueError("Expected an HTTP(S) URL without credentials") from None
    return value


def aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return value


class PageText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    page_number: Positive
    text: str


class TextBlock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    block_id: NonEmpty
    page_number: Positive
    text: str
    bbox: tuple[float, float, float, float] | None

    @field_validator("bbox")
    @classmethod
    def check_bbox(cls, value):
        if value is not None:
            import math
            if not all(math.isfinite(x) for x in value) or value[0] > value[2] or value[1] > value[3]:
                raise ValueError("Invalid bounding box")
        return value


class Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    section_id: NonEmpty
    title: str
    kind: SectionKind
    # Ordered raw block IDs, not a mutable mapping or a set.
    value: tuple[NonEmpty, ...]
    page_start: Positive
    page_end: Positive

    @model_validator(mode="after")
    def ordered_pages(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("Section page range is reversed")
        return self


class SourceSnippet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    field: ExtractionField
    text: NonEmpty
    page_start: Positive
    page_end: Positive
    section: NonEmpty | None
    block_id: NonEmpty
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=1)]
    strategy: NonEmpty

    @model_validator(mode="after")
    def check_ranges(self) -> Self:
        if self.page_end != self.page_start:
            raise ValueError("Split cross-page evidence into separate snippets")
        if self.end_offset <= self.start_offset:
            raise ValueError("Snippet offsets must describe a nonempty half-open range")
        if self.end_offset - self.start_offset != len(self.text):
            raise ValueError("Snippet offsets must match the original text length")
        return self


class PaperQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    input_type: InputType
    query_value: NonEmpty
    category: NonEmpty | None
    max_results: Positive
    date_from: date | None
    date_to: date | None

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not exceed date_to")
        return self


class PaperRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    source: Source
    source_id: NonEmpty
    version: NonEmpty | None


class PaperMeta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    paper_id: NonEmpty
    source_id: NonEmpty
    doi: str | None
    title: NonEmpty
    page_url: str
    pdf_url: str
    version: NonEmpty | None
    fetched_at: datetime

    _doi = field_validator("doi")(validate_doi)
    _urls = field_validator("page_url", "pdf_url")(validate_url)
    _time = field_validator("fetched_at")(aware)


class DownloadArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    pdf_path: Path
    content_hash: SHA256
    bytes: Positive
    downloaded_at: datetime

    _time = field_validator("downloaded_at")(aware)


class ParsedPaper(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    paper_id: NonEmpty
    pdf_hash: SHA256
    pages: tuple[PageText, ...]
    raw_blocks: tuple[TextBlock, ...]
    cleaned_text: str
    sections: tuple[Section, ...]
    warnings: tuple[NonEmpty, ...]

    @model_validator(mode="after")
    def check_references(self) -> Self:
        page_numbers = tuple(p.page_number for p in self.pages)
        if page_numbers != tuple(range(1, len(self.pages) + 1)):
            raise ValueError("Pages must be ordered and numbered consecutively from one")
        blocks = {b.block_id: b for b in self.raw_blocks}
        if len(blocks) != len(self.raw_blocks):
            raise ValueError("Duplicate block IDs")
        if any(b.page_number not in page_numbers for b in self.raw_blocks):
            raise ValueError("Block refers to a missing page")
        if len({s.section_id for s in self.sections}) != len(self.sections):
            raise ValueError("Duplicate section IDs")
        for section in self.sections:
            if section.page_start not in page_numbers or section.page_end not in page_numbers:
                raise ValueError("Section refers to a missing page")
            for block_id in section.value:
                if block_id not in blocks or not section.page_start <= blocks[block_id].page_number <= section.page_end:
                    raise ValueError("Section refers to a missing or out-of-range block")
        return self


class ExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    chemicals: tuple[NonEmpty, ...]
    conclusions: str
    methods: str
    extraction_method: NonEmpty
    source_snippets: tuple[SourceSnippet, ...]
    # Ordered (field, status) pairs preserve deep immutability.
    field_status: tuple[tuple[ExtractionField, FieldStatus], ...]
    warnings: tuple[NonEmpty, ...]

    @field_validator("field_status")
    @classmethod
    def complete_statuses(cls, value):
        names = tuple(field for field, _ in value)
        if len(names) != 3 or set(names) != set(ExtractionField):
            raise ValueError("field_status must contain each extraction field exactly once")
        return value


class TaskRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    task_id: NonEmpty
    paper_id: NonEmpty
    stage: Stage
    stage_status: StageStatus
    attempts: Annotated[int, Field(ge=0)]
    config_fingerprint: SHA256
    # Classification only; raw exceptions must never enter serialized task data.
    error: ErrorKind | None
