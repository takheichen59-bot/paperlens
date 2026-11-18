# Reading-quality repair — 2026-11-18

The user-supplied 11-page review (SHA256 `b7fd83be503feacddf3be01a33f4ab07930b7f423ba819cfe7e0a7c970445345`) was read as a problem report. Its PDF, full extracted public-source snapshots and user data are excluded from this public PR. The GitHub connection was rechecked as DerekChen315 with write permission. PRs #1 and #2 remain open/unmerged. This branch retains their integrated fixes and original commit `17113833cb76595123e012551c58de95bfa053e3`; it builds on #4 and does not alter main.

## What changed

`research-1` automatic results and review overlays remain available. A separately versioned `paperlens-reading-1` layer now reconstructs complete sentences with reversible raw block/codepoint ranges. It can retrieve method routes across body sections, withhold orphan fragments, classify perspective/review candidates, and explain missing fields. Sparse two-column order, caption continuation and decimal-temperature boundaries were fixed. Current-work numeric context can reset preceding cited-work ownership; mixed conditions stay uncertain.

The Chinese cards for the five pinned PDF hashes are **assistant-authored source reviews**, not automatic summaries, an independent expert gold standard, or user-approved records. They are stored separately, include claim-to-evidence links, distinguish author limitations from assistant boundaries/suggestions, and only apply to the matching PDF hashes. Missing sources withhold claims instead of fabricating support. All five remain user-unreviewed.

Primary exports are a Chinese card workbook, reading PDF and expandable offline HTML. Full original records, old field workbook and audit CSVs remain available. Browser-selected exports add reading sheets without removing the original six sheets. Web detail defaults to the reading card; comparison uses reading questions, objects, methods, findings/arguments and boundaries. Key numbers require an object, quantity, value, unit, conditions, ownership and evidence. Unbound candidates remain in audit outputs.

## Field-level before/after

The old automatic core fields are deliberately not rewritten to hide the reported errors. The following improvements are in the independent reading layer; they are not evidence that the old rules now have complete scientific recall.

| Paper | Old automatic issue | New reading result |
| --- | --- | --- |
| 2501.00680v1 · BiFeO3 | Three material mentions could be confused with samples; numerical candidates included 97% from cited work | BiFeO3 is the study object; MoS2/Bi4Ti3O12 remain background. 1 K and the two 10 ps stages retain simulation context; 97% is not promoted to a key result. |
| 2501.00591v1 · CoxNbSe2 | Method and conclusion fields empty | Source-reviewed preparation, single-crystal neutron and powder neutron routes, 3 research steps, 3 findings and a separate conclusion. The raw empty fields remain visible. |
| 2501.00561v1 · Cr in beta-Ga2O3 | Host/impurity relation incomplete; ~1.8 eV could inherit ruby ownership | Explicit impurity-in-host relation and calculation–growth–PL route. 1.80 eV calculated excitation and 1.79 eV measured ZPL at 4.2 K are distinct. Ruby's 1.786 eV remains background. |
| 2501.00447v1 · Quantum 2.0 | All old experimental core fields empty; structural failure misleading | Perspective/review candidate with question, arguments and methodological challenges; experimental steps/results are not applicable. Old `failed` remains an audit state, not the reading verdict. |
| 2501.00423v1 · double perovskite | Method/findings empty; orphan conclusion fragments | A/B preparation, XRD/Raman/PL routes and source-supported complete claims; comparison objects and Fano mechanism attribution retain their context. Fragments remain in old fields/audit. |

## Disposition of the 18 reported issues

| Issue | Implemented response | Remaining boundary |
| --- | --- | --- |
| 01 missing fields | Cross-section reading candidates and hash-bound Chinese cards | Generic automatic recall remains incomplete; three old method fields are still empty. |
| 02 orphan conclusions | Complete-sentence gate and original source maps | Rule gate does not establish semantic completeness. |
| 03 method routes | Separate computation/preparation/characterization/validation candidates; five source reviews | Ordering/generalization needs domain review. |
| 04 entities | Center entity/topic and Cr impurity–host relation in reading layer | Open-ended chemical entity recognition remains incomplete. |
| 05 numerical ownership | Current-context reset, fully bound key table, cited/parameter/condition separation | Mixed values and many candidates remain unreviewed. |
| 06 reconstruction | Sparse-column fix, conservative dehyphenation, decimal boundaries, fixed PDF numeric column widths | Equations/tables are retained in raw evidence, not converted into prose. |
| 07 metadata first | Question-led cards; hashes/version diagnostics in audit layer | Original ID/title/source remain visible for identification. |
| 08 question/steps | Research question plus source-supported steps or argument route | No fabricated step sequence for unreviewed generic records. |
| 09 duplicate/unsynthesized fields | Distinct source-reviewed findings and author conclusion | General automatic semantic synthesis is not claimed. |
| 10 long English blocks | Chinese source reviews, complete English evidence behind disclosure | No external translation/model is configured. |
| 11 article type | Perspective template and explicit not-applicable fields | Classification is a candidate, not editorial certification. |
| 12 applicability/limits | Author limitations, assistant boundaries and suggestions separate; Bi 1 K retained | Absence of an extracted limitation does not imply no limitation. |
| 13 batch orientation | Overview, bookmarks, links and comparison | Cross-condition quantitative ranking remains unavailable. |
| 14 success meaning | Separate parsing, coverage, source location and human review states | No scientific-confidence percentage or accuracy guarantee. |
| 15 density/type | Short Chinese points, hierarchy, mixed-script title normalization | Target-reader readability study not performed. |
| 16 pagination | Bounded 1–2-page cards, intentional continuation, source/footer links | Pagination may differ between PyMuPDF versions; exported version has its own receipt. |
| 17 notation | Chemical subscript/Greek display normalization; raw metadata retained | This is not general equation reconstruction. |
| 18 navigation/codes | Linked overview, PDF bookmarks, evidence inspector and folded diagnostics | Native PDF viewers differ in page-fragment handling. |

## Actual verification and limits

Five actual CC BY 4.0 PDFs were hash-checked and reprocessed: 2501.00680v1, 2501.00591v1, 2501.00561v1, 2501.00447v1 and 2501.00423v1. The reading layer contains 490 complete evidence sentences with 648 original source parts and 7 fully bound key numeric rows. Literal slicing was checked; this does not validate scientific interpretation. See [real-five-validation.json](real-five-validation.json). Reproduction: `python scripts/validate_reading_corpus.py --manifest <licensed-manifest.json> --output <new-directory> --before <previous-research.jsonl>`.

Local verification: 69 Python tests; existing 160-check acceptance suite; phase-A integrity, scientific-record and research-intelligence acceptance each passed 5 checks. New reading engineering verifier passed 8 checks. Six PDF/export regressions were also exercised using PyMuPDF 1.28.2 in an isolated runtime, after the first CI attempt exposed the numeric-table layout defect. The same five source records render within 1–2 pages per card in that runtime (8 pages total before the typography pass). The final deliverable uses 11 pt body text, 10 pt numeric tables and 12 pt section headings, with 11 pages total under PyMuPDF 1.28.2; every card occupies 2 pages. Both 1.26.6 and 1.28.2 export within the same 1–2-page bound. These versions contain the same claims; page counts are not scientific quality scores.

Remote CI status, screenshots and private deployment receipts are recorded after completion below. The initial failures are retained in [attempts.json](attempts.json), not counted as passes. Local source auditing initially scanned ignored virtualenv dependencies and found their bundled certificates/test key text; the clean tracked-source snapshot passed without findings. Fulltext data upload was separately rejected by automatic approval review; the safe public-source version uses metadata/receipts only.

Not executed: independent domain expert gold/scientific precision-recall evaluation; target-reader timed study; paid or external model extraction; 20-real-fulltext regression; all-browser/phone-device tests. Browser CI uses labelled synthetic engineering data and does not claim scientific content validation or private production authentication.

## Data preservation and publication

Before production updates, 7 existing files and 24 records plus their review overlays were backed up privately. R2 updates preserve immutable record/review history and both old/new artifacts by content hash. Frozen `src/contracts/`, old `src/storage/`, and database schemas are unchanged. No public sharing change is requested.

Next priority: obtain domain review of the five cards, extend source-backed generic extraction beyond the curated five, then run a fresh 20-paper real-fulltext corpus. Do not expand graph/agent architecture first.
