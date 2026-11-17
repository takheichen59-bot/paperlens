# Independent audit against the master development request

Status: initial audit; implementation changes and test receipts are recorded per phase. This is not a research-grade certification.

The full source inventory is INVENTORY.json. A pre-change archive preserves Python source, local research records, site assets and Worker code. Existing PDF caches and the accepted contracts/storage tables are retained.

## Reusable implementation

- Real arXiv metadata/download adapter, rate limiting and a 20-paper CC corpus.
- PyMuPDF text/layout/section parsing with immutable raw blocks and source offsets.
- Source-span and legacy JSONL validation; rule/dictionary extraction explicitly limited in scope.
- CLI, checkpoint recovery, XLSX/CSV/JSONL export and basic comparison/quoted retrieval.
- Existing 20-module and repair acceptance tests. Passing these does not establish scientific accuracy.

## Verified code defects / missing capabilities

| Priority | Finding | Location | Required action |
|---|---|---|---|
| P0 | Old current checkpoint overwritten on source change; history not retained | src/research/library.py | Archive old source-linked extraction and invalidate current visibility before replacement |
| P0 | Export reads library multiple times without one snapshot lock | Library.export | One consistent snapshot and atomic publication |
| P0 | Invalid manifest item can abort remaining papers | Library.run / research.__main__.manifest | Per-item validation and isolated failure records |
| P0 | R2 record/summary written separately | worker/research-api.mjs | Immutable records + atomic authoritative pointer; derive index from pointer |
| P0 | Review revision comparison is not atomic | worker/research-api.mjs | R2 conditional write; reject concurrent losers |
| P1 | fcntl imported unconditionally | src/research/library.py | Platform-specific standard-library lock |
| P1 | Arbitrary full-text providers need redirect/DNS/size protections | future acquisition path | Public IP pinning, safe redirects and bounded files |
| Scientific gap | Algorithm names are mentions, not full algorithm analysis | research/extraction.py | Separate strict deep schema, specialized extractors and evidence validation |
| Scientific gap | Hash vectors are lexical, not semantic | research/analysis.py | Explicit baseline labeling; optional real embedding client |
| Scientific gap | No GROBID/Docling or independent human gold | parsing/evaluation | Real adapters; unavailable external tests NOT EXECUTED |
| Product gap | No canonical web-facing Python API / durable web job queue | hosted Worker + CLI split | Add versioned FastAPI API and persistent transactional queue |
| Product gap | Missing algorithm/gap/detail workspace | frontend | Connect to real backend; do not mark browser acceptance passed without execution |

## External and environmental gates

- No LLM, embedding, OpenAlex, Semantic Scholar, Springer or Elsevier credentials configured.
- No GROBID/Docling service or Docling package configured. Docker is available; Tesseract with English data is installed.
- No independent human-reviewed gold corpus supplied. Existing assistant/rule annotations are not a human gold standard.
- No attached browser/desktop execution tool. Hosted Sites instructions prohibit inventing a substitute preview-control path; browser E2E and screenshots cannot be reported as executed in this environment.
- Existing Sites hosting runs JavaScript Workers, not a Python/GROBID/PostgreSQL process. New Python service can run locally or on an independently authorized backend host; no such remote host is configured.

No credentials will be embedded in the browser or committed. No missing external verification is converted into a pass.
