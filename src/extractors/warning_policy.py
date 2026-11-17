"""Registered warning policy; independent of frozen wire contracts.

See docs/diagnosis/WARNINGS_INVENTORY.md. A blocking message describes an
actually unavailable field, never a reason to discard otherwise valid evidence.
"""
from dataclasses import dataclass
import re
from contracts import ContractError, ErrorKind, ExtractionField, Stage


class WarningClassificationError(ContractError):
    def __init__(self):
        super().__init__(Stage.VALIDATE, ErrorKind.VALIDATION_FAILED, False)


@dataclass(frozen=True)
class WarningsBySeverity:
    informational: tuple[str, ...]
    blocking: tuple[str, ...]


INFORMATIONAL = frozenset({
    'sections_unknown', 'conclusions_fallback', 'llm_input_limit', 'llm_timeout',
    'llm_response_rejected', 'llm_evidence_rejected','methods_primary_bounded',
})
INFORMATIONAL_PATTERNS = tuple(re.compile(p) for p in (
    r'page_[1-9]\d*_(?:possible_multicolumn|no_text)',
    r'removed_block:.+', r'caption_block:.+', r'ner_(?:failed|invalid_offset|overlap):.+',
    r'methods_fallback:(?:unknown|methods|results|discussion|conclusions)',
))
METHODS_UNAVAILABLE = frozenset({'methods_fallback_truncated', 'methods_fallback_rejected'})
ALL_UNAVAILABLE = frozenset({'operation_failed', 'warning_classification_error'})


def classify_warnings(value) -> WarningsBySeverity:
    info, block = [], []
    present = {f: bool(getattr(value, f.value)) if f == ExtractionField.CHEMICALS
               else bool(getattr(value, f.value).strip()) for f in ExtractionField}
    evidence = {f: any(s.field == f for s in value.source_snippets) for f in ExtractionField}
    for code in value.warnings:
        if code in INFORMATIONAL or any(p.fullmatch(code) for p in INFORMATIONAL_PATTERNS):
            info.append(code)
            continue
        if code in METHODS_UNAVAILABLE:
            affected = (ExtractionField.METHODS,)
        elif code.startswith('missing_field:'):
            try:
                affected = (ExtractionField(code.removeprefix('missing_field:')),)
            except ValueError:
                raise WarningClassificationError() from None
        elif code in ALL_UNAVAILABLE:
            affected = tuple(ExtractionField)
        else:
            raise WarningClassificationError()
        if any(present[f] or evidence[f] for f in affected):
            raise WarningClassificationError()
        block.append(code)
    return WarningsBySeverity(tuple(info), tuple(block))
