"""Independent research CLI; old paperlens commands and interfaces are unchanged."""
from pathlib import Path
import argparse, asyncio, hashlib, json, re
from datetime import datetime, timezone
from .library import Library
from .analysis import search, answer, graph


def manifest(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        with path.open(encoding="utf-8-sig") as handle:
            for line in handle:
                if line.strip():
                    item = json.loads(line); item["pdf"] = str((path.parent / item["pdf"]).resolve()); yield item
    else:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(value, dict) and "papers" in value:
            for paper in value["papers"]:
                yield {"meta": paper, "pdf": str((path.parent / paper["file"]).resolve())}
        else:
            for item in value:
                item["pdf"] = str((path.parent / item["pdf"]).resolve()); yield item


async def sync(args):
    from fetchers import ArxivFetcher
    from fetchers.pdf_download import DownloadSizeLimit
    from contracts import ContractError, Stage, ErrorKind
    from exports import parse_failure_line
    import feedparser
    fetcher = ArxivFetcher(max_pdf_bytes=args.max_pdf_mib*1048576)
    destination = Path(args.workdir) / "acquired"; destination.mkdir(parents=True, exist_ok=True)
    items = []; failures = []; excluded = []; seen = set(); max_candidates = min(30000, args.count*10)
    try:
        for start in range(0, max_candidates, 100):
            query = "cat:" + args.category
            if args.query:
                query += ' AND all:"' + args.query.replace('"', ' ') + '"'
            response = await fetcher._get(fetcher.endpoint, params={"search_query": query,
                "start": str(start), "max_results": "100", "sortBy": "submittedDate", "sortOrder": "descending"})
            metas = fetcher._parse(response.content)
            entries = {e.id.rsplit("/abs/",1)[-1]: e for e in feedparser.parse(response.content).entries}
            if not metas:
                break
            for meta in metas:
                if meta.paper_id in seen: continue
                seen.add(meta.paper_id)
                try:
                    response = await fetcher._get(meta.page_url)
                    match = re.search(r'<div class="abs-license">\s*<a href="([^"]+)"', response.text)
                    license_url = match[1].replace("http:", "https:") if match else ""
                    if not license_url.startswith("https://creativecommons.org/"):
                        excluded.append({"paper_id": meta.paper_id, "status": "excluded", "reason": "unverified_cc_license", "source_url": meta.page_url}); continue
                    artifact = await fetcher.download(meta, destination / "PDF")
                    info = meta.model_dump(mode="json")
                    info.update(id=meta.source_id+(meta.version or ""), url=meta.page_url, license_url=license_url, source="arxiv")
                    entry = entries.get(info["id"], {})
                    info.update(authors=[a.get("name", "") for a in entry.get("authors", [])], year=entry.get("published", "")[:4], categories=[t.get("term", "") for t in entry.get("tags", [])])
                    items.append({"meta": info, "pdf": str(artifact.pdf_path.resolve())})
                    print(json.dumps({"downloaded": len(items), "target": args.count, "id": info["id"]}), flush=True)
                    if len(items) >= args.count: break
                except DownloadSizeLimit as exc:
                    failures.append({"paper_id": meta.paper_id, "stage": "download", "error_kind": "invalid_download", **exc.audit()})
                except Exception as exc:
                    error = exc if isinstance(exc, ContractError) else ContractError(Stage.DOWNLOAD, ErrorKind.INVALID_DOWNLOAD, False)
                    failures.append({"paper_id": meta.paper_id, "status": "failed", **error.to_dict(), "reason": type(exc).__name__})
            if len(items) >= args.count: break
    finally: await fetcher.aclose()
    path = destination / "manifest.jsonl"
    path.write_text("".join(json.dumps(item, ensure_ascii=False)+"\n" for item in items))
    for failure in failures: parse_failure_line(failure)
    (destination / "license_exclusions.jsonl").write_text("".join(json.dumps(item)+"\n" for item in excluded))
    (destination / "download_failures.jsonl").write_text("".join(json.dumps(item)+"\n" for item in failures))
    report = Library(args.workdir).run(items, workers=args.workers)
    exported = Library(args.workdir).export(args.output)
    print(json.dumps({**report, "downloaded": len(items), "target": args.count, "output": exported}, ensure_ascii=False))
    return 0 if len(items) == args.count and report["failed"] == 0 else 1


def main():
    parser = argparse.ArgumentParser(prog="paperlens-research", description="Batch scientific extraction, evidence, comparison and export. No external model.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run"); run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--workdir", required=True, type=Path); run.add_argument("--output", required=True, type=Path)
    run.add_argument("--workers", type=int, default=2); run.add_argument("--max-items", type=int, default=5000)
    export = sub.add_parser("export"); export.add_argument("--workdir", required=True, type=Path); export.add_argument("--output", required=True, type=Path)
    review = sub.add_parser("review"); review.add_argument("--workdir", required=True, type=Path); review.add_argument("--paper-id", required=True)
    review.add_argument("--edits", type=Path); review.add_argument("--decision", choices=["reviewed", "needs_review"], default="reviewed"); review.add_argument("--note", default="")
    for command in ("search", "ask", "graph"):
        p = sub.add_parser(command); p.add_argument("--workdir", required=True, type=Path)
        if command != "graph": p.add_argument("query")
    online = sub.add_parser("sync"); online.add_argument("--online", action="store_true", required=True)
    online.add_argument("--query", default=""); online.add_argument("--category", default="cond-mat.mtrl-sci")
    online.add_argument("--count", type=int, default=20); online.add_argument("--max-pdf-mib", type=int, default=100)
    online.add_argument("--workers", type=int, default=2); online.add_argument("--workdir", required=True, type=Path); online.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "sync":
            if not 1 <= args.count <= 5000 or not re.fullmatch(r"[\w.-]+", args.category):
                raise ValueError("Invalid count or category")
            return asyncio.run(sync(args))
        library = Library(args.workdir)
        if args.command == "run":
            report = library.run(manifest(args.manifest), workers=args.workers, max_items=args.max_items)
            result = {**report, "output": library.export(args.output)}
        elif args.command == "export": result = library.export(args.output)
        elif args.command == "review": result = library.review(args.paper_id, edits=json.loads(args.edits.read_text()) if args.edits else None, decision=args.decision, note=args.note)
        elif args.command == "search": result = search(args.query, library.records())
        elif args.command == "ask": result = answer(args.query, library.records())
        else: result = graph(library.records())
        print(json.dumps(result, ensure_ascii=False))
        return int(args.command == "run" and report["failed"] > 0)
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"error": "Input, file or record validation failed; check paths, manifest and field types."})); return 1


if __name__ == "__main__":
    raise SystemExit(main())
