# Browser workflow checks

These tests launch real Chromium, a real FastAPI server, SQLite and PDF subprocesses in temporary directories. They never reuse the personal library, intercept requests, fake upstream search results or call a real model.

Install once:

```bash
python -m pip install -e '.[platform,browser]'
python -m playwright install --with-deps chromium
```

Deterministic suite:

```bash
python tests/browser/run_workflow.py --output work/browser
# Or use an already installed Chromium:
python tests/browser/run_workflow.py --browser /usr/bin/chromium --output work/browser
```

The 12 scenarios cover authentication recovery, navigation/empty states, filtering, evidence/PDF controls, review persistence, duplicate-DOI uploads, failure-only retry, selected exports, comparisons, graph interaction, insufficient-evidence refusal, no-model state and mobile/CSP checks. Nonempty claims are manually grounded **synthetic engineering fixtures**, explicitly labelled in the PDF and UI; they are not model output or scientific accuracy evidence. The failed-job test waits for the resume HTTP response before reading a new state.

Opt-in real upstream test (network required, not part of deterministic CI):

```bash
python tests/browser/run_live_smoke.py --output work/browser-live
```

This separately searches 20 Crossref records and downloads a fixed arXiv benchmark declared in `samples/browser/real_paper.json`. It does not claim that the benchmark came from those 20 results. The known paper's CC license was checked previously; the run records whether newly downloaded bytes match that verified version. It parses the actual PDF, records a workflow note, and downloads JSONL/Excel/PDF exports. No model means `NOT_EXECUTED`; generated findings are not asserted. Published screenshots contain public source metadata and synthetic/workflow notes only. The source PDF itself is excluded from Git.

Each process exits nonzero on failure and writes `report.json`. The local server always terminates in `finally`. Browser-native PDF layout and fragment scrolling vary by browser: URL/page controls are asserted, but precise PDF scroll position and bbox overlays are not certified.

Actual research-format delivery preview (requires previously generated legal exports; no model):

```bash
python tests/browser/run_research_delivery.py --directory /absolute/export/version \
  --browser /usr/bin/chromium --output work/delivery-browser
```

This separately checks real paper identities and identical Excel/JSONL/report-PDF download bytes. It does not import research records into the independent ScientificRecord database or certify scientific accuracy.

## Hosted workspace UI

`python tests/browser/run_hosted_workspace.py --output work/hosted-browser-ci` runs the new Worker UI in actual Chromium with explicitly synthetic engineering fixtures and an isolated filesystem storage adapter. GitHub Actions runs it after the existing FastAPI browser suite. It exercises search controls, selection/JSONL/Excel scope, PDF report rendering, evidence, review overlays, viewed-record replacement, real PDF.js ingestion, invalid-PDF retry and mobile navigation. Screenshots and downloaded artifacts are uploaded by CI. The search response in this UI suite is a labelled fixture; real arXiv/Crossref calls and the five real-paper downloads have separate production receipts.

This suite does not authenticate to the private production Site, evaluate scientific accuracy, or substitute mocked storage for a production R2 test. On managed Sites Linux it refuses to create a separate preview server; use the official preview relay there.
