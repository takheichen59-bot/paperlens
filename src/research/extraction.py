"""Evidence-first scientific records. All quotations point to immutable PDF blocks.

Numerical data and equations are explicitly candidates, never interpreted results.
No external model, inferred measurement, fabricated summary or synthetic citation.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re

from contracts import ExtractionField, BaseExtractor
from contracts.jsonl_schema import validate_record
from extractors.composite import CompositeExtractor, status_for
from extractors.common import result
from parsers.sections import StructuredPDFParser, eligible_blocks
from .attribution import build_attribution, validate_attribution

VERSION = "scientific-evidence-v1.2"


class ScientificBaselineAdapter(BaseExtractor):
    """Use frozen strategies and validation, deduplicating repeated passage text.

    Repeated raw blocks retain their evidence; stable text deduplication aligns
    the candidate with M14's existing required text assembly. No checks disabled.
    """
    def __init__(self, view):
        self.baseline = CompositeExtractor(view=view)

    @property
    def version(self):
        return self.baseline.version + "+stable-passage-assembly"

    def extract(self, parsed_paper):
        c = self.baseline.chemical.extract(parsed_paper)
        m = self.baseline.methods.extract(parsed_paper)
        s = self.baseline.conclusions.extract(parsed_paper)
        candidate = result(chemicals=c.chemicals,
            methods="\n\n".join(dict.fromkeys(x.text for x in m.source_snippets if x.field == ExtractionField.METHODS)),
            conclusions="\n\n".join(dict.fromkeys(x.text for x in s.source_snippets if x.field == ExtractionField.CONCLUSIONS)),
            snippets=c.source_snippets + m.source_snippets + s.source_snippets,
            method=self.version, warnings=tuple(w for w in parsed_paper.warnings if not w.startswith("removed_block:"))
                + c.warnings + m.warnings + s.warnings)
        return self.baseline.validate_candidate(parsed_paper, candidate)
ALGORITHMS = {
    "density functional theory": r"\b(?:DFT|density[ -]functional theory)\b",
    "molecular dynamics": r"\bmolecular dynamics\b",
    "Monte Carlo": r"\bMonte[ -]Carlo\b",
    "finite element method": r"\b(?:finite element|FEM)\b",
    "random forest": r"\brandom forests?\b",
    "neural network": r"\b(?:neural networks?|deep learning)\b",
    "support vector machine": r"\b(?:support vector machines?|SVM)\b",
    "Gaussian process": r"\bGaussian processes?\b|\bGaussian process\b",
    "gradient boosting": r"\b(?:gradient boosting|XGBoost)\b",
    "nudged elastic band": r"\b(?:nudged elastic band|NEB)\b",
    "PBE functional": r"\b(?:PBE|Perdew.Burke.Ernzerhof)\b",
    "HSE functional": r"\bHSE(?:06)?\b",
}
FINDING = re.compile(r"\b(?:we(?: have)? (?:find|found|show(?:ed|n)?|observ(?:e|ed))|results? (?:show|indicate|suggest)|demonstrat\w*|reveal\w*|improv\w*|enhanc\w*|achiev\w*|exhibit\w*|increas\w*|decreas\w*)\b", re.I)
LIMITATION = re.compile(r"\b(?:limitation|limited by|remain(?:s)? (?:unclear|unknown)|future work|further (?:work|research)|not (?:considered|included)|beyond the scope)\b", re.I)
MEASUREMENT = re.compile(r"(?<![\w.])([−-]?\d+(?:\.\d+)?(?:\s*[×x]\s*10[−-]?\d+)?)\s*(GPa|MPa|kPa|mAh\s*g[−-]?1|mAh|mS\s*cm[−-]?1|S\s*cm[−-]?1|W\s*m[−-]?1\s*K[−-]?1|meV|eV|nm|μm|µm|mm|cm|mV|mA|GHz|THz|MHz|kHz|Hz|°C|K|%|Å|wt\.?\s*%)\b|(?<!\w)(\d+(?:\.\d+)?)\s*(%)", re.I)
EQUATION = re.compile(r"[=≡≈∝].*(?:\d|[α-ωΑ-Ω∂∇Σ∑∫]|\b[A-Za-z]\b)")


def sentence_ranges(text):
    """Keep exact raw characters, including line breaks; no offset-changing cleanup."""
    start = 0
    for match in re.finditer(r"[.!?](?=\s+[A-Z]|\s*$)", text):
        end = match.end()
        a = start
        while a < end and text[a].isspace():
            a += 1
        if end > a:
            yield a, end
        start = end
    while start < len(text) and text[start].isspace():
        start += 1
    if start < len(text):
        end = len(text.rstrip())
        if end > start:
            yield start, end


def enrich(paper, view, base, meta):
    raw = {b.block_id: b for b in paper.raw_blocks}
    body = eligible_blocks(paper, view)
    evidence = []
    def quote(block, field, start=0, end=None):
        end = len(block.text) if end is None else end
        a = block.raw_start + start
        z = block.raw_start + end
        b = raw[block.block_id]
        item = {"evidence_id": "e" + str(len(evidence) + 1), "field": field,
                "text": b.text[a:z], "block_id": b.block_id, "start_offset": a, "end_offset": z,
                "page_start": b.page_number, "page_end": b.page_number,
                "section": block.section_title, "section_kind": block.kind.value,
                "strategy": VERSION}
        evidence.append(item)
        return item
    for snippet in base.source_snippets:
        value = snippet.model_dump(mode="json")
        value["evidence_id"] = "e" + str(len(evidence) + 1)
        value["section_kind"] = next((b.kind.value for b in body if b.block_id == snippet.block_id
            and b.raw_start <= snippet.start_offset < snippet.end_offset <= b.raw_end), "unknown")
        evidence.append(value)
    algorithms = []
    for name, expression in ALGORITHMS.items():
        found = next(((b, m) for b in body for m in [re.search(expression, b.text, re.I)] if m), None)
        if found:
            block, match = found
            item = quote(block, "algorithms", max(0, match.start() - 90), min(len(block.text), match.end() + 150))
            algorithms.append({"name": name, "evidence_ids": [item["evidence_id"]]})
    findings = []
    candidates = [b for b in body if b.kind.value in {"results", "discussion", "conclusions"}]
    if not candidates:
        candidates = [b for b in body if b.kind.value not in {"methods", "abstract"}]
    for block in candidates:
        for a, z in sentence_ranges(block.text):
            text = block.text[a:z]
            if 35 <= len(text) <= 900 and FINDING.search(text) and len(findings) < 5:
                findings.append(quote(block, "findings", a, z))
    limitations = []
    for block in body:
        for a, z in sentence_ranges(block.text):
            if 30 <= z - a <= 900 and LIMITATION.search(block.text[a:z]) and len(limitations) < 4:
                limitations.append(quote(block, "limitations", a, z))
    data = []
    formulas = []
    for block in body:
        for a, z in sentence_ranges(block.text):
            text = block.text[a:z]
            if not 12 <= len(text) <= 700:
                continue
            matches = list(MEASUREMENT.finditer(text))
            if matches and len(data) < 16:
                item = quote(block, "experimental_data", a, z)
                data.append({"text": text, "values": [{"value": m[1] or m[3], "unit": m[2] or m[4]} for m in matches[:8]],
                    "interpretation": "numeric_candidate_not_normalized", "evidence_ids": [item["evidence_id"]]})
        offset = 0
        for line in block.text.splitlines(keepends=True):
            text = line.strip()
            if 4 <= len(text) <= 180 and EQUATION.search(text) and len(formulas) < 12:
                start = offset + line.index(text)
                item = quote(block, "formulas", start, start + len(text))
                formulas.append({"text": text, "format": "pdf_text_candidate", "evidence_ids": [item["evidence_id"]]})
            offset += len(line)
    legacy = {"doi": meta.get("doi"), "title": meta.get("title", ""), "source_url": meta.get("url", ""),
        "chemicals": list(base.chemicals), "methods": base.methods, "conclusions": base.conclusions,
        "extraction_method": base.extraction_method, "source_snippets": [s.model_dump(mode="json") for s in base.source_snippets],
        "status": status_for(base).value}
    checked = validate_record(legacy)
    if not checked.valid:
        raise ValueError("Legacy record validation failed: " + ",".join(checked.errors))
    record = {"schema_version": "research-1", "paper_id": meta.get("paper_id", paper.paper_id),
        "id": meta.get("id", paper.paper_id), "meta": meta, "pdf_hash": paper.pdf_hash,
        "parser_version": view.parser_version, "extractor_version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "materials": list(base.chemicals), "methods": base.methods, "conclusions": base.conclusions,
        "findings": "\n\n".join(x["text"] for x in findings), "algorithms": algorithms,
        "formulas": formulas, "experimental_data": data,
        "limitations": "\n\n".join(x["text"] for x in limitations), "source_snippets": evidence,
        "raw_blocks": [{"block_id": b.block_id, "page": b.page_number, "text": b.text} for b in paper.raw_blocks],
        "eligible_ranges": [{"block_id": b.block_id, "start": b.raw_start, "end": b.raw_end,
                             "section_kind": b.kind.value} for b in body],
        "status": legacy["status"], "review_status": "unreviewed", "warnings": list(base.warnings),
        "legacy_record": legacy}
    record["attribution"] = build_attribution(record, body, quote, sentence_ranges)
    validate_scientific_record(record)
    return record


def validate_scientific_record(record):
    if record.get("schema_version") != "research-1":
        raise ValueError("Unsupported scientific schema")
    raw = {b["block_id"]: b for b in record["raw_blocks"]}
    if len(raw) != len(record["raw_blocks"]):
        raise ValueError("Duplicate raw block ID")
    snippets = record["source_snippets"]
    ids = {s["evidence_id"] for s in snippets}
    if len(ids) != len(snippets):
        raise ValueError("Duplicate evidence ID")
    for s in snippets:
        b = raw.get(s["block_id"])
        a, z = s["start_offset"], s["end_offset"]
        if (not b or type(a) is not int or type(z) is not int or not 0 <= a < z <= len(b["text"])
            or b["text"][a:z] != s["text"] or s["page_start"] != b["page"] or s["page_end"] != b["page"]):
            raise ValueError("Evidence raw slice mismatch")
        if not any(x["block_id"] == s["block_id"] and x["start"] <= a < z <= x["end"]
                   and x["section_kind"] not in {"references", "supplement"} for x in record["eligible_ranges"]):
            raise ValueError("Evidence is outside extraction view")
    for field in ("materials", "methods", "conclusions", "findings", "limitations", "algorithms", "formulas", "experimental_data"):
        target = "chemicals" if field == "materials" else field
        supported = [s for s in snippets if s["field"] == target]
        if bool(record[field]) != bool(supported):
            raise ValueError("Field evidence presence mismatch: " + field)
        if isinstance(record[field], str) and record[field] != "\n\n".join(dict.fromkeys(s["text"] for s in supported)):
            raise ValueError("Field contradicts evidence: " + field)
    by_id = {s["evidence_id"]: s for s in snippets}
    for field in ("algorithms", "formulas", "experimental_data"):
        for value in record[field]:
            if not value["evidence_ids"] or any(eid not in ids or by_id[eid]["field"] != field for eid in value["evidence_ids"]):
                raise ValueError("Candidate lacks field-specific evidence")
            if field != "algorithms" and not any(by_id[eid]["text"] == value["text"] for eid in value["evidence_ids"]):
                raise ValueError("Candidate contradicts evidence")
    if len(record["methods"]) > 3000:
        raise ValueError("Methods passage exceeds policy")
    validate_attribution(record)
    return record


def extract_pdf(path, meta):
    parser = StructuredPDFParser()
    paper, view = parser.parse_with_view(Path(path))
    paper = paper.model_copy(update={"paper_id": meta.get("paper_id", paper.paper_id)})
    base = ScientificBaselineAdapter(view).extract(paper)
    return enrich(paper, view, base, meta)


def record_summary(record):
    return {k: v for k, v in record.items() if k not in {"raw_blocks", "eligible_ranges", "legacy_record"}}
