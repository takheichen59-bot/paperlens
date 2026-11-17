from pathlib import Path
from tempfile import TemporaryDirectory
import asyncio,json,socket,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import httpx
from science_platform.discovery import *
from science_platform.store import Store
from science_platform.acquisition import SafeAcquirer,public_target
from science_platform.venues import VenueRegistry

def public_dns(host,port):
 async def result():return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',port))]
 return result()
class PhaseB(unittest.TestCase):
 def test_normalization_dedup_and_registry(self):
  self.assertEqual(normalize_doi('https://doi.org/10.1234/ABC'),'10.1234/abc')
  p=paper('crossref','1',doi='10.1234/a',title='Same title',url='https://doi.org/10.1234/a',year=2024,authors=[{'name':'A'}])
  p2=p.model_copy(update={'sources':(SourceFact(provider='openalex',source_id='W1',retrieved_at='now'),)})
  self.assertEqual(len(deduplicate([p,p2])),1);self.assertEqual(len(deduplicate([p,p.model_copy(update={'doi':'10.1234/b','paper_id':'other'})])),2)
  self.assertTrue(VenueRegistry().match('Proceedings of the International Conference on Machine Learning'));self.assertFalse(VenueRegistry().match('satisfaction in chemical reactions'))
 def test_provider_contracts_offline_fixture(self):
  def handler(request):return httpx.Response(200,json={'message':{'items':[{'DOI':'10.1234/A','title':['Fixture title'],'author':[{'given':'Ada','family':'Lovelace'}],'container-title':['CAV'],'published':{'date-parts':[[2024,1]]},'is-referenced-by-count':7,'URL':'https://doi.org/10.1234/A'}],'total-results':1}})
  async def run():
   async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
    page=await Crossref(ProviderHTTP(c,interval=0)).search(SearchQuery(query='fixture'))
    self.assertEqual(page.papers[0].authors[0].name,'Ada Lovelace');self.assertEqual(page.papers[0].year,2024);self.assertEqual(page.papers[0].venue,'CAV');self.assertIsNone(page.papers[0].is_open_access)
    self.assertFalse(matches(page.papers[0],SearchQuery(query='fixture',open_access=True)))
  asyncio.run(run())
 def test_missing_credentials_and_rate_limit(self):
  async def run():
   with self.assertRaises(PlatformError):await Springer().search(SearchQuery(query='fixture'))
   count=0
   def handler(request):
    nonlocal count;count+=1;return httpx.Response(429,headers={'Retry-After':'0'})
   async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
    with self.assertRaises(PlatformError) as error:await ProviderHTTP(c,interval=0,retries=2).get('https://api.crossref.org/works')
    self.assertEqual(error.exception.code,'RATE_LIMITED');self.assertEqual(count,3)
  asyncio.run(run())
 def test_ssrf_redirect_and_html_rejected(self):
  async def run():
   async def private(host,port):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',port))]
   with self.assertRaises(PlatformError):await public_target('https://example.org/file',private)
   with self.assertRaises(PlatformError):await public_target('http://user:secret@public.org/a',public_dns)
   with TemporaryDirectory() as d:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'Location':'https://127.0.0.1/secret'}))) as c:
     with self.assertRaises(PlatformError):await SafeAcquirer(d,client=c,resolver=private).acquire(FullTextLink(url='https://example.org/a',kind='pdf',access='OPEN_ACCESS'))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b'<html>not a PDF</html>'))) as c:
     with self.assertRaises(PlatformError) as error:await SafeAcquirer(d,client=c,resolver=public_dns).acquire(FullTextLink(url='https://example.org/a',kind='pdf',access='OPEN_ACCESS'))
     self.assertEqual(error.exception.code,'INVALID_PDF_FORMAT')
    self.assertFalse(list(Path(d).glob('*.part')))
  asyncio.run(run())
 def test_transactional_job_and_document_history(self):
  with TemporaryDirectory() as d:
   store=Store(Path(d)/'new.sqlite');p=store.upsert_paper(paper('fixture','1',title='Real database fixture',url='https://example.org/p'))
   file=Path(d)/'one';file.write_text('one');did=store.save_document(p.paper_id,'a'*64,file,'pdf')
   r=ScientificRecord(paper_id=p.paper_id,document_sha256='a'*64,extraction_version='test',model='none',execution_status='NOT_EXECUTED')
   eid=store.save_extraction(did,r);self.assertEqual(store.extraction(p.paper_id)['extraction_id'],eid)
   store.save_document(p.paper_id,'b'*64,file,'pdf');self.assertIsNone(store.extraction(p.paper_id));self.assertEqual(store.history(p.paper_id)[0]['status'],'STALE')
   jid=store.enqueue('search',{},idempotency_key='fixed');self.assertEqual(store.enqueue('search',{},idempotency_key='fixed'),jid)
   self.assertEqual(store.claim('worker')['job_id'],jid);self.assertIsNone(store.claim('other'));store.pause(jid);store.resume(jid);self.assertEqual(store.claim('other')['job_id'],jid)
if __name__=='__main__':unittest.main(verbosity=2)
