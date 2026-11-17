"""Verify the actual acquired corpus, not synthetic extraction accuracy."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import feedparser
from phase1_acquire import acquire, inspect_pdf
from fetchers.arxiv import ArxivFetcher


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--feed", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads((args.corpus / "index.json").read_text())
    papers = data["papers"]
    passed = failed = 0

    def check(name, fn):
        nonlocal passed, failed
        try:
            fn()
            print("PASS " + name)
            passed += 1
        except Exception as exc:
            print("FAIL " + name + ": " + type(exc).__name__)
            failed += 1

    def identity():
        assert len(papers) == data["acquired"] == data["target"] == 20
        assert len({p["source_id"] for p in papers}) == 20
        assert len({p["sha256"] for p in papers}) == 20
        dois = [p["doi"].lower() for p in papers if p["doi"]]
        assert len(set(dois)) == len(dois)

    def sources():
        for paper in papers:
            assert paper["source"] == "arxiv"
            assert paper["url"] == "https://arxiv.org/abs/" + paper["id"]
            assert paper["pdf_url"] == "https://arxiv.org/pdf/" + paper["id"]
            assert paper["title"] and paper["authors"]
            assert re.fullmatch(r"https://creativecommons.org/(?:licenses/by(?:-sa)?/[\d.]+|publicdomain/zero/[\d.]+)/?", paper["license_url"])

    def files():
        for paper in papers:
            path = args.corpus / paper["file"]
            actual = inspect_pdf(path)
            assert actual == {key: paper[key] for key in actual}
            assert actual["pages"] > 0 and actual["text_characters"] >= 200
            assert paper["status"] == "verified"

    def provenance():
        content = args.feed.read_bytes()
        assert hashlib.sha256(content).hexdigest() == data["search_feed_sha256"]
        ids = {entry.id.rsplit("/abs/", 1)[-1] for entry in feedparser.parse(content).entries}
        assert all(p["id"] in ids for p in papers)
        assert all("cond-mat.mtrl-sci" in p["categories"] for p in papers)

    def resume():
        before = {p["file"]: (args.corpus / p["file"]).stat().st_mtime_ns for p in papers}
        with patch.object(ArxivFetcher, "_get", side_effect=AssertionError("unexpected_network")) as network:
            with patch.object(ArxivFetcher, "download", side_effect=AssertionError("unexpected_download")) as download:
                result = asyncio.run(acquire(SimpleNamespace(dest=args.corpus, feed=args.feed, count=20, max_pdf_mib=20)))
                assert result == 0
                network.assert_not_called()
                download.assert_not_called()
        assert before == {p["file"]: (args.corpus / p["file"]).stat().st_mtime_ns for p in papers}

    check("20 unique papers, DOI deduplication and 20 unique PDF hashes", identity)
    check("Official source URLs and explicit redistributable CC licenses", sources)
    check("All 20 PDFs: bytes, SHA256, every page, readable text and rendering", files)
    check("All records trace to the exact official materials-science search feed", provenance)
    check("Resume performs zero network requests and does not rewrite completed PDFs", resume)
    print(f"PHASE 1 SUMMARY: {passed} passed, {failed} failed")
    print(json.dumps({"papers": len(papers), "pages": sum(p["pages"] for p in papers),
                      "bytes": sum(p["bytes"] for p in papers)}, ensure_ascii=False))
    return int(failed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
