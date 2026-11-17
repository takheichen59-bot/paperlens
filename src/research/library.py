"""Bounded local batch processing with hash checkpoints and review overlays.

The existing SQLite schema is untouched. Immutable per-paper JSON checkpoints
and an append-only audit log are separate workspace artifacts.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import csv, hashlib, json, os, zipfile
from threading import Lock
from .locking import exclusive_lock
from xml.sax.saxutils import escape

from contracts import ContractError, Stage, ErrorKind
from exports import parse_failure_line
from extractors.warning_policy import WarningClassificationError
from .extraction import extract_pdf, validate_scientific_record, VERSION, ScientificBaselineAdapter
from parsers.sections import StructuredPDFParser

FIELDS = ["materials", "methods", "findings", "conclusions", "algorithms", "formulas", "experimental_data", "limitations"]
HEADERS = ["paper_id", "title", "materials", "methods", "findings", "conclusions", "algorithms", "formulas", "experimental_data", "limitations", "doi", "source_url", "status", "review_status", "notes"]


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".part")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def key(paper_id):
    return hashlib.sha256(paper_id.encode()).hexdigest()


class Library:
    def __init__(self, directory):
        self.directory = Path(directory)
        for folder in ("records", "reviews", "failures", "history", "state"):
            (self.directory / folder).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def writer(self):
        with exclusive_lock(self.directory / "writer.lock"):
            yield

    def event(self, value):
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **value}, ensure_ascii=False) + "\n")
            handle.flush(); os.fsync(handle.fileno())

    def run(self, items, *, workers=2, extractor=extract_pdf, max_items=5000, stop_after=None):
        if not 1 <= workers <= 8 or not 1 <= max_items <= 5000:
            raise ValueError("workers must be 1–8; max_items 1–5000")
        stats = {"submitted": 0, "processed": 0, "resumed": 0, "duplicates": 0, "failed": 0}
        seen = set(); seen_hashes = set(); seen_dois = set(); pending = []
        parser_version = StructuredPDFParser().version + ScientificBaselineAdapter(None).version; parser_lock = Lock()
        def process(item):
            meta = dict(item["meta"]); pid = meta["paper_id"]; path = Path(item["pdf"])
            target = self.directory / "records" / (key(pid) + ".json")
            state_path = self.directory / "state" / (key(pid) + ".json")
            digest = item.get("_hash") or checksum(path)
            fingerprint = hashlib.sha256((digest + parser_version + VERSION + json.dumps(meta,sort_keys=True,ensure_ascii=False)).encode()).hexdigest()
            if target.exists():
                old = json.loads(target.read_text())
                if old.get("fingerprint") == fingerprint:
                    validate_scientific_record(old["record"])
                    (self.directory / "failures" / (key(pid) + ".json")).unlink(missing_ok=True)
                    atomic_json(state_path, {"status":"CURRENT", "fingerprint":fingerprint})
                    return pid, "resumed", None
                historical=self.directory/"history"/key(pid)/(old["fingerprint"]+".json")
                if not historical.exists(): atomic_json(historical,old)
            atomic_json(state_path,{"status":"STALE","fingerprint":fingerprint})
            # PyMuPDF does not support concurrent threads entering its parser.
            with parser_lock:
                result = extractor(path, meta)
            validate_scientific_record(result)
            if result["pdf_hash"] != digest:
                raise ValueError("Record hash does not match the input file")
            validate_scientific_record(result)
            atomic_json(target, {"fingerprint": fingerprint, "record": result})
            atomic_json(state_path,{"status":"CURRENT","fingerprint":fingerprint})
            (self.directory / "failures" / (key(pid) + ".json")).unlink(missing_ok=True)
            return pid, "processed", result
        def drain():
            for pid, future in pending:
                try:
                    _, state, _ = future.result(); stats[state] += 1
                    self.event({"paper_id": pid, "status": state})
                except Exception as exc:
                    stats["failed"] += 1
                    error = exc if isinstance(exc, ContractError) else ContractError(Stage.EXTRACT, ErrorKind.EXTRACT_FAILED, False)
                    failure = {"paper_id": pid, "status": "failed", **error.to_dict(), "attempts": 1,
                        "reason": "warning_classification_error" if isinstance(exc, WarningClassificationError) else type(exc).__name__}
                    parse_failure_line(failure)
                    atomic_json(self.directory / "failures" / (key(pid) + ".json"), failure)
                    self.event(failure)
            pending.clear()
        with self.writer(), ThreadPoolExecutor(max_workers=workers) as executor:
            for item in items:
                if stop_after is not None and stats["submitted"] >= stop_after:
                    break
                try:
                    if type(item) is not dict or type(item.get("meta")) is not dict: raise ValueError()
                    pid=item["meta"]["paper_id"]
                    if type(pid) is not str or not pid.strip() or "pdf" not in item: raise ValueError()
                except (KeyError,ValueError,TypeError):
                    stats["submitted"]+=1;stats["failed"]+=1
                    failure={"paper_id":None,"status":"failed",**ContractError(Stage.VALIDATE,ErrorKind.VALIDATION_FAILED,False).to_dict(),"reason":"invalid_manifest_item","attempts":1}
                    atomic_json(self.directory/"failures"/("input-"+uuid4().hex+".json"),failure);self.event(failure)
                    continue
                if pid in seen:
                    stats["duplicates"] += 1; continue
                doi = (item["meta"].get("doi") or "").lower()
                if doi and doi in seen_dois:
                    stats["duplicates"] += 1; continue
                try:
                    digest = checksum(item["pdf"])
                    if digest in seen_hashes:
                        stats["duplicates"] += 1; continue
                    seen_hashes.add(digest); item = {**item, "_hash": digest}
                except OSError:
                    pass  # The per-paper boundary records missing files as failures.
                if stats["submitted"] >= max_items:
                    raise ValueError("Manifest exceeds max_items; split into batches")
                seen.add(pid)
                if doi: seen_dois.add(doi)
                stats["submitted"] += 1
                pending.append((pid, executor.submit(process, item)))
                if len(pending) >= workers*2:
                    drain()
            drain()
        return stats

    def records(self):
        for path in sorted((self.directory / "records").glob("*.json")):
            envelope = json.loads(path.read_text())
            record = envelope["record"]
            state_path=self.directory/"state"/(key(record["paper_id"])+".json")
            if state_path.exists():
                state=json.loads(state_path.read_text())
                if state.get("status")!="CURRENT" or state.get("fingerprint")!=envelope["fingerprint"]: continue
            if (self.directory / "failures" / (key(record["paper_id"]) + ".json")).exists():
                continue
            overlay = self.directory / "reviews" / (key(record["paper_id"]) + ".json")
            if overlay.exists():
                saved = json.loads(overlay.read_text())
                if saved.get("pdf_hash") == record["pdf_hash"]:
                    record["review"] = saved
                else:
                    record["previous_review"] = saved
            yield record

    def review(self, paper_id, *, edits=None, decision="reviewed", note=""):
        if decision not in {"reviewed", "needs_review"} or set(edits or {}) - set(FIELDS[:4]):
            raise ValueError("Unsupported review decision or field")
        edits = edits or {}
        if any((field == "materials" and (type(value) is not list or any(type(x) is not str for x in value)))
               or (field != "materials" and type(value) is not str) for field, value in edits.items()):
            raise ValueError("Review field type mismatch")
        if not (self.directory / "records" / (key(paper_id) + ".json")).exists():
            raise ValueError("Unknown paper")
        overlay = {"paper_id": paper_id, "decision": decision, "edits": edits, "note": note,
                   "updated_at": datetime.now(timezone.utc).isoformat(), "source": "human", "pdf_hash": json.loads((self.directory / "records" / (key(paper_id) + ".json")).read_text())["record"]["pdf_hash"]}
        with self.writer():
            atomic_json(self.directory / "reviews" / (key(paper_id) + ".json"), overlay)
            self.event({"paper_id": paper_id, "status": "review_updated"})
        return overlay

    def export(self, output):
        with self.writer():
            return self._export_snapshot(output)

    def history(self, paper_id):
        return tuple(json.loads(p.read_text()) for p in sorted((self.directory/"history"/key(paper_id)).glob("*.json")))

    def _export_snapshot(self, output):
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        version = uuid4().hex; directory = output / "versions" / version; directory.mkdir(parents=True)
        count = 0
        with (directory / "research.jsonl").open("w", encoding="utf-8") as full, \
             (directory / "results.jsonl").open("w", encoding="utf-8") as legacy, \
             (directory / "review.jsonl").open("w", encoding="utf-8") as review, \
             (directory / "research.csv").open("w", encoding="utf-8-sig", newline="") as table:
            writer = csv.writer(table); writer.writerow(HEADERS)
            for record in self.records():
                count += 1; full.write(json.dumps(record, ensure_ascii=False) + "\n")
                legacy.write(json.dumps(record["legacy_record"], ensure_ascii=False) + "\n")
                writer.writerow([csv_safe(v) for v in table_row(record)])
                if record.get("review", {}).get("decision") != "reviewed":
                    review.write(json.dumps({"paper_id": record["paper_id"], "reason": "manual_scientific_review_required",
                        "missing_fields": [f for f in FIELDS[:4] if not record[f]]}, ensure_ascii=False) + "\n")
        with (directory / "failures.jsonl").open("w", encoding="utf-8") as failures:
            for path in sorted((self.directory / "failures").glob("*.json")):
                parse_failure_line(json.loads(path.read_text()))
                failures.write(path.read_text().strip() + "\n")
        write_xlsx(directory / "research.xlsx", self.records())
        manifest = {"version": version, "records": count, "directory": str(directory.resolve()),
            "files": {p.name: checksum(p) for p in directory.iterdir() if p.is_file()}}
        atomic_json(directory / "manifest.json", manifest)
        atomic_json(output / "CURRENT.json", manifest)
        return manifest


def current_output(destination):
    return json.loads((Path(destination) / "CURRENT.json").read_text())


def table_row(record):
    overlay = record.get("review", {}); values = {f: record[f] for f in FIELDS}
    values.update(overlay.get("edits", {}))
    return [record["paper_id"], record["meta"].get("title", ""), "; ".join(values["materials"]),
        values["methods"], values["findings"], values["conclusions"],
        "; ".join(a["name"] for a in record["algorithms"]),
        "\n".join(a["text"] for a in record["formulas"]), "\n".join(a["text"] for a in record["experimental_data"]),
        values["limitations"], record["meta"].get("doi") or "", record["meta"].get("url", ""), record["status"],
        overlay.get("decision", "unreviewed"), overlay.get("note", "")]


def csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def write_xlsx(path, records):
    def cell(value, style=0):
        text = re_xml(str(value))[:32760]
        return '<c t="inlineStr" s="'+str(style)+'"><is><t xml:space="preserve">' + escape(text) + '</t></is></c>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
        z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Research" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr('xl/styles.xml','<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs></styleSheet>')
        with z.open("xl/worksheets/sheet1.xml", "w") as sheet:
            widths=[20,52,28,65,65,65,30,50,65,50,30,48,15,20,40]
            cols='<cols>'+''.join(f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i,width in enumerate(widths,1))+'</cols>'
            sheet.write(('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'+cols+'<sheetData>').encode())
            sheet.write(('<row r="1" ht="30" customHeight="1">' + ''.join(cell(v,1) for v in ['论文ID','论文标题','材料 / 化学物','研究方法','主要发现','结论','算法 / 计算方法','公式候选','数值 / 实验数据候选','局限候选','DOI','原文链接','结构状态','复核状态','复核备注']) + '</row>').encode())
            count=1
            for record in records:
                count+=1
                sheet.write((f'<row r="{count}" ht="90" customHeight="1">' + ''.join(cell(v) for v in table_row(record)) + '</row>').encode())
            sheet.write(('</sheetData><autoFilter ref="A1:O'+str(count)+'"/></worksheet>').encode())


def re_xml(text):
    import re
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
