"""Five independent offline scientific-record acceptance scenarios."""
from pathlib import Path
from tempfile import TemporaryDirectory
import copy, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from research.extraction import extract_pdf, validate_scientific_record
from contracts.jsonl_schema import validate_record


def fixture(directory):
    path = Path(directory) / "paper.pdf"
    doc = fitz.open(); page = doc.new_page(); y = 48
    for text, heading in [
        ("Materials Research", True), ("Abstract", True),
        ("We investigate graphene using a reproducible computational method.", False),
        ("Methods", True),
        ("Graphene samples were prepared and measured using density functional theory.", False),
        ("The simulations used a plane wave cutoff of 500 eV at 300 K.", False),
        ("Results", True),
        ("Our results demonstrate improved strength reaching 26.5 GPa.", False),
        ("E = a + b", False),
        ("Fig. 1. The caption reports a hypothetical value of 999 MPa.", False),
        ("Conclusions", True),
        ("In conclusion, graphene exhibits improved strength under the tested conditions.", False),
        ("A limitation is that temperature effects were not considered.", False),
        ("References", True),
        ("[1] Titanium dioxide TiO2 and MoS2 were discussed in prior work.", False),
    ]:
        page.insert_text((45, y), text, fontsize=13 if heading else 10,
                         fontname="hebo" if heading else "helv")
        y += 23 if heading else 19
    doc.save(path); doc.close()
    return extract_pdf(path, {"id": "2501.00001v1", "paper_id": "arxiv:2501.00001",
        "title": "Materials Research", "doi": None, "url": "https://arxiv.org/abs/2501.00001v1"})


def complete():
    with TemporaryDirectory() as d:
        r = fixture(d)
        assert r["materials"] and r["methods"] and r["conclusions"] and r["findings"]
        assert r["algorithms"] and r["formulas"] and r["experimental_data"]
        assert validate_record(r["legacy_record"]).valid
        assert validate_scientific_record(r) is r


def slices():
    with TemporaryDirectory() as d:
        r = fixture(d)
        raw = {b["block_id"]: b for b in r["raw_blocks"]}
        for s in r["source_snippets"]:
            assert s["text"] == raw[s["block_id"]]["text"][s["start_offset"]:s["end_offset"]]
        bad = copy.deepcopy(r); bad["source_snippets"][0]["text"] = "fabricated"
        try: validate_scientific_record(bad)
        except ValueError: pass
        else: raise AssertionError("wrong evidence accepted")


def exclusions():
    with TemporaryDirectory() as d:
        r = fixture(d)
        assert "TiO2" not in r["materials"] and "MoS2" not in r["materials"]
        assert not any("999 MPa" in s["text"] or s["section_kind"] == "references" for s in r["source_snippets"])


def candidates():
    with TemporaryDirectory() as d:
        r = fixture(d)
        assert any(x["value"] == "26.5" for x in r["experimental_data"]) if r["experimental_data"] and "value" in r["experimental_data"][0] else any("26.5" in x["text"] for x in r["experimental_data"])
        assert all(x["format"] == "pdf_text_candidate" for x in r["formulas"])
        assert all(x["evidence_ids"] for field in ("algorithms", "formulas", "experimental_data") for x in r[field])


def contradictions():
    with TemporaryDirectory() as d:
        r = fixture(d); r["findings"] = "This conclusion was never in the PDF."
        try: validate_scientific_record(r)
        except ValueError: pass
        else: raise AssertionError("unsupported field accepted")


failed = 0
for name, case in [("complete_scientific_record", complete), ("all_raw_slices_and_tamper_rejection", slices),
                   ("references_and_captions_excluded", exclusions), ("candidates_are_evidence_backed", candidates),
                   ("unsupported_findings_rejected", contradictions)]:
    try: case(); print("PASS", name)
    except Exception as exc: failed += 1; print("FAIL", name, type(exc).__name__, str(exc))
print(f"SCIENCE SUMMARY: {5-failed} passed, {failed} failed")
raise SystemExit(int(bool(failed)))
