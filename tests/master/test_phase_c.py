from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import pymupdf as fitz
from science_platform.models import *
from science_platform.parsing import *
from science_platform.extraction import *

class PhaseC(unittest.TestCase):
 def document(self):return ParsedDocument(paper_id='fixture:1',document_sha256='a'*64,parser='fixture',parser_version='test',segments=(Segment(segment_id='s1',text='The accuracy is 95 percent.',page=1,section='Results',kind='results'),))
 def output(self):
  d=self.document();e=Evidence(evidence_id='e1',paper_id=d.paper_id,document_sha256=d.document_sha256,segment_id='s1',page=1,section='Results',quote=d.segments[0].text,start=0,end=len(d.segments[0].text),extraction_model='test-mock',extraction_version='test',validation_status=ValidationStatus.VERIFIED)
  return TaskOutput(claims=(Claim(claim_id='c1',text=e.quote,evidence_ids=('e1',)),),evidence=(e,))
 def test_grounding_rejects_wrong_hash_span_and_numbers(self):
  d=self.document();o=self.output();validate_task(d,o,extractor_field='results')
  for bad in [o.model_copy(update={'claims':(o.claims[0].model_copy(update={'text':'The accuracy is 99 percent.'}),)}),o.model_copy(update={'evidence':(o.evidence[0].model_copy(update={'document_sha256':'b'*64}),)}),o.model_copy(update={'evidence':(o.evidence[0].model_copy(update={'end':3}),)})]:
   with self.assertRaises(PlatformError):validate_task(d,bad,extractor_field='results')
 def test_no_model_is_not_executed(self):
  client=Mock(configured=False);r=DeepExtractor(client).extract(self.document());self.assertEqual(r.execution_status,'NOT_EXECUTED');self.assertFalse(r.results)
 def test_algorithm_mention_is_not_deep(self):
  d=self.document();o=self.output();algorithm=Algorithm(name='accuracy',algorithm_type='OTHER',novelty='NOT_REPORTED',evidence_ids=('e1',))
  with self.assertRaises(PlatformError):validate_task(d,o.model_copy(update={'algorithms':(algorithm,)}),extractor_field='algorithms')
 def test_external_parser_fixture_alignment_and_uncertainty(self):
  d=self.document();xml='<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><p coords="1,0,0,5,5">The accuracy is 95 percent.</p><formula type="latex">x^{2}=1</formula></body></text></TEI>'
  tei=GrobidParser.parse_tei(xml,d.paper_id,d.document_sha256);self.assertEqual(tei.equations[0].latex,'x^{2}=1');self.assertEqual(tei.equations[0].parse_status,'PARSE_UNCERTAIN')
  result=align_documents(d,tei);self.assertEqual(len(result['mappings']),1);self.assertFalse(result['merged_text']);self.assertTrue(result['conflicts'])
 def test_real_pymupdf_and_tesseract_fixture(self):
  with TemporaryDirectory() as tmp:
   path=Path(tmp)/'text.pdf';doc=fitz.open();p=doc.new_page();p.insert_text((50,80),'Methods',fontname='hebo',fontsize=15);p.insert_text((50,110),'We solve constraints using a SAT solver.',fontsize=12);p.insert_text((50,140),'x = 2 + 1',fontsize=12);doc.save(path);doc.close()
   parsed=PyMuPDFParser().parse(path,'fixture:pdf');self.assertTrue(parsed.segments);self.assertTrue(parsed.equations);self.assertIsNone(parsed.equations[0].latex)
   with fitz.open(path) as source:png=source[0].get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png')
   scan=Path(tmp)/'scan.pdf';doc=fitz.open();p=doc.new_page();p.insert_image(p.rect,stream=png);doc.save(scan);doc.close()
   ocr=TesseractParser().parse(scan,'fixture:scan');self.assertIn('Methods',' '.join(s.text for s in ocr.segments));self.assertIn('OCR_TEXT_UNVERIFIED',ocr.warnings)
if __name__=='__main__':unittest.main(verbosity=2)
