"""Acquire an auditable, CC-licensed materials-science corpus. No extraction.

Uses the existing fetcher without changing contracts or the state database.
Completed PDFs are re-validated on resume; each candidate fails independently.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import feedparser
import httpx
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from fetchers.arxiv import ArxivFetcher
from fetchers.pdf_download import DownloadSizeLimit


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def inspect_pdf(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with fitz.open(path) as doc:
        if doc.needs_pass or not len(doc):
            raise ValueError("encrypted_or_empty_pdf")
        chars = sum(len(page.get_text().strip()) for page in doc)
        # Access every page, and render the first page to detect broken resources.
        doc[0].get_pixmap(matrix=fitz.Matrix(0.3, 0.3), alpha=False)
        if chars < 200:
            raise ValueError("insufficient_readable_text")
        return {"sha256": digest, "pages": len(doc), "text_characters": chars,
                "bytes": path.stat().st_size}


async def acquire(args):
    dest = args.dest.resolve()
    (dest / "PDF").mkdir(parents=True, exist_ok=True)
    state = dest / "index.json"
    previous = json.loads(state.read_text()) if state.exists() else {"papers": []}
    papers = []
    for old in previous["papers"]:
        path = dest / old["file"]
        if path.exists() and inspect_pdf(path)["sha256"] == old["sha256"]:
            papers.append(old)
    seen_ids = {p["source_id"] for p in papers}
    seen_dois = {p["doi"].lower() for p in papers if p["doi"]}
    seen_hashes = {p["sha256"] for p in papers}
    attempts = json.loads((dest / "attempts.json").read_text()) if (dest / "attempts.json").exists() else []
    fetcher = ArxivFetcher(max_pdf_bytes=args.max_pdf_mib * 1024 * 1024)
    if args.feed.exists():
        content = args.feed.read_bytes()
    else:
        response = await fetcher._get(fetcher.endpoint, params={
            "search_query": "cat:cond-mat.mtrl-sci", "start": "0",
            "max_results": "100", "sortBy": "submittedDate", "sortOrder": "descending"})
        content = response.content
        args.feed.parent.mkdir(parents=True, exist_ok=True)
        args.feed.write_bytes(content)
    entries = feedparser.parse(content).entries
    metas = fetcher._parse(content)
    started = datetime.now(timezone.utc).isoformat()
    try:
        for meta, entry in zip(metas, entries):
            if len(papers) >= args.count:
                break
            identifier = meta.source_id + (meta.version or "")
            if meta.source_id in seen_ids or (meta.doi and meta.doi.lower() in seen_dois):
                continue
            attempt = {"id": identifier, "source_url": meta.page_url}
            try:
                response = await fetcher._get(meta.page_url)
                html = response.text
                license_match = re.search(r'<div class="abs-license">\s*<a href="([^"]+)"', html)
                license_url = license_match[1].replace("http:", "https:") if license_match else ""
                if not re.fullmatch(r"https://creativecommons.org/(?:licenses/by(?:-sa)?/[\d.]+|publicdomain/zero/[\d.]+)/?", license_url):
                    attempt.update(status="skipped", reason="license_not_cc_by_or_cc0", license_url=license_url)
                    print(f"SKIP {identifier}: license not verified CC BY/BY-SA/CC0", flush=True)
                else:
                    artifact = await fetcher.download(meta, dest / "cache")
                    details = inspect_pdf(artifact.pdf_path)
                    if details["sha256"] in seen_hashes:
                        attempt.update(status="skipped", reason="duplicate_pdf_sha256")
                    else:
                        filename = "PDF/" + identifier.replace("/", "_") + ".pdf"
                        shutil.copyfile(artifact.pdf_path, dest / filename)
                        paper = {"paper_id": meta.paper_id, "id": identifier,
                            "source": "arxiv", "source_id": meta.source_id, "version": meta.version,
                            "doi": meta.doi, "title": meta.title,
                            "authors": [a.name for a in entry.get("authors", [])],
                            "published": entry.get("published", ""), "year": entry.get("published", "")[:4],
                            "categories": [t.term for t in entry.get("tags", [])],
                            "abstract": " ".join(entry.get("summary", "").split()),
                            "url": meta.page_url, "pdf_url": meta.pdf_url,
                            "license_url": license_url, "license_checked_at": datetime.now(timezone.utc).isoformat(),
                            "downloaded_at": artifact.downloaded_at.isoformat(), "file": filename,
                            "status": "verified", **details}
                        papers.append(paper)
                        seen_ids.add(meta.source_id)
                        if meta.doi:
                            seen_dois.add(meta.doi.lower())
                        seen_hashes.add(details["sha256"])
                        attempt.update(status="verified", **details)
                        print(f"PASS {len(papers):02}/{args.count} {identifier} {details['pages']} pages {details['bytes']} bytes CC verified", flush=True)
            except DownloadSizeLimit as exc:
                attempt.update(exc.audit())
                print(f"SKIP {identifier}: size_limit", flush=True)
            except Exception as exc:
                # Deliberately log the type, not arbitrary network response bodies.
                attempt.update(status="failed", reason=type(exc).__name__)
                print(f"FAIL {identifier}: {type(exc).__name__}", flush=True)
            attempts.append(attempt)
            write_json(dest / "attempts.json", attempts)
            write_json(state, {"phase": 1, "topic": "材料科学综合", "source": "arxiv",
                "target": args.count, "acquired": len(papers), "run_started_at": started,
                "search_feed_sha256": hashlib.sha256(content).hexdigest(), "papers": papers})
    finally:
        await fetcher.aclose()
    print(json.dumps({"target": args.count, "verified": len(papers), "unique_source_ids": len(seen_ids),
        "unique_pdf_hashes": len(seen_hashes), "total_bytes": sum(p["bytes"] for p in papers)}, ensure_ascii=False), flush=True)
    return 0 if len(papers) == args.count else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--max-pdf-mib", type=int, default=20)
    sys.exit(asyncio.run(acquire(parser.parse_args())))
