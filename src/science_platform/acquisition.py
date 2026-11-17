"""Public-IP-pinned acquisition with explicit redirect, byte and format budgets."""
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from uuid import uuid4
import asyncio,hashlib,ipaddress,json,os,socket,subprocess,sys
from abc import ABC,abstractmethod
import httpx
from .errors import PlatformError

async def public_target(url,resolver=None):
 try:
  u=urlsplit(url)
  if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password or u.port not in (None,80,443) or any(c.isspace() for c in url):raise ValueError()
  host=u.hostname.encode('idna').decode();port=u.port or (443 if u.scheme=='https' else 80)
  if host.lower()=='localhost' or host.lower().endswith(('.local','.internal','.localhost')):raise ValueError()
  addresses=await (resolver(host,port) if resolver else asyncio.to_thread(socket.getaddrinfo,host,port,type=socket.SOCK_STREAM))
  ips=list(dict.fromkeys(a[4][0] for a in addresses))
  if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):raise ValueError()
  return httpx.URL(url).copy_with(host=ips[0]),host,port
 except (ValueError,UnicodeError,OSError):raise PlatformError('UNSAFE_FULLTEXT_URL') from None

class BaseAcquirer(ABC):
 @abstractmethod
 async def acquire(self,link):...
 @abstractmethod
 async def aclose(self):...

class SafeAcquirer(BaseAcquirer):
 def __init__(self,directory,*,max_bytes=100*1024*1024,client=None,resolver=None,official_sources_only=False):
  self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True);self.max_bytes=max_bytes;self.client=client or httpx.AsyncClient(timeout=45,follow_redirects=False,trust_env=False);self.owned=client is None;self.resolver=resolver;self.official_sources_only=official_sources_only
 async def acquire(self,link):
  if link.access not in {'OPEN_ACCESS','AUTHORIZED_API'}:raise PlatformError('FULLTEXT_UNAVAILABLE')
  if link.access=='AUTHORIZED_API':raise PlatformError('LICENSED_FULLTEXT_NOT_CONFIGURED')
  current=link.url;response=None;temporary=self.directory/(uuid4().hex+'.part')
  try:
   for hop in range(6):
    pinned,host,port=await public_target(current,self.resolver)
    headers={'Host':host if port in (80,443) else f'{host}:{port}','User-Agent':'ScientificLiteraturePlatform/0.3 scholarly research'}
    if self.official_sources_only and host not in {'arxiv.org','export.arxiv.org','pmc.ncbi.nlm.nih.gov','europepmc.org'}:raise PlatformError('HOST_NOT_IN_OFFICIAL_SOURCE_ALLOWLIST')
    request=self.client.build_request('GET',current if self.official_sources_only else pinned,headers=headers,extensions={'sni_hostname':host})
    response=await self.client.send(request,stream=True,follow_redirects=False)
    if response.status_code in (301,302,303,307,308):
     location=response.headers.get('location');await response.aclose();response=None
     if not location or hop==5:raise PlatformError('REDIRECT_LIMIT')
     target=urljoin(current,location)
     if urlsplit(current).scheme=='https' and urlsplit(target).scheme!='https':raise PlatformError('UNSAFE_REDIRECT_DOWNGRADE')
     current=target;continue
    if response.status_code in (401,403):raise PlatformError('FULLTEXT_UNAVAILABLE',status=response.status_code)
    if response.status_code==429:raise PlatformError('RATE_LIMITED',retryable=True,status=429)
    if response.status_code!=200:raise PlatformError('FULLTEXT_UNAVAILABLE',status=response.status_code)
    break
   if not response:raise PlatformError('FULLTEXT_UNAVAILABLE')
   try:length=int(response.headers.get('content-length') or 0)
   except ValueError:length=0
   if length>self.max_bytes:raise PlatformError('SIZE_LIMIT')
   size=0;digest=hashlib.sha256()
   with temporary.open('wb') as handle:
    async for chunk in response.aiter_bytes():
     size+=len(chunk)
     if size>self.max_bytes:raise PlatformError('SIZE_LIMIT')
     digest.update(chunk);handle.write(chunk)
   if link.kind=='pdf':
    with temporary.open('rb') as handle:header=handle.read(1024)
    if not header.startswith(b'%PDF-'):raise PlatformError('INVALID_PDF_FORMAT')
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(str(p) for p in sys.path if p)
    result=await asyncio.to_thread(subprocess.run,[sys.executable,'-m','science_platform.pdf_probe',str(temporary)],capture_output=True,timeout=50,env=env)
    if result.returncode:raise PlatformError('PDF_CORRUPTED')
    probe=json.loads(result.stdout)
   else:
    from xml.etree import ElementTree as ET
    raw=temporary.read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise PlatformError('UNSAFE_XML')
    try:ET.fromstring(raw)
    except ET.ParseError:raise PlatformError('INVALID_XML_FORMAT') from None
    probe={'kind':'xml'}
   sha=digest.hexdigest();target=self.directory/(sha+'.'+link.kind)
   if target.exists():
    existing=hashlib.sha256(target.read_bytes()).hexdigest()
    if existing!=sha:raise PlatformError('CACHE_HASH_MISMATCH')
   else:temporary.replace(target)
   return {'sha256':sha,'path':str(target),'bytes':size,'source_url':current,'license':link.license,'access_status':'FULLTEXT_AVAILABLE','acquisition_method':('OFFICIAL_HOST_ALLOWLIST_EGRESS_' if self.official_sources_only else 'PUBLIC_IP_PINNED_')+link.kind.upper(),'downloaded_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'reuse_scope':'FOLLOW_RECORDED_LICENSE' if link.license else 'UNKNOWN_REUSE_PERMISSION','probe':probe}
  except (httpx.HTTPError,subprocess.TimeoutExpired):raise PlatformError('ACQUISITION_TIMEOUT_OR_NETWORK',retryable=True) from None
  finally:
   if response:await response.aclose()
   temporary.unlink(missing_ok=True)
 async def aclose(self):
  if self.owned:await self.client.aclose()

class OfficialSourceAcquirer(SafeAcquirer):
 """Configured egress proxy is trusted only for four fixed official hosts.

 Generic OA URLs still require the IP-pinned acquirer. All redirects are resolved,
 checked for public IPs, and restricted to the same fixed official-host registry.
 """
 def __init__(self,directory,**kwargs):
  client=kwargs.pop('client',None)
  super().__init__(directory,client=client or httpx.AsyncClient(timeout=45,follow_redirects=False,trust_env=True),official_sources_only=True,**kwargs)
  self.owned=client is None
