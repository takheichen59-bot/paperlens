"""Durable bounded worker. Long jobs never run on the HTTP event loop."""
import asyncio,json,os,threading,time,uuid
from pathlib import Path
from urllib.parse import urlsplit
from .store import Store
from .models import Paper,SearchQuery,ScientificRecord
from .discovery import PROVIDERS,ProviderHTTP,deduplicate,matches
from .acquisition import SafeAcquirer,OfficialSourceAcquirer
from .parsing import ParserRouter,digest
from .extraction import DeepExtractor
from .errors import PlatformError

class PersistentHTTP(ProviderHTTP):
 def __init__(self,store,provider):super().__init__();self.store=store;self.provider=provider
 async def get(self,*args,**kwargs):
  delay=self.store.reserve_source(self.provider,1.1)
  if delay:await asyncio.sleep(delay)
  return await super().get(*args,**kwargs)

class Worker:
 def __init__(self,store,directory,*,lease_seconds=120):self.store=store;self.directory=Path(directory);self.owner=uuid.uuid4().hex;self.stop=threading.Event();self.lease_seconds=max(5,lease_seconds)
 def heartbeat(self,jid,**kwargs):self.store.update_job(jid,self.owner,lease_seconds=self.lease_seconds,**kwargs)
 def one(self):
  job=self.store.claim(self.owner,lease_seconds=self.lease_seconds)
  if not job:return False
  jid=job['job_id'];finish=threading.Event()
  def renew():
   while not finish.wait(min(25,self.lease_seconds/3)):
    try:self.heartbeat(jid)
    except PlatformError:return
  thread=threading.Thread(target=renew,daemon=True);thread.start()
  try:
   payload=json.loads(job['payload_json']);self.store.event(jid,'START',{'attempt':job['attempts'],'kind':job['kind']})
   if job['kind']=='discovery':result=asyncio.run(self.discover(job,payload))
   elif job['kind']=='batch':result=self.batch(job,payload)
   else:raise PlatformError('UNKNOWN_JOB_KIND')
   self.heartbeat(jid,status='COMPLETED',result=result);self.store.event(jid,'COMPLETED',{'kind':job['kind']})
  except PlatformError as e:
   if e.code!='JOB_LEASE_LOST':
    try:self.heartbeat(jid,status='FAILED',error=e.code);self.store.event(jid,'FAILED',e.safe())
    except PlatformError:pass
  except Exception:
   # No exception body: external requests, prompts and credentials cannot enter logs.
   try:self.heartbeat(jid,status='FAILED',error='INTERNAL_PROCESSING_ERROR');self.store.event(jid,'FAILED',{'code':'INTERNAL_PROCESSING_ERROR'})
   except PlatformError:pass
  finally:finish.set();thread.join(timeout=1)
  return True
 def serve(self):
  while not self.stop.is_set():
   if not self.one():self.stop.wait(.4)
 async def discover(self,job,payload):
  q=SearchQuery.model_validate_json(json.dumps(payload));jid=job['job_id'];state=json.loads(job['result_json'] or '{}')
  statuses=state.get('sources',{});raw=state.get('raw_received',0);current=[Paper.model_validate_json(r['metadata_json']) for r in self.store.search_results(jid)]
  env={'openalex':'OPENALEX_API_KEY','semantic_scholar':'SEMANTIC_SCHOLAR_API_KEY','springer':'SPRINGER_API_KEY','elsevier':'ELSEVIER_API_KEY'}
  providers={name:PROVIDERS[name](http=PersistentHTTP(self.store,name),api_key=os.getenv(env.get(name,''))) for name in q.providers if name in PROVIDERS}
  if len(providers)!=len(q.providers):raise PlatformError('UNKNOWN_DISCOVERY_PROVIDER')
  try:
   # Persist each page and its cursor before moving on; source failures are independent.
   for cycle in range(max(2,(q.target+49)//50*3)):
    active=False
    for name,adapter in providers.items():
     s=statuses.setdefault(name,{'pages':0,'cursor':None,'status':'QUEUED'})
     if s['status'] in {'EXHAUSTED','FAILED','NOT_EXECUTED'}:continue
     active=True;self.heartbeat(jid)
     try:
      page=await adapter.search(q,s['cursor']);raw+=len(page.papers);current=deduplicate(current+[p for p in page.papers if matches(p,q)])[:q.target]
      self.store.save_search_results(jid,current);s.update(pages=s['pages']+1,cursor=page.next_cursor,status='READY' if page.next_cursor else 'EXHAUSTED',reported_total=page.total)
     except PlatformError as e:s.update(status='NOT_EXECUTED' if 'KEY_REQUIRED' in e.code or 'NOT_CONFIGURED' in e.code else 'FAILED',error=e.safe())
     except (ValueError,KeyError,TypeError):s.update(status='FAILED',error={'code':'PROVIDER_RESPONSE_INVALID'})
     state={'target':q.target,'raw_received':raw,'deduplicated':len(current),'sources':statuses,'note':'Target is not a guarantee; only real received records are stored.'};self.heartbeat(jid,progress=len(current),result=state)
    if len(current)>=q.target or not active:break
   if not current and all(s['status'] in {'FAILED','NOT_EXECUTED'} for s in statuses.values()):raise PlatformError('ALL_DISCOVERY_SOURCES_UNAVAILABLE')
   return state
  finally:
   for a in providers.values():await a.aclose()
 async def acquire(self,paper):
  directory=self.directory/'documents';errors=[]
  for link in sorted(paper.fulltext_links,key=lambda l:l.kind!='pdf'):
   if link.access!='OPEN_ACCESS':continue
   official=urlsplit(link.url).hostname in {'arxiv.org','export.arxiv.org','pmc.ncbi.nlm.nih.gov','europepmc.org'}
   adapter=OfficialSourceAcquirer(directory) if official else SafeAcquirer(directory)
   try:return await adapter.acquire(link)
   except PlatformError as e:errors.append(e.code)
   finally:await adapter.aclose()
  self.store.mark_unavailable(paper.paper_id);raise PlatformError(errors[-1] if errors else 'FULLTEXT_UNAVAILABLE')
 def batch(self,job,payload):
  ids=payload['paper_ids'];action=payload['action'];jid=job['job_id'];state=json.loads(job['result_json'] or '{}');items=state.get('items',{})
  for pid in ids:
   if pid in items:continue
   self.heartbeat(jid)
   try:
    row=self.store.paper(pid)
    if not row:raise PlatformError('PAPER_NOT_FOUND')
    paper=Paper.model_validate_json(row['metadata_json']);did=row['current_document']
    if action in {'acquire','all'} and not did:
     receipt=asyncio.run(self.acquire(paper));did=self.store.save_document(pid,receipt['sha256'],receipt['path'],Path(receipt['path']).suffix.lstrip('.'),source_url=receipt['source_url'],license=receipt['license'],method=receipt['acquisition_method'])
    if action in {'parse','extract','all'}:
     if not did:raise PlatformError('FULLTEXT_UNAVAILABLE')
     doc=self.store.document(did)
     if digest(doc['path'])!=doc['sha256']:raise PlatformError('DOCUMENT_FILE_CHANGED')
     parsed=self.store.latest_parse(did)
     if not parsed:
      # Separate process with time/memory limits; hostile PDFs do not share the API process.
      parsed,external=parse_isolated(doc['path'],pid,self.directory);self.store.save_parse(did,parsed);self.store.event(jid,'PARSED',{'paper_id':pid,'external':external})
     if action in {'extract','all'}:
      existing=self.store.extraction(pid)
      if existing and ScientificRecord.model_validate_json(existing['payload_json']).execution_status=='EXECUTED' and not payload.get('force'):rec=ScientificRecord.model_validate_json(existing['payload_json'])
      else:
       extractor=DeepExtractor()
       try:rec=extractor.extract(parsed,heartbeat=lambda:self.heartbeat(jid))
       finally:extractor.client.close()
       self.store.save_extraction(did,rec)
      items[pid]={'status':rec.execution_status,'missing_fields':list(rec.missing_fields),'evidence_count':len(rec.evidence)}
     else:items[pid]={'status':'PARSED','segments':len(parsed.segments)}
    else:items[pid]={'status':'FULLTEXT_AVAILABLE','document_id':did}
   except PlatformError as e:
    if e.code=='JOB_LEASE_LOST':raise
    items[pid]={'status':'FAILED','error':e.safe()}
   except Exception:items[pid]={'status':'FAILED','error':{'code':'PAPER_PROCESSING_ERROR'}}
   self.heartbeat(jid,progress=len(items),result={'items':items,'submitted':len(ids),'processed':len(items)})
  counts={}
  for value in items.values():counts[value['status']]=counts.get(value['status'],0)+1
  return {'items':items,'submitted':len(ids),'processed':len(items),'counts':counts}

def parse_isolated(path,pid,directory):
 import subprocess,sys,tempfile
 from .models import ParsedDocument
 directory.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=directory) as tmp:
  output=Path(tmp)/'parsed.json';env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(str(p) for p in sys.path if p)
  try:r=subprocess.run([sys.executable,'-m','science_platform.parse_worker',str(path),pid,str(output)],capture_output=True,timeout=600,env=env)
  except subprocess.TimeoutExpired:raise PlatformError('PARSER_TIME_BUDGET') from None
  if r.returncode or not output.exists():raise PlatformError('PARSER_SUBPROCESS_FAILED')
  data=json.loads(output.read_text());return ParsedDocument.model_validate_json(json.dumps(data['document'])),data['external']
