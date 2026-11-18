"""Artifact checks for source provenance and readable reading-layer exports."""
import copy
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import fitz

from research.reading import build_reading
from research.reading_delivery import write_reading_preview, write_reading_report, write_reading_workbook


def sample(assisted=True, perspective=False):
    text = ("We outline and discuss outstanding challenges for quantum matter and the development of theories. "
            if perspective else
            "We used Raman spectroscopy to study the synthetic Ga2O3 sample at 4.2 K. "
            "We observed a synthetic signal in this sample. ")
    r = {"id":"SYNTHETIC-renderer", "paper_id":"SYNTHETIC-renderer", "pdf_hash":"a"*64,
         "meta":{"title":("Challenges in understanding Quantum Matter" if perspective else r"Synthetic Cr in $\beta$-Ga$_2$O$_3$"),
                 "pdf_url":"https://example.org/SYNTHETIC.pdf", "license_url":"https://example.org/SYNTHETIC-license"},
         "materials":["OLD candidate"], "methods":"HISTORICAL methods, not rewritten",
         "findings":"HISTORICAL findings", "conclusions":"HISTORICAL conclusion", "experimental_data":[],
         "review":{"decision":"unreviewed","edits":{"methods":"MANUAL old overlay"}},
         "raw_blocks":[{"block_id":"body", "page":1, "text":text, "bbox":(40,40,550,100)}],
         "eligible_ranges":[{"block_id":"body","start":0,"end":len(text),"section_kind":"unknown"}]}
    r["reading_card"] = build_reading(r)
    if assisted:
        e = r["reading_card"]["evidence"][0]["id"]
        claim = {"text":"这是合成测试主张，不是真实科研结论。", "evidence_ids":[e]}
        r["reading_card"]["source_review"] = {
            "origin":"assistant_source_review", "human_review_status":"unreviewed", "independent_gold":False,
            "pdf_hash":r["pdf_hash"],"status":"source_bound", "version":"SYNTHETIC-test",
            "title_zh":"合成渲染测试", "type_zh":"合成观点测试" if perspective else "合成实验测试",
            "question":[claim],"objects":[claim],"methods":[] if perspective else [claim],
            "arguments":[claim] if perspective else [], "steps":[] if perspective else [claim]*3,
            "findings":[] if perspective else [claim],"conclusion":[claim],
            "author_limitations":[],"boundaries":[claim],"suggestions":[claim],
            "numbers":[] if perspective else [{**claim,"value":"4.2","unit":"K","quantity":"合成条件",
                                                "object":"合成对象","conditions":"合成测试条件","ownership":"合成条件"}],
        }
    return r


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=set(); self.targets=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get("id"): self.ids.add(attrs["id"])
        if attrs.get("href","").startswith("#"): self.targets.append(attrs["href"][1:])


class ReadingDeliveryTests(unittest.TestCase):
    def test_exports_preserve_history_and_review_and_map_evidence(self):
        r=sample();before=copy.deepcopy(r)
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);write_reading_preview(d/"preview.html",[r]);write_reading_workbook(d/"cards.xlsx",[r]);write_reading_report(d/"report.pdf",[r])
            self.assertEqual(r,before)
            with ZipFile(d/"cards.xlsx") as z:
                ns={"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                source=ET.fromstring(z.read("xl/worksheets/sheet5.xml"))
                rows=source.findall("s:sheetData/s:row",ns)[1:]
                self.assertEqual(len(rows),len(r["reading_card"]["evidence"]))
                for row in rows:
                    cells=[c.find("s:is/s:t",ns).text or "" for c in row]
                    self.assertEqual(cells[8],r["raw_blocks"][0]["text"][int(cells[6]):int(cells[7])])
                original=z.read("xl/worksheets/sheet6.xml").decode()
                self.assertIn("HISTORICAL methods, not rewritten",original)
                self.assertIn("MANUAL old overlay",original)
    def test_rule_only_record_explains_missing_review_and_does_not_promote_numbers(self):
        r=sample(assisted=False)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"preview.html";write_reading_preview(p,[r]);html=p.read_text()
            self.assertIn("本篇没有助手来源复核层",html)
            self.assertIn("尚未核实可复述的步骤顺序",html)
            self.assertIn("未提供对象、物理量、条件和归属均明确",html)
            self.assertNotIn("HISTORICAL methods",html)
    def test_perspective_has_arguments_and_explicit_not_applicable_results(self):
        r=sample(perspective=True)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"preview.html";write_reading_preview(p,[r]);html=p.read_text()
            self.assertIn("<h3>论证路径</h3>",html)
            self.assertIn("实验操作流程不适用",html)
            self.assertIn("未按原创实验结果模板填充",html)
            self.assertNotIn("<h3>来源支持的研究步骤</h3>",html)
    def test_html_source_links_have_portable_targets_and_complete_quotes(self):
        r=sample()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"preview.html";write_reading_preview(p,[r]);html=p.read_text();links=Links();links.feed(html)
            self.assertTrue(set(links.targets)<=links.ids)
            for e in r["reading_card"]["evidence"]: self.assertIn(e["text"],html)
            self.assertIn('block body · [0,',html)
            self.assertIn("独立金标准：否；用户复核：unreviewed",html)
    def test_pdf_navigation_page_bounds_and_unicode_title(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"report.pdf";result=write_reading_report(p,[sample()]);doc=fitz.open(p)
            self.assertEqual(result["overview_pages"],1);self.assertEqual(len(doc),2)
            self.assertEqual(len(doc.get_toc()),2)
            self.assertTrue(any(l.get("page")==1 for l in doc[0].get_links()))
            self.assertIn("β-Ga₂O₃",doc[1].get_text())
            self.assertNotIn("a"*64,"".join(p.get_text() for p in doc))
            self.assertLess(p.stat().st_size,12*1024*1024)
            for page in doc:
                for word in page.get_text("words"):
                    self.assertGreaterEqual(word[0],37)
                    self.assertLessEqual(word[2],558)
                    self.assertLessEqual(word[3],826)
            doc.close()
    def test_invalid_source_review_is_rejected_instead_of_relabelled(self):
        r=sample();r["reading_card"]["source_review"]["independent_gold"]=True
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):write_reading_preview(Path(d)/"preview.html",[r])


if __name__ == "__main__":
    unittest.main()
