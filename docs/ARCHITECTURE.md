# Architecture, API and data dictionary

Version0.3.0. The project is local-first, single-host and review-oriented. It is not a validated research-grade system.

## Components

- Frozen `contracts` / `storage`: original M01/M02 public API. Twelve files are hash-checked against the0.1.2 release; no mutation was required.
- `research`: rule-based material/method/finding/conclusion records, cross-platform locking, immutable history and snapshot exports.
- `science_platform`: separate strict Pydantic contracts, versioned FastAPI API, SQLite WAL state, lease-based serial worker, metadata adapters, acquisition and source-grounded extraction.
- `science_platform/web`: static HTML/CSS/modules served by the same FastAPI origin. The detail view combines PDF, structured records and evidence inspection.
- `website`: hosted Worker snapshot with separate R2 persistence. It is not a Python runtime and is not automatically connected to the local API.

## State and migrations

New DB: `data/science-platform/platform.sqlite3`. Schema baseline: `src/science_platform/schema.sql`; migration: `migrations/0001_platform.sql`, tracked by `PRAGMA user_version=1`. Higher versions and unrelated legacy DBs are rejected. A separate DB avoids breaking frozen M02 tables. PostgreSQL, Redis and pgvector are not deployed.

| Table | Purpose / important fields |
|---|---|
| schema_versions | Migration number and application timestamp |
| papers | paper_id PK, unique DOI, title, metadata_json, access_status, current_document |
| documents | document_id PK, paper FK, SHA256, path, kind, license, source_url, acquisition_method, file_size, acquired_at, status |
| parses | document FK, parser_version, structured payload; unique(document_id,parser_version) |
| extractions | immutable extraction ID, document FK, model, version, payload, status, created_at |
| reviews | extraction FK, optimistic revision, notes/status, timestamp; preserves old versions |
| jobs | kind, payload, persistent status/progress/total, attempts, max_attempts, owner, lease, result, error, idempotency key |
| events | bounded safe stage/event diagnostic payloads |
| search_results | job→paper membership |
| source_rates | persistent per-source next-allowed timestamps |

PDF changes invalidate current extraction/review usability and preserve history. Existing files are hash-checked before evidence-bearing snapshots. This protects source identity, not scientific truth. Such checks can be expensive at large scale.

## Data objects

`Paper` contains normalized bibliographic data, fulltext candidates, reference DOIs, source facts and conflicts. `ParsedDocument` holds document hash, parser/version, segments and equations. A segment carries exact text, page/section, kind, bounding box and source path. XML page numbers may be unknown.

`ScientificRecord` contains task-specific claims and algorithms. Evidence binds paper/hash/segment/page/section/quote/offsets/model/version. Scientific claims remain reviewable even when quote existence is `VERIFIED`; verification scope is explicitly `SOURCE_SPAN_ONLY`. Missing values are not inferred. No configuration produces `NOT_EXECUTED`.

## HTTP API

Base URL: `/api/v1`. Runtime API description: `/docs`; schema: `/openapi.json`. Several strict JSON bodies are parsed by explicit dependencies, so OpenAPI does not currently describe every request schema completely; use the Pydantic input classes in `api.py` and `models.py` for authoritative shapes.

| Method/path | Behavior |
|---|---|
| GET health / capabilities / stats | Runtime state and actual configuration flags |
| POST discovery | Enqueue SearchQuery; optional Idempotency-Key header |
| GET jobs, jobs/{id}, jobs/{id}/results | Persistent progress, source states, search results/events |
| POST jobs/{id}/pause, resume | Pause/requeue without deleting completed checkpoints |
| POST batch | `{paper_ids:[...], action:acquire|parse|extract|all, force:false}` |
| GET papers | Query/title/DOI, venue, years, fulltext flag, offset/limit |
| POST papers | Store strict Paper metadata |
| GET papers/{paper_id}/detail | Metadata, current document/parse/extraction/review and history list |
| GET papers/{paper_id}/file | Current verified local fulltext |
| POST papers/{paper_id}/document | Raw application/pdf upload,100MiB bound, independent format probe |
| POST extractions/{id}/review | `{revision,confirmed,notes,evidence_ids}`; rejects stale/conflicting revision |
| GET algorithms | Real structured algorithm records, name/type filters |
| POST compare, gaps | `{paper_ids:[2–10 selected IDs]}`; missing data preserved |
| GET graph | Nodes/edges derived from stored metadata/records |
| POST assistant | `{question,paper_ids:[],threshold:0.2}`; insufficient evidence abstains |
| GET/POST venues | Curated/user-maintained registry, no inferred journal rankings |
| GET export?format=jsonl/csv/xlsx | One read snapshot, paper identity and evidence preserved |
| GET export/pdf | PDF archive with license manifest; unsupported reuse cases excluded |
| POST compare/export?format=csv/xlsx/jsonl | Structured comparison export |

Example:

```json
{"query":"formal verification constraint reasoning","providers":["crossref","openalex"],"year_from":2020,"target":20}
```

Paper IDs may contain DOI slashes; URL-encode them in clients. Secrets stay in server configuration. Default binding is loopback; cross-origin writes are rejected. Non-loopback serving requires an API token and separately configured TLS proxy/allowed hosts. No multi-tenant authorization is claimed.

## Scientific boundaries

The OpenAI-compatible client makes bounded specialist calls, validates exact cited text and structured numbers, rejects unsupported fields and separates model status from quote status. Real-model integration is not executed. Cross-section reconciliation, inference and graph relation coverage are incomplete; consult KNOWN_ISSUES.

Real embeddings are optional; current semantic behavior reranks BM25 candidates rather than providing a semantic-only candidate pool. The assistant is extractive and evidence-thresholded, not a general researcher or novelty oracle.
