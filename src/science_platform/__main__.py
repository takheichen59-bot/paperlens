"""Run local web app, persistent worker or import an authorized local corpus."""
import argparse,hashlib,json,os,sys
from pathlib import Path
from . import __version__

def import_corpus(directory,corpus,limit):
 from .store import Store
 from .models import Paper,Author,SourceFact,FullTextLink,ScientificRecord
 from .jobs import parse_isolated
 from .extraction import DeepExtractor
 from .parsing import digest
 store=Store(Path(directory)/'platform.sqlite3');corpus=Path(corpus);items=json.loads((corpus/'index.json').read_text())['papers'];success=failed=0
 for x in items[:limit]:
  try:
   pid='arxiv:'+x['id'];path=(corpus/x['file']).resolve()
   if not path.is_relative_to(corpus.resolve()):raise ValueError('Invalid corpus path')
   sha=digest(path)
   if x.get('sha256') and x['sha256']!=sha:raise ValueError('Source hash mismatch')
   p=Paper(paper_id=pid,doi=x.get('doi'),title=x['title'],authors=tuple(Author(name=a if isinstance(a,str) else a['name']) for a in x.get('authors',[])),venue='arXiv',year=int(x.get('year') or str(x.get('published','2025'))[:4]),source_url=x.get('source_url') or x.get('page_url') or x.get('url') or 'https://arxiv.org/abs/'+x['id'],is_open_access=True,fulltext_links=(FullTextLink(url='https://arxiv.org/pdf/'+x['id'],kind='pdf',access='OPEN_ACCESS',license=(x.get('license') or x.get('license_url'))),),sources=(SourceFact(provider='arxiv',source_id=x['id'],retrieved_at=x.get('downloaded_at') or 'imported-existing-corpus'),))
   p=store.upsert_paper(p);did=store.save_document(p.paper_id,sha,path,'pdf',license=(x.get('license') or x.get('license_url')),source_url=p.source_url,method='AUTHORIZED_LOCAL_CORPUS_IMPORT')
   if store.latest_parse(did):print('CACHED',p.paper_id,flush=True);success+=1;continue
   parsed,external=parse_isolated(path,p.paper_id,Path(directory));store.save_parse(did,parsed);ext=DeepExtractor()
   try:record=ext.extract(parsed)
   finally:ext.client.close()
   store.save_extraction(did,record);success+=1;print('IMPORTED',p.paper_id,'segments='+str(len(parsed.segments)),'deep_ai='+record.execution_status,flush=True)
  except Exception as exc:failed+=1;print('FAILED',x.get('id'),type(exc).__name__,flush=True)
 print(json.dumps({'imported_or_cached':success,'failed':failed}));return bool(failed)

def load_environment(path):
 import re
 path=Path(path)
 if not path.is_file():return
 for raw in path.read_text().splitlines():
  line=raw.strip()
  if not line or line.startswith('#'):continue
  key,sep,value=line.partition('=');key=key.strip()
  if not sep or not re.fullmatch(r'[A-Z][A-Z0-9_]*',key):continue
  value=value.strip()
  if value[:1] in {'"',"'"} and value[-1:]==value[:1]:value=value[1:-1]
  os.environ.setdefault(key,value)

def main():
 load_environment('.env')
 p=argparse.ArgumentParser(description='Scientific Literature Intelligence & Method Mining Platform');p.add_argument('--version',action='version',version=__version__);sub=p.add_subparsers(dest='command',required=True)
 for name in ['serve','worker','import-corpus']:
  q=sub.add_parser(name);q.add_argument('--data',default=os.getenv('PAPERLENS_DATA','./data/science-platform'))
  if name=='serve':q.add_argument('--host',default='127.0.0.1');q.add_argument('--port',type=int,default=8765);q.add_argument('--external-worker',action='store_true')
  if name=='import-corpus':q.add_argument('--corpus',required=True);q.add_argument('--limit',type=int,default=20)
 a=p.parse_args()
 if a.command=='serve':
  if a.host not in {'127.0.0.1','localhost','::1'} and not os.getenv('PAPERLENS_API_TOKEN'):p.error('Non-loopback binding requires PAPERLENS_API_TOKEN and a TLS reverse proxy; configure PAPERLENS_ALLOWED_HOSTS.')
  import uvicorn
  from .api import create_app
  uvicorn.run(create_app(a.data,start_worker=not a.external_worker),host=a.host,port=a.port,access_log=False)
 elif a.command=='worker':
  from .jobs import Worker
  from .store import Store
  w=Worker(Store(Path(a.data)/'platform.sqlite3'),a.data)
  try:w.serve()
  except KeyboardInterrupt:w.stop.set()
 elif a.command=='import-corpus':raise SystemExit(import_corpus(a.data,a.corpus,a.limit))
if __name__=='__main__':main()
