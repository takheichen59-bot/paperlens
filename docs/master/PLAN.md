# Execution plan and gates

A. Back up records; repair stale/history handling, snapshot export, failure isolation, Windows locks and hosted conditional publication. Run targeted regression tests before proceeding.
B. Add a separate strict metadata contract, DOI normalization, five provider adapters plus retained arXiv, curated venue registry, transactional search/job state, safe full-text acquisition. Run offline failure tests and real public-source discovery; report authorization-limited sources separately.
C. Add a document/evidence contract and PyMuPDF/OCR/GROBID/Docling adapters, structure alignment, multi-stage task-specific LLM extraction with bounded retry, quote validation and reconciliation. Preserve uncertainty. Run actual PDF/OCR tests; LLM/dual-parser/human-gold tests require their real dependencies.
D. Add evidence-linked algorithm detail, 2–10 paper comparison, retrieval threshold, typed literature observations/hypotheses and derived graph relations. Use no claims inferred merely from absence in the library.
E. Connect a research workspace to a versioned Python API with PDF page/evidence views and durable jobs. Browser validation remains an explicit gate, not a static-render pass.
F. Run integration/recovery/source-change tests, generate Windows/Linux startup files, env template, Chinese/English/API/database docs, package source and installable wheel, publish the download/report update while preserving existing site audience and data.

Status vocabulary: IMPLEMENTED_TESTED, IMPLEMENTED_NOT_EXTERNALLY_VERIFIED, NOT_EXECUTED, FAILED, NOT_IMPLEMENTED. A phase with unresolved critical correctness failures blocks the next phase.
