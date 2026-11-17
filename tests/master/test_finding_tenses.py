"""A real-paper recall defect, covered by synthetic PDF integration regressions."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import pymupdf as fitz
from research.extraction import extract_pdf,validate_scientific_record

class FindingTenses(unittest.TestCase):
 def extract(self,root,sentence):
  path=Path(root)/'fixture.pdf';pdf=fitz.open();page=pdf.new_page();y=50
  for text,heading in [('Engineering fixture',True),('Methods',True),('Graphene was prepared and measured in a synthetic test.',False),('The test used a controlled temperature and repeated measurements.',False),('Conclusions',True),(sentence,False),('References',True),('[1] We observed a fictional background result in a prior study.',False)]:
   page.insert_text((45,y),text,fontsize=13 if heading else 10,fontname='hebo' if heading else 'helv');y+=26
  pdf.save(path);pdf.close();return extract_pdf(path,{'paper_id':'test:tense','id':'test:tense','title':'Synthetic tense test','url':'','doi':None})
 def test_past_and_perfect_findings_have_exact_evidence(self):
  for sentence in ['We observed stable domains within the synthetic test conditions.','We have observed stable domains within the synthetic test conditions.','We showed stable domains within the synthetic test conditions.','We have shown stable domains within the synthetic test conditions.']:
   with self.subTest(sentence=sentence),tempfile.TemporaryDirectory() as root:
    r=self.extract(root,sentence);self.assertIn(sentence,r['findings']);self.assertIs(validate_scientific_record(r),r)
    raw={b['block_id']:b['text'] for b in r['raw_blocks']}
    for s in r['source_snippets']:
     if s['field']=='findings':self.assertEqual(s['text'],raw[s['block_id']][s['start_offset']:s['end_offset']]);self.assertEqual(s['page_start'],1)
 def test_negative_finding_not_rewritten_as_improvement(self):
  with tempfile.TemporaryDirectory() as root:
   r=self.extract(root,'We observed no reduction in the synthetic test error.');self.assertEqual(r['findings'],'We observed no reduction in the synthetic test error.')
 def test_future_and_reference_text_not_presented_as_findings(self):
  with tempfile.TemporaryDirectory() as root:
   r=self.extract(root,'We will observe the domains in a future synthetic experiment.');self.assertEqual(r['findings'],'');self.assertFalse(any(s['field']=='findings' for s in r['source_snippets']))
if __name__=='__main__':unittest.main(verbosity=2)
