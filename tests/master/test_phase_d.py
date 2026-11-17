import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from science_platform.models import *
from science_platform.store import Store
from science_platform.parsing import digest
from science_platform.intelligence import Retriever,compare,gaps,graph,answer
from science_platform.errors import PlatformError

class ResearchTests(unittest.TestCase):
 def test_1_real_bm25_threshold_and_exclusions(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=Store(Path(tmp)/'db');f=Path(tmp)/'f.pdf';f.write_bytes(b'example')
   for pid,title,venue in [('p1','One','CAV'),('p2','Two','ICML')]:
    s.upsert_paper(Paper(paper_id=pid,doi=None,title=title,source_url='',venue=venue,year=2024));did=s.save_document(pid,digest(f),f,'pdf')
    s.save_parse(did,ParsedDocument(paper_id=pid,document_sha256=digest(f),parser='fixture',parser_version='1',segments=(Segment(segment_id='s',text='minimum cost repair uses proof certificates',page=1,section='Methods',kind='methodology'),Segment(segment_id='r',text='unicorn evidence',page=2,section='References',kind='references'))))
   self.assertEqual(len(Retriever(s).search('proof certificate',venue='CAV')['hits']),1)
   self.assertFalse(Retriever(s).search('unicorn')['hits']);self.assertFalse(Retriever(s).search('quantum ocean')['hits'])
 def rec(self,pid):return ScientificRecord(paper_id=pid,document_sha256='a'*64,extraction_version='x',model='fixture',execution_status='EXECUTED')
 def test_2_compare_preserves_missing(self):
  rows=compare([self.rec('1'),self.rec('2')]);self.assertEqual(rows[0]['quantitative_results'],'Not Reported');self.assertEqual(rows[0]['methodology'],'Not Reported');self.assertEqual(rows[0]['conclusions'],'Not Reported');self.assertIn('No cross-dataset',rows[0]['comparison_warning'])
  with self.assertRaises(PlatformError):compare([self.rec('1')])
 def test_3_gaps_no_global_novelty_claim(self):
  g=gaps([self.rec('1'),self.rec('2')]);self.assertFalse(g['novelty_claims']);self.assertEqual(g['hypotheses'],[]);self.assertIn('does not establish absence',g['observations'][0]['text'])
 def test_4_graph_only_actual_relations(self):
  papers=[Paper(paper_id='1',doi='10.1234/a',title='One',source_url='',references=('10.1234/b',)),Paper(paper_id='2',doi='10.1234/b',title='Two',source_url='')]
  g=graph(papers,[]);self.assertEqual(len(g['edges']),1);self.assertEqual(g['edges'][0]['type'],'PAPER_CITES_PAPER');self.assertFalse(any(n['kind']=='Algorithm' for n in g['nodes']))
 def test_5_assistant_abstains_without_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertEqual(answer(Store(Path(tmp)/'db'),'unreported optimality proof')['status'],'INSUFFICIENT_EVIDENCE')
if __name__=='__main__':unittest.main(verbosity=2)
