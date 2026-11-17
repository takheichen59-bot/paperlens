import sys,tempfile,socket,asyncio,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
import httpx,pymupdf as fitz
from science_platform.acquisition import SafeAcquirer,OfficialSourceAcquirer
from science_platform.models import FullTextLink
from science_platform.errors import PlatformError

class AcquisitionTests(unittest.TestCase):
 def run_case(self,content,expected=None,*,redirect=False):
  async def run():
   calls=[]
   async def dns(host,port):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1' if host=='private.example' else '93.184.216.34',port))]
   def handler(req):
    calls.append(str(req.url));return httpx.Response(302,headers={'Location':'https://private.example/x'}) if redirect else httpx.Response(200,content=content)
   with tempfile.TemporaryDirectory() as tmp:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
     a=SafeAcquirer(tmp,client=c,resolver=dns);link=FullTextLink(url='https://public.example/p.pdf',kind='pdf',access='OPEN_ACCESS',license='https://creativecommons.org/licenses/by/4.0/')
     if expected:
      with self.assertRaises(PlatformError) as caught:await a.acquire(link)
      self.assertEqual(caught.exception.code,expected)
     else:
      first=await a.acquire(link);second=await a.acquire(link);self.assertEqual(first['sha256'],second['sha256']);self.assertEqual(len(list(Path(tmp).glob('*.pdf'))),1);self.assertEqual(first['bytes'],len(content));self.assertEqual(first['probe']['pages'],1)
     self.assertFalse(list(Path(tmp).glob('*.part')))
     if redirect:self.assertEqual(len(calls),1)
  asyncio.run(run())
 def test_real_pdf_validation_and_duplicate(self):
  d=fitz.open();p=d.new_page();p.insert_text((72,72),'Acquisition engineering fixture');raw=d.tobytes();d.close();self.run_case(raw)
 def test_corrupt_pdf(self):self.run_case(b'%PDF-1.7\ntruncated','PDF_CORRUPTED')
 def test_html(self):self.run_case(b'<html>paywall</html>','INVALID_PDF_FORMAT')
 def test_private_redirect(self):self.run_case(b'','UNSAFE_FULLTEXT_URL',redirect=True)
 def test_official_mode_rejects_unknown_host(self):
  async def run():
   async def dns(h,p):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',p))]
   with tempfile.TemporaryDirectory() as tmp:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,content=b''))) as c:
     with self.assertRaises(PlatformError) as e:await OfficialSourceAcquirer(tmp,client=c,resolver=dns).acquire(FullTextLink(url='https://other.example/x',kind='pdf',access='OPEN_ACCESS'))
     self.assertEqual(e.exception.code,'HOST_NOT_IN_OFFICIAL_SOURCE_ALLOWLIST')
  asyncio.run(run())
if __name__=='__main__':unittest.main(verbosity=2)
