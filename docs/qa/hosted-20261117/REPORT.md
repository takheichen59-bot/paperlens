# Search-first hosted PaperLens validation

Website: https://paperlens-research-workspace.halvedbolt3.chatgpt.site

The native Sites publication succeeded. The audience is owner-private and requires ChatGPT sign-in. This publication deploys the independent Worker/R2 web workflow; it does not deploy the Python FastAPI service, change GitHub main, or migrate old databases. Source is based on preserved commit `17113833cb76595123e012551c58de95bfa053e3`.

## Implemented behavior

- Literature search is the primary homepage action. arXiv and Crossref queries use their real upstream APIs. Fixed acquired-paper examples and direct fixed-ID lookups are labelled separately from live queries. Crossref XML/MathML tags are removed from metadata display without inventing scientific text.
- A library keeps explicit selected scope across routes, readable missing-field states, comparison, six-sheet Excel, CSV, JSONL, ZIP and printable reports.
- Material roles and numerical ownership are separate candidate layers. Evidence shows original page, block, code-point offsets and exact source text. Review edits/notes remain a separate overlay; importing a newer record invalidates the viewed-record cache.
- PDF.js processes permitted PDFs in the browser. Batch pause/resume preserves completed records and retry handles failed entries only. Duplicate source/DOI/hash handling reuses canonical identity. Local PDF bytes are temporary; extracted records are persisted privately.
- Closed mobile navigation is inert and hidden from assistive technology. Content switches use ordinary pressed buttons with focus restoration, and reduced-motion preference is respected by the evidence scroll action.

## Results actually rerun

Commands and full output are committed beside this report.

| Scope | Command | Actual result | Limit |
|---|---|---|---|
| Python unit/integration regressions | `.venv/bin/python -m unittest discover -s tests/master -v` | 54 passed | Existing Python source behavior; not this UI's browser acceptance |
| Existing acquisition/web API/archive checks | `node verify-phase1.mjs` | 19 passed | Includes older 20-record metadata fixtures; not 20 new full-text extractions |
| Existing research API/evidence/export checks | `node verify-research.mjs` | 16 passed | Offline API/logic checks |
| History, concurrency and bounded storage | `node verify-master-a.mjs` | 5 passed | Isolated test storage |
| Hosted attribution | `node verify-hosted-attribution.mjs --real-jsonl <actual-five-records>` | 11 passed | Synthetic rule safety plus actual five-record format/source-span compatibility; no scientific accuracy score |
| Hosted exports | `node verify-hosted-exports.mjs --records <actual-five-records>` | 8 passed | File/field/source consistency, not browser rendering |
| New discovery/workspace requests | `node verify-workspace.mjs` | 8 passed | Synthetic service responses are explicitly labelled fixtures |
| Impeccable mechanical design detector | `impeccable detect --json --changed` | `[]` | Static detector, not a visual verdict |

The additional `verify-site.mjs` CI entry also passed its 19 existing phase-one checks; it invokes the same suite and is not counted as a separate test population. The clean staged-source export secret scan checked 539 files with zero findings. A scan of the entire developer folder initially encountered certificate/private-key test strings in ignored virtual-environment dependencies; these runtime files are not part of the source export. Vendored Impeccable whitespace/Windows CRLF is retained from upstream; the application diff passes whitespace checks.

These results are separate scopes. Historical branch counts are not added together or presented as one new browser run.

## Real production data and downloads

`seed-receipts.json` records successful R2 uploads of five actual CC BY 4.0 PDFs, their five complete research records and seven processing files. Every registered download was fetched back from the production Site and matched its pinned SHA256.

`live-verification.json` records actual production HTTP checks: the HTML entry and CSP, five-record index, complete records validated against their original blocks, original PDF hash, explicit fixed-lookup provenance, upstream keyword requests, cross-origin write rejection and the streamed full package. The five records contain **233** evidence snippets in total. States are **2 success, 2 partial, 1 failed**, all unreviewed. Success describes structure only.

Both real keyword requests returned 20 metadata records each, from arXiv and Crossref. This is metadata retrieval, not processing 20 full texts. The separate full package was downloaded: **25,538,403 bytes**, 12 entries, ZIP CRC passed, containing five original PDFs and seven processing files.

The download screen provides actual `research.xlsx`, `research.jsonl` and `processing-report.pdf`. The fixed processing report is 15 pages for all five papers, not an original paper. The original BiFeO3 PDF remains 11 pages and 6,027,220 bytes with SHA256 `1f88d96cfa8bc36595ac00eaebd42db85fbcc1eb35733058e2399906aa0fb7cd`.

## Field-level before/after for arXiv:2501.00680v1

| Field/candidate | Earlier flat extraction | Preserved record plus attribution |
|---|---|---|
| BiFeO3 | Material mention | Study-subject candidate |
| MoS2 | Same material list | Background mention, page 2 |
| Bi4Ti3O12 | Same material list | Background mention, page 2 |
| 97% degradation | Numeric candidate from introduction | Cited-result candidate, not this paper's new result |
| 1 K | Numeric candidate | Simulation-parameter candidate |
| Methods | 1,676 characters, pages 3–4 | Unchanged original field |
| Findings | 134 characters, page 8 | Unchanged original field; rule coverage is incomplete |
| Conclusions | 405 characters, page 8 | Unchanged original field |
| Source evidence | 22 original snippets | Original snippets retained; 33 role/context snippets added, total 55 |
| Review | unreviewed | unreviewed |

The browser extractor records `browser-context-roles-v1`; the actual seeded Python results retain `context-roles-v1`. They share a validated representation but are not silently treated as the same parser/model output.

## Failed or unavailable verification

- Managed browser preview failed with `relay could not open browser port 4173: timed out waiting for relay readiness`, including after the app's port-argument repair and environment recovery. A manual replacement preview server was not used to bypass this limitation.
- The cloud browser opened the real production URL but encountered its ChatGPT sign-in gate. No authenticated desktop/mobile captures were obtained. The independent Impeccable reviewer returned **recapture**, not a visual ship verdict. This UI's interactive browser acceptance remains **not executed**. Prior FastAPI browser suites are not substituted for it.
- The documentation agent exhausted its usage limit after writing DESIGN.md. The build thread completed the sidecar and documented the substitution in `.impeccable/review/finish-review.md`.
- An initial Node direct-network request failed. Re-running with the execution environment's configured HTTP proxy succeeded; the production receipts above are from successful real requests.

## Remaining priorities

1. Capture the authenticated UI at desktop and mobile widths, execute selection/review/upload/retry/download flows in the rendered browser, and repeat the independent finish review.
2. Add 3–5 further papers with explicit role-level expert labels, then extend to 20 full-text batch regressions. The current five-paper outputs have no independent scientific gold standard.
3. Improve rule coverage of methods/findings/conclusions and ambiguous role ownership without silently rewriting original automatic fields.

No paid model, external private-paper upload or public audience change was performed. The deep-model state is explicitly `NOT_CONFIGURED`; OCR and expert scientific validation are not claimed.
