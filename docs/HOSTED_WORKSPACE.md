# PaperLens hosted workspace

Live website: https://paperlens-research-workspace.halvedbolt3.chatgpt.site

The Site is owner-private. Open the link and sign in with the ChatGPT account that owns the Site. The deployment does not expose a public anonymous workspace. Source changes are on `codex/impeccable-site`, based on preserved commit `17113833cb76595123e012551c58de95bfa053e3`; GitHub `main` is not changed by deployment.

## Use the website

1. Start at **文献检索**. Query keywords, a DOI, or an arXiv ID. Crossref returns source metadata; an accessible PDF is a separate step. The three fixed examples are explicitly labelled as previously acquired records.
2. Select arXiv results to fetch and process their open PDFs, or import PDFs you are authorized to process. PDF.js reads text locally in the browser. Progress, failures, pause/resume and failed-only retry are explicit.
3. Open **我的文献库** and inspect original fields, material roles and numerical ownership. A source chip opens exact evidence, original page, block and character offsets. Automatic records and manual review overlays are stored separately.
4. Use **导出文件** to choose selected or all records and obtain six-sheet Excel, CSV, JSONL, ZIP, or a printable processing report. Selected scope persists across navigation. Browser-generated reports use the browser's Save as PDF facility.
5. The same export screen offers the pinned five-paper Excel, JSONL, 15-page processing-report PDF, and a package containing all five original PDFs. The processing report is not an original paper.

## Runtime and data boundaries

The hosted backend is a Cloudflare Worker with an R2 binding. This is the repository's independent `research-1` web format, not a deployed FastAPI/PyMuPDF/SQLite service and not an implicit database migration. No frozen contract, old storage interface or SQL schema is changed. The public five-paper corpus is licensed CC BY 4.0 and retains authors, source URLs and PDF fingerprints.

New PDFs are parsed in the current browser using PDF.js and `browser-scientific-rules-v1.2` / `browser-context-roles-v1`. The seeded records retain their actual Python extractor and `context-roles-v1` attribution versions. These parsers can produce different blocks and fields. Private local PDF bytes stay in the browser; extracted records and excerpts are saved in the owner-private Site. Browser refresh requires reselecting a local PDF for original-page viewing. Original public sample PDFs are separately pinned in R2.

There is no configured language-model service, no paid model call and no OCR in the hosted browser workflow. Rules identify candidates; they do not establish scientific correctness. Material mention, source-span equality, structural success and an expert-verified scientific conclusion are different things. All five seeds remain unreviewed: two structurally complete, two partial and one failed extraction. No independent scientific accuracy gold standard exists.

## Reproduce source checks/build

From `website/`, run:

```sh
node verify-phase1.mjs
node verify-research.mjs
node verify-master-a.mjs
node verify-hosted-attribution.mjs
node verify-hosted-exports.mjs
node verify-workspace.mjs
node build-workspace.mjs
```

`seed/` contains the public fixed corpus/index, including exact downloadable-artifact receipts. Full PDFs and R2 objects are runtime data, not Git source. For the managed local preview only, `scripts/dev.mjs` provides an isolated filesystem adapter; it is not the production R2 implementation. The built production Worker is `dist/server/index.js`. `.openai/hosting.json` records the existing Site identity and R2 binding, with no credentials.

See [the current validation report](qa/hosted-20261117/REPORT.md) for actual output, limitations and publication state. Prior Python/browser results are not added to new web checks or represented as a browser run for this UI.
