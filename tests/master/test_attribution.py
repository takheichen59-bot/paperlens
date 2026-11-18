"""Role safety and actual PDF/export regressions; fixtures are not science gold."""
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf as fitz
from research.attribution import material_role, numeric_role
from research.delivery import role_cells
from research.extraction import extract_pdf, validate_scientific_record, VERSION
from research.library import Library, key


def fixture(root):
    path = Path(root) / "fixture.pdf"
    doc = fitz.open(); page = doc.new_page(); y = 38
    for text, heading in [
        ("Graphene comparison study - SYNTHETIC", True), ("Introduction", True),
        ("In previous work, TiO2 degraded 97% of a fictional dye. The results show a high rate.", False),
        ("Methods", True), ("We study graphene and compare graphene with MoS2.", False),
        ("The samples were washed with ethanol.", False),
        ("The simulations used a plane wave cutoff of 500 eV at 300 K.", False),
        ("Results", True), ("We observed a strength of 26.5 GPa in this synthetic test.", False),
        ("We found 26.5 GPa compared with 31 GPa in previous work [4].", False),
        ("Conclusions", True), ("In conclusion, graphene was investigated in a synthetic test only.", False),
        ("References", True), ("[1] A fictional reference reports MoS2 at 999 K.", False),
    ]:
        page.insert_textbox(fitz.Rect(40, y, 550, y + 40), text, fontsize=12 if heading else 10,
            fontname="hebo" if heading else "helv")
        y += 42
    doc.save(path); doc.close()
    return path, {"paper_id": "test:roles", "id": "test-roles", "title": "Graphene comparison study - SYNTHETIC", "url": "", "doi": None}


class AttributionTests(unittest.TestCase):
    def test_background_comparison_is_not_current_control(self):
        role, _ = material_role("MoS2", "The previous record was observed with MoS2 [14].", "In recent work, collaborators investigated catalysts.", "introduction", "BiFeO3 study")
        self.assertEqual(role, "background")

    def test_current_comparator_and_subject_are_distinguished(self):
        text = "We study graphene and compare graphene with MoS2."
        self.assertEqual(material_role("graphene", text, "", "methods", "Graphene study")[0], "study_subject")
        self.assertEqual(material_role("MoS2", text, "", "methods", "Graphene study")[0], "comparator")
        self.assertEqual(material_role("ethanol", "The samples were washed with ethanol.", "", "methods", "Graphene study")[0], "reagent_or_environment")

    def test_adjacent_prior_attribution_keeps_results_show_external(self):
        self.assertEqual(numeric_role("The results show a 97% degradation rate.", "In recent work, Amdouni investigated particles [1].", "introduction")[0], "cited_result")
        self.assertEqual(numeric_role("We observed 3 eV.", "In previous work, others studied defects.", "results")[0], "own_result")
        self.assertEqual(numeric_role("The results show 3 eV.", "In previous work, others studied defects. We studied our samples.", "results")[0], "own_result")

    def test_version_change_archives_old_record_without_silent_reuse(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            path, meta = fixture(root); lib = Library(Path(root) / "lib")
            item = {"meta": meta, "pdf": path}
            with patch('research.library.VERSION', 'scientific-evidence-v1.1'):
                lib.run([item], workers=1)
            self.assertEqual(lib.run([item], workers=1)['processed'], 1)
            self.assertEqual(len(lib.history(meta['paper_id'])), 1)
            self.assertEqual(next(lib.records())['attribution']['review_status'], 'unreviewed')

    def test_result_parameter_and_experimental_condition(self):
        self.assertEqual(numeric_role("A temperature of 1 K was chosen for relaxation.", "", "methods")[0], "simulation_parameter")
        self.assertEqual(numeric_role("A 532 nm laser was used.", "", "methods", "density functional calculations")[0], "experimental_condition")
        self.assertEqual(numeric_role("We observed 26.5 GPa.", "", "results")[0], "own_result")

    def test_mixed_and_unknown_ownership_stays_uncertain(self):
        self.assertEqual(numeric_role("We found 3 eV compared with 2 eV in previous work [4].", "", "results")[0], "uncertain")
        self.assertEqual(numeric_role("A peak near 3 eV.", "", "unknown")[0], "uncertain")
        self.assertEqual(numeric_role("We observe asymmetry with a laser energy excitation of 2.3 eV.", "", "results")[0], "uncertain")
        self.assertEqual(material_role("MoS2", "MoS2 occurs here.", "", "unknown", "Unrelated title")[0], "uncertain")

    def test_pdf_integration_preserves_original_candidates_and_exact_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            path, meta = fixture(root); r = extract_pdf(path, meta)
            self.assertEqual(VERSION, "scientific-evidence-v1.4")
            self.assertIs(validate_scientific_record(r), r)
            self.assertEqual(r["materials"], r["legacy_record"]["chemicals"])
            roles = {m["name"].casefold(): m["role"] for m in r["attribution"]["materials"]}
            self.assertEqual(roles["graphene"], "study_subject"); self.assertEqual(roles["mos2"], "comparator")
            self.assertEqual(roles["tio2"], "background"); self.assertEqual(roles["ethanol"], "reagent_or_environment")
            numeric = {n["role"] for n in r["attribution"]["numeric"]}
            self.assertTrue({"own_result", "simulation_parameter", "cited_result", "uncertain"} <= numeric)
            self.assertFalse(any("999 K" in s["text"] for s in r["source_snippets"]))
            self.assertEqual(r["review_status"], "unreviewed")

    def test_role_evidence_and_numeric_index_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path, meta = fixture(root); r = extract_pdf(path, meta)
            bad = copy.deepcopy(r); bad["attribution"]["numeric"][0]["candidate_index"] = 99
            with self.assertRaises(ValueError): validate_scientific_record(bad)
            bad = copy.deepcopy(r); bad["attribution"]["materials"][0]["mentions"][0]["evidence_ids"] = ["missing"]
            with self.assertRaises(ValueError): validate_scientific_record(bad)

    def test_export_workbook_pdf_and_legacy_format_boundaries(self):
        with tempfile.TemporaryDirectory() as root:
            path, meta = fixture(root); lib = Library(Path(root) / "lib")
            self.assertEqual(lib.run([{"meta": meta, "pdf": path}], workers=1)["processed"], 1)
            record_path = lib.directory / "records" / (key(meta["paper_id"]) + ".json")
            envelope = json.loads(record_path.read_text()); current = envelope["record"]
            historical = copy.deepcopy(current); historical.pop("attribution")
            self.assertEqual(role_cells(historical)[-1], "NOT_EXECUTED_HISTORICAL_RECORD")
            out = Path(lib.export(Path(root) / "out")["directory"])
            exported = json.loads((out / "research.jsonl").read_text())
            self.assertEqual(exported["attribution"], current["attribution"])
            self.assertNotIn("attribution", json.loads((out / "results.jsonl").read_text()))
            with zipfile.ZipFile(out / "research.xlsx") as z:
                ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                book = ET.fromstring(z.read("xl/workbook.xml"))
                self.assertEqual(len(book.findall("s:sheets/s:sheet", ns)), 6)
                for field, col in [("methods", 3), ("findings", 4), ("conclusions", 5)]:
                    sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml")); cells = sheet.findall("s:sheetData/s:row", ns)[1].findall("s:c", ns)
                    self.assertEqual(cells[col].find("s:is/s:t", ns).text or "", current[field])
            with fitz.open(out / "processing-report.pdf") as report:
                self.assertIn("PaperLens", "".join(page.get_text() for page in report))
            self.assertTrue((out / "evidence.csv").stat().st_size > 100)
            self.assertEqual(lib.run([{"meta": meta, "pdf": path}], workers=1)["resumed"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
