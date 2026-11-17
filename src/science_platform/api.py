"""Versioned local-first API; separate database, no credentials in browser bundles."""
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4
from urllib.parse import urlsplit
import hmac,json,os,shutil,threading
from fastapi import FastAPI,Request,HTTPException,Query,Depends
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import Field,ValidationError
from . import __version__
from .models import *
from .store import Store
from .jobs import Worker
from .errors import PlatformError
from .extraction import OpenAICompatible
from .intelligence import Embeddings,Retriever,answer,compare,gaps,graph
from .exporting import encode_export
from .venues import VenueRegistry

class BatchInput(StrictModel):
 paper_ids:tuple[str,...]=Field(min_length=1,max_length=5000)
 action:Literal['acquire','parse','extract','all'];force:bool=False
class Selection(StrictModel):
 paper_ids:tuple[str,...]=Field(min_length=2,max_length=10)
class Question(StrictModel):
 question:str=Field(min_length=2,max_length=2000);paper_ids:tuple[str,...]=();threshold:float=Field(default=.2,ge=.01,le=20)
class ReviewInput(StrictModel):
 revision:int=Field(ge=0);confirmed:bool=False;notes:str=Field(default='',max_length=10000)
 evidence_ids:tuple[str,...]=()
class VenueInput(StrictModel):
 name:str=Field(min_length=1,max_length=200);domain:str=Field(min_length=1,max_length=80);aliases:tuple[str,...]=()

def input_for(model):
 async def dependency(request:Request):
  data=bytearray()
  async for chunk in request.stream():
   data.extend(chunk)
   if len(data)>2*1024*1024:raise HTTPException(413,'JSON_BODY_TOO_LARGE')
  return model.model_validate_json(bytes(data))
 return dependency

def create_app(directory=None,*,start_worker=True):
 root=Path(directory or os.getenv('PAPERLENS_DATA','./data/science-platform')).resolve();root.mkdir(parents=True,exist_ok=True);store=Store(root/'platform.sqlite3');worker=Worker(store,root)
 @asynccontextmanager
 async def lifespan(app):
  thread=threading.Thread(target=worker.serve,daemon=True)
  if start_worker:thread.start()
  yield
  worker.stop.set()
  if start_worker:thread.join(timeout=2)
 app=FastAPI(title='Scientific Literature Intelligence & Method Mining Platform',version=__version__,lifespan=lifespan)
 app.state.store=store;app.state.worker=worker;app.state.directory=root
 app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.getenv('PAPERLENS_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(','))
 @app.middleware('http')
 async def security(request,call_next):
  if request.url.path.startswith('/api/v1/'):
   token=os.getenv('PAPERLENS_API_TOKEN')
   if token and request.url.path!='/api/v1/health' and not hmac.compare_digest(request.headers.get('Authorization',''),'Bearer '+token):return JSONResponse({'error':'AUTHENTICATION_REQUIRED'},status_code=401)
   origin=request.headers.get('origin')
   if origin and request.method not in {'GET','HEAD','OPTIONS'} and urlsplit(origin).netloc!=request.headers.get('host'):return JSONResponse({'error':'CROSS_ORIGIN_WRITE_REJECTED'},status_code=403)
  response=await call_next(request);response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='same-origin';response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; frame-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'";return response
 @app.exception_handler(ValidationError)
 async def validation_error(request,exc):return JSONResponse({'error':'SCHEMA_VALIDATION_FAILED','fields':[{'loc':e['loc'],'type':e['type']} for e in exc.errors()]},status_code=422)
 @app.exception_handler(PlatformError)
 async def platform_error(request,exc):return JSONResponse({'error':exc.safe()},status_code=409 if exc.code in {'REVIEW_CONFLICT','STALE_DOCUMENT','REFUSE_UNRELATED_DATABASE'} else 422)
 def paper_row(pid,*,verify=True):
  if verify:store.ensure_current(pid)
  row=store.paper(pid)
  if not row:raise HTTPException(404,'PAPER_NOT_FOUND')
  return row
 def public_job(job):
  if not job:raise HTTPException(404,'JOB_NOT_FOUND')
  return {k:json.loads(v) if k.endswith('_json') and v else v for k,v in job.items() if k not in {'owner','lease_until'}}
 def records(ids=()):return [ScientificRecord.model_validate_json(json.dumps(r['extraction'])) for r in store.current_snapshot(ids) if r['extraction']]
 def selected_records(ids):
  rs=records(ids)
  if len(rs)!=len(set(ids)):raise PlatformError('EXTRACTION_NOT_AVAILABLE_FOR_SELECTION')
  return rs
 @app.get('/api/v1/health')
 def health():return {'status':'ok','version':__version__,'database':'sqlite-wal','worker':'embedded-serial' if start_worker else 'external','scientific_accuracy':'NOT_INDEPENDENTLY_EVALUATED'}
 @app.get('/api/v1/capabilities')
 def capabilities():
  client=OpenAICompatible();llm=client.configured;client.close()
  return {'llm':{'configured':llm,'integration_test':'NOT_EXECUTED_UNLESS_EXPLICITLY_REPORTED'},'semantic_embeddings':{'configured':Embeddings().configured},'parsers':{'pymupdf':True,'ocr':bool(shutil.which('tesseract')),'grobid':bool(os.getenv('GROBID_URL')),'docling':bool(os.getenv('DOCLING_COMMAND') or shutil.which('docling'))},'discovery':{'crossref':True,'arxiv':True,'openalex':True,'semantic_scholar':True,'springer':bool(os.getenv('SPRINGER_API_KEY')),'elsevier':bool(os.getenv('ELSEVIER_API_KEY'))},'limits':{'target':5000,'upload_bytes':100*1024*1024,'compare':10},'browser_e2e':'NOT_EXECUTED','human_gold':'NOT_EXECUTED'}
 @app.get('/api/v1/stats')
 def stats():
  data=store.current_snapshot();return {'papers':len(data),'fulltext':sum(bool(r['document_id']) for r in data),'extractions_executed':sum(bool(r['extraction'] and r['extraction']['execution_status']=='EXECUTED') for r in data),'not_executed':sum(bool(r['extraction'] and r['extraction']['execution_status']=='NOT_EXECUTED') for r in data),'jobs':len(store.jobs())}
 @app.post('/api/v1/discovery',status_code=202)
 def discovery(request:Request,q:SearchQuery=Depends(input_for(SearchQuery))):
  return {'job_id':store.enqueue('discovery',q.model_dump(mode='json'),idempotency_key=request.headers.get('Idempotency-Key'),total=q.target)}
 @app.get('/api/v1/jobs')
 def jobs():return {'items':[public_job(j) for j in store.jobs()]}
 @app.get('/api/v1/jobs/{jid}')
 def job(jid:str):return public_job(store.job(jid))
 @app.get('/api/v1/jobs/{jid}/results')
 def job_results(jid:str):
  if not store.job(jid):raise HTTPException(404,'JOB_NOT_FOUND')
  return {'items':[{**json.loads(r['metadata_json']),'access_status':r['access_status']} for r in store.search_results(jid)],'events':store.job_events(jid)}
 @app.post('/api/v1/jobs/{jid}/pause')
 def pause(jid:str):
  if not store.job(jid):raise HTTPException(404,'JOB_NOT_FOUND')
  store.pause(jid);return public_job(store.job(jid))
 @app.post('/api/v1/jobs/{jid}/resume')
 def resume(jid:str):
  if not store.job(jid):raise HTTPException(404,'JOB_NOT_FOUND')
  store.resume(jid);return public_job(store.job(jid))
 @app.post('/api/v1/batch',status_code=202)
 def batch(request:Request,body:BatchInput=Depends(input_for(BatchInput))):
  return {'job_id':store.enqueue('batch',body.model_dump(mode='json'),idempotency_key=request.headers.get('Idempotency-Key'),total=len(body.paper_ids))}
 @app.get('/api/v1/papers')
 def papers(q:str='',venue:str='',year_from:int|None=None,year_to:int|None=None,fulltext:bool|None=None,offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=200)):
  rows=[]
  for r in store.papers(limit=100000):
   p=json.loads(r['metadata_json'])
   if q and q.casefold() not in (p['title']+' '+(p['abstract'] or '')+' '+(p['doi'] or '')).casefold():continue
   if venue and venue.casefold() not in (p['venue'] or '').casefold():continue
   if year_from and (p['year'] is None or p['year']<year_from):continue
   if year_to and (p['year'] is None or p['year']>year_to):continue
   if fulltext is not None and bool(r['current_document'])!=fulltext:continue
   rows.append({**p,'access_status':r['access_status'],'document_id':r['current_document']})
  return {'items':rows[offset:offset+limit],'total':len(rows),'offset':offset,'limit':limit}
 @app.post('/api/v1/papers',status_code=201)
 def add_paper(p:Paper=Depends(input_for(Paper))):
  from .discovery import normalize_doi
  try:doi=normalize_doi(p.doi) if p.doi else None
  except ValueError:raise PlatformError('INVALID_DOI') from None
  return store.upsert_paper(p.model_copy(update={'doi':doi})).model_dump(mode='json')
 @app.get('/api/v1/papers/{pid:path}/detail')
 def detail(pid:str):
  row=paper_row(pid);doc=store.document(row['current_document']) if row['current_document'] else None;parsed=store.latest_parse(row['current_document']) if doc else None;extraction=store.extraction(pid)
  return {'paper':{**json.loads(row['metadata_json']),'access_status':row['access_status']},'document':{k:v for k,v in doc.items() if k!='path'} if doc else None,'parsed':parsed.model_dump(mode='json') if parsed else None,'extraction':{**extraction,'payload_json':json.loads(extraction['payload_json'])} if extraction else None,'review':store.current_review(extraction['extraction_id']) if extraction else None,'history':[{k:v for k,v in h.items() if k!='payload_json'} for h in store.history(pid)]}
 @app.get('/api/v1/papers/{pid:path}/file')
 def document_file(pid:str):
  row=paper_row(pid);doc=store.document(row['current_document']) if row['current_document'] else None
  if not doc or not Path(doc['path']).exists():raise HTTPException(404,'FULLTEXT_UNAVAILABLE')
  from .parsing import digest
  if digest(doc['path'])!=doc['sha256']:raise PlatformError('DOCUMENT_FILE_CHANGED')
  return FileResponse(doc['path'],media_type='application/pdf' if doc['kind']=='pdf' else 'application/xml',headers={'Content-Disposition':'inline'})
 @app.post('/api/v1/papers/{pid:path}/document',status_code=201)
 async def upload(pid:str,request:Request):
  paper_row(pid,verify=False)
  if request.headers.get('content-type','').split(';')[0]!='application/pdf':raise HTTPException(415,'PDF_REQUIRED')
  temp=root/'documents'/(uuid4().hex+'.part');temp.parent.mkdir(parents=True,exist_ok=True);size=0;hasher=sha256()
  try:
   with temp.open('wb') as f:
    async for chunk in request.stream():
     size+=len(chunk)
     if size>100*1024*1024:raise HTTPException(413,'SIZE_LIMIT')
     hasher.update(chunk);f.write(chunk)
   from .acquisition import SafeAcquirer
   import subprocess,sys,asyncio
   env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(str(p) for p in sys.path if p)
   try:probe=await asyncio.to_thread(subprocess.run,[sys.executable,'-m','science_platform.pdf_probe',str(temp)],capture_output=True,timeout=50,env=env)
   except subprocess.TimeoutExpired:raise HTTPException(422,'PDF_PROBE_TIMEOUT') from None
   if probe.returncode:raise HTTPException(422,'INVALID_OR_UNSAFE_PDF')
   digest=hasher.hexdigest();target=temp.with_name(digest+'.pdf');temp.replace(target)
   did=store.save_document(pid,digest,target,'pdf',method='USER_AUTHORIZED_UPLOAD')
   return {'document_id':did,'sha256':digest,'bytes':size,'reuse_permission':'NOT_GRANTED_BY_UPLOAD'}
  finally:temp.unlink(missing_ok=True)
 @app.post('/api/v1/extractions/{eid}/review')
 def review(eid:str,body:ReviewInput=Depends(input_for(ReviewInput))):
  current=next((r for r in store.current_snapshot() if r['extraction_id']==eid),None)
  if not current:raise PlatformError('STALE_DOCUMENT')
  known={e['evidence_id'] for e in current['extraction']['evidence']}
  if any(e not in known for e in body.evidence_ids):raise PlatformError('UNKNOWN_REVIEW_EVIDENCE')
  return {'revision':store.review(eid,body.revision,body.model_dump(mode='json')),'scope':'HUMAN_REVIEW_NOTE_NOT_AUTOMATIC_TRUTH'}
 @app.get('/api/v1/algorithms')
 def algorithms(q:str='',type:str=''):
  items=[{'paper_id':r.paper_id,'document_sha256':r.document_sha256,'algorithm':a.model_dump(mode='json'),'evidence':[e.model_dump(mode='json') for e in r.evidence if e.evidence_id in a.evidence_ids]} for r in records() for a in r.algorithms if (not q or q.casefold() in a.name.casefold()) and (not type or a.algorithm_type==type)]
  return {'items':items,'note':'Validated structured extraction only; no keyword mentions promoted to algorithms.'}
 @app.post('/api/v1/compare')
 def comparison(body:Selection=Depends(input_for(Selection))):
  rs=selected_records(body.paper_ids)
  return {'rows':compare(rs)}
 @app.post('/api/v1/gaps')
 def gap_analysis(body:Selection=Depends(input_for(Selection))):return gaps(selected_records(body.paper_ids))
 @app.get('/api/v1/graph')
 def knowledge_graph():
  snap=store.current_snapshot();return graph([Paper.model_validate_json(json.dumps(r['paper'])) for r in snap],[ScientificRecord.model_validate_json(json.dumps(r['extraction'])) for r in snap if r['extraction']])
 @app.post('/api/v1/assistant')
 def assistant(body:Question=Depends(input_for(Question))):return answer(store,body.question,paper_ids=body.paper_ids,threshold=body.threshold)
 @app.get('/api/v1/venues')
 def venues():return VenueRegistry(root/'custom-venues.json').data['venues']
 @app.post('/api/v1/venues',status_code=201)
 def add_venue(body:VenueInput=Depends(input_for(VenueInput))):
  registry=VenueRegistry(root/'custom-venues.json');registry.add(body.name,body.domain,body.aliases);return {'saved':True}
 def export_selection(ids):
  if ids is not None:
   if not ids or len(ids)>5000 or any(not pid for pid in ids):raise PlatformError('INVALID_EXPORT_SELECTION')
   selected=tuple(dict.fromkeys(ids))
   if any(not store.paper(pid) for pid in selected):raise PlatformError('EXPORT_PAPER_NOT_FOUND')
   return store.current_snapshot(selected)
  return store.current_snapshot()
 @app.get('/api/v1/export')
 def export(format:Literal['jsonl','csv','xlsx']='jsonl',paper_id:list[str]|None=Query(None)):
  selected=export_selection(paper_id)
  data,mime=encode_export(selected,format);return Response(data,media_type=mime,headers={'Content-Disposition':'attachment; filename="research.'+format+'"'})
 @app.get('/api/v1/export/pdf')
 def pdf_bundle(paper_id:list[str]|None=Query(None)):
  import tempfile,zipfile
  from starlette.background import BackgroundTask
  from .parsing import digest
  folder=root/'exports';folder.mkdir(exist_ok=True);handle=tempfile.NamedTemporaryFile(suffix='.zip',dir=folder,delete=False);path=Path(handle.name);handle.close();manifest=[]
  try:
   with zipfile.ZipFile(path,'w',zipfile.ZIP_STORED) as z:
    for item in export_selection(paper_id):
     d=store.document(item['document_id']) if item['document_id'] else None
     license=(d or {}).get('license') or '';permitted=any(v in license.casefold() for v in ['creativecommons.org','cc-by','cc0','public domain'])
     if not d or d['kind']!='pdf' or not permitted:
      manifest.append({'paper_id':item['paper']['paper_id'],'included':False,'reason':'FULLTEXT_UNAVAILABLE_OR_REUSE_LICENSE_NOT_RECORDED'});continue
     if digest(d['path'])!=d['sha256']:raise PlatformError('DOCUMENT_FILE_CHANGED')
     name=d['sha256']+'.pdf'
     if name not in z.namelist():z.write(d['path'],name)
     manifest.append({'paper_id':item['paper']['paper_id'],'file':name,'license':license,'source_url':d['source_url'],'sha256':d['sha256'],'bytes':d['file_size'],'included':True})
    z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2));z.writestr('README.txt','Original PDFs. Follow each recorded license. Open access does not grant unrestricted reuse. Exclusions are listed in manifest.json.')
   return FileResponse(path,filename='papers.zip',media_type='application/zip',background=BackgroundTask(path.unlink,missing_ok=True))
  except BaseException:path.unlink(missing_ok=True);raise
 @app.post('/api/v1/compare/export')
 def export_comparison(format:Literal['jsonl','csv','xlsx']='csv',body:Selection=Depends(input_for(Selection))):
  data,mime=encode_export(compare(selected_records(body.paper_ids)),format);return Response(data,media_type=mime,headers={'Content-Disposition':'attachment; filename="comparison.'+format+'"'})
 assets=Path(__file__).with_name('web');app.mount('/',StaticFiles(directory=assets,html=True),name='workspace')
 return app
