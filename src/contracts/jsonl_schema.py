"""JSONL boundary validation; this module performs no file I/O or exports."""
import json
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator
from .enums import ExtractionField, ResultStatus
from .models import NonEmpty, SourceSnippet, validate_doi, validate_url


class JSONLRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    doi: str | None
    title: str
    source_url: str
    chemicals: tuple[NonEmpty, ...]
    conclusions: str
    methods: str
    extraction_method: str
    source_snippets: tuple[SourceSnippet, ...]
    status: ResultStatus

    _doi = field_validator("doi")(validate_doi)
    @field_validator("source_url")
    @classmethod
    def source_url_or_empty(cls, value: str) -> str:
        return validate_url(value) if value else value


class RecordValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    valid: bool
    record: JSONLRecord | None
    errors: tuple[str, ...]

    @model_validator(mode="after")
    def consistent_result(self):
        if self.valid:
            if self.record is None or self.errors:
                raise ValueError("Valid result requires a record and no errors")
        elif self.record is not None or not self.errors:
            raise ValueError("Invalid result requires errors and no record")
        return self


def _evidence_errors(record: JSONLRecord) -> tuple[str, ...]:
    errors = []
    present = {
        ExtractionField.CHEMICALS: bool(record.chemicals),
        ExtractionField.CONCLUSIONS: bool(record.conclusions.strip()),
        ExtractionField.METHODS: bool(record.methods.strip()),
    }
    supported = []
    for field in ExtractionField:
        snippets = tuple(s for s in record.source_snippets if s.field == field)
        if present[field] != bool(snippets):
            errors.append(f"evidence_presence_mismatch:{field.value}")
        # Structural association only: raw PDF blocks are not available here.
        if field == ExtractionField.CHEMICALS:
            if snippets and any(not any(c.casefold() in s.text.casefold() for s in snippets)
                                for c in record.chemicals):
                errors.append("chemical_not_supported_by_snippets")
        else:
            value = getattr(record, field.value)
            if any(s.text not in value for s in snippets):
                errors.append(f"snippet_not_in_field:{field.value}")
        supported.append(present[field] and bool(snippets))
    count = sum(supported)
    if record.status == ResultStatus.SUCCESS and count != 3:
        errors.append("success_requires_three_supported_fields")
    elif record.status == ResultStatus.PARTIAL and count < 1:
        errors.append("partial_requires_supported_field")
    elif record.status == ResultStatus.FAILED and count != 0:
        errors.append("failed_cannot_have_supported_fields")
    return tuple(errors)


def validate_record(record: dict) -> RecordValidationResult:
    """Construct JSONLRecord first, then check field/evidence/status consistency.

    Accept JSON-compatible dictionaries. JSON-mode strict validation deliberately
    permits JSON arrays for tuple fields and wire strings for enums. Invalid
    results never contain an exportable record. Errors contain controlled codes
    only, never input values or Pydantic's input-bearing exception text.
    """
    if type(record) is not dict:
        return RecordValidationResult(valid=False, record=None,
                                      errors=("record_must_be_dict",))
    try:
        payload = json.dumps(record, ensure_ascii=False, allow_nan=False)
        parsed = JSONLRecord.model_validate_json(payload)
    except ValidationError as exc:
        # Pydantic errors may include arbitrary user input, keys and contexts.
        # Retain only a total count; do not stringify or return those details.
        return RecordValidationResult(valid=False, record=None,
                                      errors=(f"schema_validation_failed:{exc.error_count()}",))
    except (TypeError, ValueError, OverflowError, RecursionError):
        return RecordValidationResult(valid=False, record=None,
                                      errors=("record_is_not_json_compatible",))
    errors = _evidence_errors(parsed)
    if errors:
        return RecordValidationResult(valid=False, record=None, errors=errors)
    return RecordValidationResult(valid=True, record=parsed, errors=())
