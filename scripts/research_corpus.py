"""Process the actual Phase 1 corpus into evidence-backed scientific records."""
from pathlib import Path
import argparse, json, sys, hashlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from research.extraction import extract_pdf, record_summary

parser = argparse.ArgumentParser()
parser.add_argument("--corpus", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
papers = json.loads((args.corpus / "index.json").read_text())["papers"]
summary = []
failed = []
for meta in papers:
    try:
        record = extract_pdf(args.corpus / meta["file"], meta)
        path = args.output / (meta["id"].replace("/", "_") + ".json")
        path.write_text(json.dumps(record, ensure_ascii=False) + "\n")
        item = record_summary(record)
        item["artifact_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        item["artifact_bytes"] = path.stat().st_size
        summary.append(item)
        print(f"PASS {meta['id']} materials={len(record['materials'])} methods={len(record['methods'])} conclusions={len(record['conclusions'])} findings={len(record['findings'])} algorithms={len(record['algorithms'])} data={len(record['experimental_data'])} formulas={len(record['formulas'])} evidence={len(record['source_snippets'])}", flush=True)
    except Exception as exc:
        failed.append({"id": meta["id"], "error": type(exc).__name__, "message": str(exc) if isinstance(exc, ValueError) else "Processing failed"})
        print("FAIL", meta["id"], type(exc).__name__, flush=True)
(args.output / "index.json").write_text(json.dumps({"records": summary, "failed": failed}, ensure_ascii=False) + "\n")
print("REAL CORPUS:", len(summary), "records;", len(failed), "failed", flush=True)
raise SystemExit(int(bool(failed)))
