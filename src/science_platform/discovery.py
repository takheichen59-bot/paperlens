"""Independent metadata adapters. Provider failures never fabricate records."""
from abc import ABC,abstractmethod
from datetime import datetime,timezone
from hashlib import sha256
from urllib.parse import unquote,urlsplit,quote
import asyncio,json,re,time
import httpx,feedparser
from .models import *
from .errors import PlatformError

def normalize_doi(value):
 if not value:return None
 value=unquote(str(value).strip())
 value=re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)','',value,flags=re.I).strip().lower()
 if not re.fullmatch(r'10\.\d{4,9}/[^\s?#]+',value):raise ValueError('Invalid DOI')
 return value

def maybe_doi(value):
 try:return normalize_doi(value)
 except (TypeError,ValueError):return None

def plain(value):return re.sub(r'\s+',' ',re.sub(r'<[^>]*>',' ',str(value or ''))).strip()
def timestamp():return datetime.now(timezone.utc).isoformat()
def paper(provider,sid,*,doi=None,title,authors=(),venue=None,year=None,citations=None,oa=None,abstract='',url,links=(),refs=()):
 doi=maybe_doi(doi);pid='doi:'+doi if doi else provider+':'+str(sid)
 return Paper(paper_id=pid,doi=doi,title=plain(title),authors=tuple(Author(name=plain(a.get('name','')),orcid=a.get('orcid')) for a in authors if a.get('name')),
  venue=plain(venue) or None,year=int(year) if year else None,citation_count=int(citations) if citations is not None else None,is_open_access=oa,
  abstract=plain(abstract),source_url=url,fulltext_links=tuple(links),references=tuple(dict.fromkeys(d for d in (maybe_doi(x) for x in refs) if d)),
  sources=(SourceFact(provider=provider,source_id=str(sid),retrieved_at=timestamp(),citation_count=int(citations) if citations is not None else None,venue=plain(venue) or None,year=int(year) if year else None),))

class ProviderHTTP:
 def __init__(self,client=None,interval=1.,retries=2):
  self.client=client or httpx.AsyncClient(timeout=20,follow_redirects=False);self.owned=client is None;self.interval=interval;self.retries=retries;self.last=0.;self.lock=asyncio.Lock()
 async def get(self,url,**kwargs):
  for attempt in range(self.retries+1):
   async with self.lock:
    delay=max(0,self.last+self.interval-time.monotonic())
    if delay:await asyncio.sleep(delay)
    self.last=time.monotonic()
   try:r=await self.client.get(url,**kwargs)
   except httpx.HTTPError:
    if attempt<self.retries:await asyncio.sleep(2**attempt);continue
    raise PlatformError('NETWORK_ERROR',retryable=True) from None
   if r.status_code in (401,403):raise PlatformError('AUTHORIZATION_REQUIRED',status=r.status_code)
   if r.status_code==429 or r.status_code>=500:
    if attempt<self.retries:
     try:delay=min(30,max(0,float(r.headers.get('Retry-After',2**attempt))))
     except ValueError:delay=2**attempt
     await asyncio.sleep(delay);continue
    raise PlatformError('RATE_LIMITED' if r.status_code==429 else 'SOURCE_UNAVAILABLE',retryable=True,status=r.status_code)
   if not r.is_success:raise PlatformError('SOURCE_HTTP_ERROR',status=r.status_code)
   if len(r.content)>16000000:raise PlatformError('SOURCE_RESPONSE_TOO_LARGE')
   return r
 async def aclose(self):
  if self.owned:await self.client.aclose()

class BaseDiscovery(ABC):
 name:str
 def __init__(self,http=None,api_key=None):self.http=http or ProviderHTTP();self.api_key=api_key
 @abstractmethod
 async def search(self,query:SearchQuery,cursor:str|None=None)->SearchPage:...
 async def aclose(self):await self.http.aclose()

class Crossref(BaseDiscovery):
 name='crossref'
 async def search(self,q,cursor=None):
  params={'rows':min(50,q.target),'cursor':cursor or '*'}
  if q.doi:
   data=(await self.http.get('https://api.crossref.org/works/'+quote(normalize_doi(q.doi),safe=''))).json()['message'];items=[data];nxt=None;total=1
  else:
   if q.query:params['query.bibliographic']=q.query
   if q.author:params['query.author']=q.author
   if q.venue:params['query.container-title']=q.venue
   filters=[]
   if q.year_from:filters.append('from-pub-date:'+str(q.year_from)+'-01-01')
   if q.year_to:filters.append('until-pub-date:'+str(q.year_to)+'-12-31')
   if filters:params['filter']=','.join(filters)
   response=(await self.http.get('https://api.crossref.org/works',params=params)).json()['message'];items=response.get('items',[]);nxt=response.get('next-cursor') if items else None;total=response.get('total-results')
  out=[]
  for x in items:
   dates=x.get('published',x.get('issued',{})).get('date-parts',[]);year=dates[0][0] if dates and dates[0] else None
   authors=[{'name':' '.join(filter(None,[a.get('given'),a.get('family')])) or a.get('name',''),'orcid':a.get('ORCID')} for a in x.get('author',[])]
   links=tuple(FullTextLink(url=l['URL'],kind='pdf' if 'pdf' in l.get('content-type','') else 'xml',access='UNKNOWN') for l in x.get('link',[]) if l.get('URL') and any(k in l.get('content-type','') for k in ('pdf','xml')))
   out.append(paper(self.name,x.get('DOI',''),doi=x.get('DOI'),title=(x.get('title') or [''])[0],authors=authors,venue=(x.get('container-title') or [None])[0],year=year,citations=x.get('is-referenced-by-count'),abstract=x.get('abstract',''),url=x.get('URL') or 'https://doi.org/'+x['DOI'],links=links,refs=[r.get('DOI') for r in x.get('reference',[])]))
  return SearchPage(papers=tuple(out),next_cursor=nxt,total=total)

class OpenAlex(BaseDiscovery):
 name='openalex'
 async def search(self,q,cursor=None):
  params={'per-page':min(50,q.target),'cursor':cursor or '*'}
  if q.query:params['search']=q.query
  if self.api_key:params['api_key']=self.api_key
  filters=[]
  if q.doi:filters.append('doi:https://doi.org/'+normalize_doi(q.doi))
  if q.year_from:filters.append('from_publication_date:'+str(q.year_from)+'-01-01')
  if q.year_to:filters.append('to_publication_date:'+str(q.year_to)+'-12-31')
  if q.min_citations is not None:filters.append('cited_by_count:>'+str(q.min_citations-1))
  if q.open_access is not None:filters.append('is_oa:'+str(q.open_access).lower())
  if filters:params['filter']=','.join(filters)
  data=(await self.http.get('https://api.openalex.org/works',params=params)).json();out=[]
  for x in data.get('results',[]):
   loc=x.get('best_oa_location') or {};primary=x.get('primary_location') or {};source=primary.get('source') or {};links=[]
   if loc.get('pdf_url'):links.append(FullTextLink(url=loc['pdf_url'],kind='pdf',access='OPEN_ACCESS',license=loc.get('license')))
   inv=x.get('abstract_inverted_index') or {};words={i:w for w,positions in inv.items() for i in positions};abstract=' '.join(words[i] for i in sorted(words))
   out.append(paper(self.name,x['id'],doi=x.get('doi'),title=x.get('title',''),authors=[{'name':a['author']['display_name'],'orcid':a['author'].get('orcid')} for a in x.get('authorships',[])],venue=source.get('display_name'),year=x.get('publication_year'),citations=x.get('cited_by_count'),oa=x.get('open_access',{}).get('is_oa'),abstract=abstract,url=x.get('doi') or primary.get('landing_page_url') or x['id'],links=links,refs=[]))
  return SearchPage(papers=tuple(out),next_cursor=data.get('meta',{}).get('next_cursor'),total=data.get('meta',{}).get('count'))

class SemanticScholar(BaseDiscovery):
 name='semantic_scholar'
 async def search(self,q,cursor=None):
  fields='title,authors,year,venue,citationCount,externalIds,openAccessPdf,url,abstract,references.externalIds'
  headers={'x-api-key':self.api_key} if self.api_key else {}
  if q.doi:
   data=(await self.http.get('https://api.semanticscholar.org/graph/v1/paper/DOI:'+quote(normalize_doi(q.doi),safe=''),params={'fields':fields},headers=headers)).json();items=[data];nxt=None;total=1
  else:
   params={'query':q.query or q.author or q.venue,'limit':min(50,q.target),'offset':int(cursor or '0'),'fields':fields}
   if q.year_from or q.year_to:params['year']=str(q.year_from or '')+'-'+str(q.year_to or '')
   data=(await self.http.get('https://api.semanticscholar.org/graph/v1/paper/search',params=params,headers=headers)).json();items=data.get('data',[]);nxt=str(data['next']) if data.get('next') is not None else None;total=data.get('total')
  out=[]
  for x in items:
   oa=x.get('openAccessPdf') or {};links=(FullTextLink(url=oa['url'],kind='pdf',access='OPEN_ACCESS',license=oa.get('license')),) if oa.get('url') else ()
   out.append(paper(self.name,x['paperId'],doi=x.get('externalIds',{}).get('DOI'),title=x.get('title',''),authors=[{'name':a['name']} for a in x.get('authors',[])],venue=x.get('venue'),year=x.get('year'),citations=x.get('citationCount'),oa=bool(links) if oa else None,abstract=x.get('abstract',''),url=x.get('url') or 'https://www.semanticscholar.org/paper/'+x['paperId'],links=links,refs=[r.get('externalIds',{}).get('DOI') for r in x.get('references',[])]))
  return SearchPage(papers=tuple(out),next_cursor=nxt,total=total)

class Springer(BaseDiscovery):
 name='springer'
 async def search(self,q,cursor=None):
  if not self.api_key:raise PlatformError('AUTHORIZATION_REQUIRED')
  terms=('doi:'+normalize_doi(q.doi)) if q.doi else q.query
  if q.author:terms+=' name:"'+q.author.replace('"','')+'"'
  if q.venue:terms+=' journal:"'+q.venue.replace('"','')+'"'
  data=(await self.http.get('https://api.springernature.com/meta/v2/json',params={'q':terms,'s':int(cursor or '1'),'p':min(50,q.target),'api_key':self.api_key})).json();out=[]
  for x in data.get('records',[]):
   out.append(paper(self.name,x.get('identifier') or x.get('doi',''),doi=x.get('doi'),title=x.get('title',''),authors=[{'name':a.get('creator','')} for a in x.get('creators',[])],venue=x.get('publicationName'),year=int(x['publicationDate'][:4]) if x.get('publicationDate') else None,oa=str(x.get('openaccess','')).lower()=='true',abstract=x.get('abstract',''),url='https://doi.org/'+x['doi'] if x.get('doi') else x.get('url',[{}])[0].get('value','')))
  total=int((data.get('result') or [{}])[0].get('total',0));n=int(cursor or '1')+len(out)
  return SearchPage(papers=tuple(out),next_cursor=str(n) if out and n<=total else None,total=total)

class Elsevier(BaseDiscovery):
 name='elsevier'
 async def search(self,q,cursor=None):
  if not self.api_key:raise PlatformError('AUTHORIZATION_REQUIRED')
  expr='DOI('+normalize_doi(q.doi)+')' if q.doi else 'TITLE-ABS-KEY('+q.query+')'
  if q.author:expr+=' AND AUTH('+q.author+')'
  if q.venue:expr+=' AND SRCTITLE('+q.venue+')'
  data=(await self.http.get('https://api.elsevier.com/content/search/scopus',params={'query':expr,'start':int(cursor or '0'),'count':min(25,q.target)},headers={'X-ELS-APIKey':self.api_key,'Accept':'application/json'})).json().get('search-results',{});out=[]
  for x in data.get('entry',[]):
   if 'dc:title' not in x:continue
   out.append(paper(self.name,x.get('dc:identifier',''),doi=x.get('prism:doi'),title=x['dc:title'],authors=[{'name':x['dc:creator']}] if x.get('dc:creator') else [],venue=x.get('prism:publicationName'),year=int(x['prism:coverDate'][:4]) if x.get('prism:coverDate') else None,citations=int(x['citedby-count']) if x.get('citedby-count') else None,oa=str(x.get('openaccess',''))=='1',url='https://doi.org/'+x['prism:doi'] if x.get('prism:doi') else 'https://www.scopus.com/record/display.uri?eid='+x.get('eid','')))
  total=int(data.get('opensearch:totalResults',0));n=int(cursor or '0')+len(out)
  return SearchPage(papers=tuple(out),next_cursor=str(n) if out and n<total else None,total=total)

class Arxiv(BaseDiscovery):
 name='arxiv'
 async def search(self,q,cursor=None):
  expr='doi:"'+normalize_doi(q.doi)+'"' if q.doi else 'all:"'+q.query.replace('"',' ')+'"'
  if q.author:expr+=' AND au:"'+q.author.replace('"','')+'"'
  data=feedparser.parse((await self.http.get('https://export.arxiv.org/api/query',params={'search_query':expr,'start':int(cursor or '0'),'max_results':min(50,q.target),'sortBy':'relevance'})).content);out=[]
  for x in data.entries:
   sid=x.id.rsplit('/abs/',1)[-1]
   out.append(paper(self.name,sid,doi=x.get('arxiv_doi'),title=x.title,authors=[{'name':a.name} for a in x.get('authors',[])],year=int(x.published[:4]),abstract=x.get('summary',''),url='https://arxiv.org/abs/'+sid,oa=True,links=(FullTextLink(url='https://arxiv.org/pdf/'+sid,kind='pdf',access='OPEN_ACCESS'),)))
  n=int(cursor or '0')+len(out);total=int(data.feed.get('opensearch_totalresults',len(out)))
  return SearchPage(papers=tuple(out),next_cursor=str(n) if out and n<total else None,total=total)

PROVIDERS={c.name:c for c in [Crossref,OpenAlex,SemanticScholar,Springer,Elsevier,Arxiv]}

def matches(p,q):
 if q.author and not any(q.author.casefold() in a.name.casefold() for a in p.authors):return False
 if q.venue and q.venue.casefold() not in (p.venue or '').casefold():return False
 if q.year_from and (p.year is None or p.year<q.year_from):return False
 if q.year_to and (p.year is None or p.year>q.year_to):return False
 if q.min_citations is not None and (p.citation_count is None or p.citation_count<q.min_citations):return False
 if q.open_access is not None and p.is_open_access!=q.open_access:return False
 return True

def deduplicate(papers):
 out={};identities={}
 for p in papers:
  secondary=(re.sub(r'\W+','',p.title.casefold()),p.year,p.authors[0].name.casefold() if p.authors else '')
  key=('doi:'+p.doi) if p.doi else p.paper_id
  match=identities.get(secondary)
  if match and (not p.doi or not out[match].doi or p.doi==out[match].doi):key=match
  if key in out:
   old=out[key];conflicts=old.conflicts+tuple(f for f in ['title','year','venue'] if getattr(p,f) and getattr(old,f) and getattr(p,f)!=getattr(old,f))
   out[key]=old.model_copy(update={'sources':tuple(dict.fromkeys(old.sources+p.sources)),'fulltext_links':tuple(dict.fromkeys(old.fulltext_links+p.fulltext_links)),'references':tuple(dict.fromkeys(old.references+p.references)),'conflicts':tuple(dict.fromkeys(conflicts)),'doi':old.doi or p.doi})
  else:out[key]=p
  identities[secondary]=key
 return tuple(out.values())
