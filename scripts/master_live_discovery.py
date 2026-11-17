from pathlib import Path
import asyncio,json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from science_platform.discovery import *
from science_platform.store import Store
async def main():
 report={};allpapers=[];query=SearchQuery(query='formal verification constraint solving',year_from=2020,target=20)
 async def one(name):
  key=os.getenv({'openalex':'OPENALEX_API_KEY','semantic_scholar':'SEMANTIC_SCHOLAR_API_KEY','springer':'SPRINGER_API_KEY','elsevier':'ELSEVIER_API_KEY'}.get(name,'_UNUSED_'))
  provider=PROVIDERS[name](ProviderHTTP(interval=1,retries=1),api_key=key)
  try:
   if name in {'springer','elsevier'} and not key:return name,{'status':'NOT EXECUTED','reason':'MISSING_AUTHORIZED_API_KEY'},[]
   page=await asyncio.wait_for(provider.search(query),timeout=60)
   return name,{'status':'EXECUTED','found':len(page.papers),'total_reported':page.total},list(page.papers)
  except PlatformError as e:return name,{'status':'FAILED_EXTERNAL','error':e.safe()},[]
  except (asyncio.TimeoutError,ValueError,KeyError,TypeError) as e:return name,{'status':'FAILED_EXTERNAL','error':type(e).__name__},[]
  finally:await provider.aclose()
 for name,result,rows in await asyncio.gather(*(one(n) for n in ['crossref','openalex','semantic_scholar','springer','elsevier'])):
  report[name]=result;allpapers+=rows;print(name,json.dumps(result),flush=True)
 merged=deduplicate(allpapers);store=Store(Path('work/master-platform/state.sqlite3'))
 for p in merged:store.upsert_paper(p)
 Path('docs/master/LIVE_DISCOVERY.json').write_text(json.dumps({'query':query.model_dump(mode='json'),'providers':report,'raw_count':len(allpapers),'deduplicated':len(merged),'papers':[p.model_dump(mode='json') for p in merged]},ensure_ascii=False,indent=2)+'\n')
 print('REAL METADATA:',len(allpapers),'raw;',len(merged),'deduplicated')
 if len(merged)<20:raise SystemExit(1)
asyncio.run(main())
