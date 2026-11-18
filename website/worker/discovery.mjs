// Resilient public metadata discovery. No fixed-paper substitution or model service.
import {api,ARXIV_ID} from './api.mjs';
const D_CACHE_SCHEMA='paperlens-discovery-cache-1',D_FRESH_MS=15*60*1000,D_STALE_MS=7*24*60*60*1000;
const dPending=new Map();
const dText=x=>String(x||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const dRetryStatus=n=>[408,429,500,502,503,504].includes(n);
const dSleep=(ms,signal)=>new Promise((resolve,reject)=>{if(signal?.aborted){reject(signal.reason);return;}const timer=setTimeout(done,ms);function done(){signal?.removeEventListener('abort',cancel);resolve();}function cancel(){clearTimeout(timer);reject(signal.reason);}signal?.addEventListener('abort',cancel,{once:true});});
const dAfter=value=>{const n=Number(value);return value===null?null:Number.isFinite(n)?Math.max(0,n):Math.max(0,Math.ceil((Date.parse(value)-Date.now())/1000))||null;};
const dAttempt=(provider,status,code,extra={})=>({provider,status,code,...extra});
async function dJSON(provider,url,{attempts=2,timeout=6500,signal}={}){
 const history=[];
 for(let n=0;n<attempts;n++){
  if(signal?.aborted)throw signal.reason;
  try{
   const deadline=AbortSignal.timeout(timeout),response=await fetch(url,{headers:{'User-Agent':'PaperLens/0.4.1 (public literature discovery)','Accept':'application/vnd.api+json, application/json'},signal:signal?AbortSignal.any([signal,deadline]):deadline});
   const retry_after_seconds=dAfter(response.headers.get('Retry-After'));
   if(!response.ok){const code=response.status===429?'RATE_LIMITED':response.status===503?'TEMPORARILY_UNAVAILABLE':'HTTP_ERROR';history.push(dAttempt(provider,response.status,code,{retry_after_seconds}));await response.body?.cancel();if(n+1<attempts&&dRetryStatus(response.status)&&(retry_after_seconds===null||retry_after_seconds<=2)){await dSleep(Math.max(1000,(retry_after_seconds||0)*1000),signal);continue;}return {history};}
   const value=await response.json();history.push(dAttempt(provider,200,'OK'));return {value,history};
  }catch(error){if(signal?.aborted)throw error;history.push(dAttempt(provider,null,error.name==='TimeoutError'||error.name==='AbortError'?'TIMEOUT':error instanceof SyntaxError?'INVALID_RESPONSE':'NETWORK_ERROR'));if(n+1===attempts)return {history};await dSleep(1000,signal);}
 }
 return {history};
}
export function dataciteArxivPaper(row){
 const a=row?.attributes||{},doi=String(a.doi||row?.id||''),client=row?.relationships?.client?.data?.id,id=doi.match(/^10\.48550\/arxiv\.(.+)$/i)?.[1];
 if(client!=='arxiv.content'||!id)return null;
 const sourceUrl=String(a.url||'');if(!/^https?:\/\/arxiv\.org\/abs\//i.test(sourceUrl))return null;
 const sourceId=sourceUrl.replace(/^https?:\/\/arxiv\.org\/abs\//i,'').replace(/\.pdf$/,'');if(!ARXIV_ID.test(sourceId)||sourceId.replace(/v\d+$/,'').toLowerCase()!==id.replace(/v\d+$/,'').toLowerCase())return null;
 const license=(a.rightsList||[]).map(x=>String(x.rightsUri||'').replace(/^http:/,'https:')).find(x=>/^https:\/\/(?:creativecommons\.org\/(?:licenses|publicdomain)\/|arxiv\.org\/licenses\/)/.test(x));
 const title=dText(a.titles?.[0]?.title);if(!title)return null;
 return {id:sourceId,source:'arxiv',source_id:sourceId.replace(/v\d+$/,''),metadata_source:'DataCite',metadata_url:'https://doi.org/'+doi,title,doi,authors:(a.creators||[]).map(x=>dText(x.name||[x.givenName,x.familyName].filter(Boolean).join(' '))).filter(Boolean),year:a.publicationYear||null,url:'https://arxiv.org/abs/'+sourceId,pdf_url:'https://arxiv.org/pdf/'+sourceId,abstract:dText((a.descriptions||[]).find(x=>x.descriptionType==='Abstract')?.description),license_url:license||null,license_source:license?'DataCite arXiv rights metadata':null,source_version:/v\d+$/.test(sourceId)?'EXPLICIT_SOURCE_VERSION':'LATEST_AT_FETCH'};
}
function dPlain(query){return !ARXIV_ID.test(query)&&!/\b(?:cat|ti|au|abs|all):/i.test(query);}
async function dArxiv(request,query,limit,corpus,env,history){
 const target=new URL('/api/search',request.url);target.searchParams.set('q',query);target.searchParams.set('limit',String(limit));target.searchParams.set('sort','relevance');
 const response=await api(new Request(target,{signal:request.signal}),env,corpus,{searchTimeoutMs:8000});const value=await response.json();history.push(dAttempt('arxiv',value.source_status||response.status,response.ok?'OK':value.code||'UNAVAILABLE',{retry_after_seconds:value.retry_after_seconds??null}));
 if(response.ok)return {...value,items:value.items.slice(0,limit),provider:'arxiv',scope:'REAL_UPSTREAM_METADATA'};
 return null;
}
async function dLive(request,query,limit,corpus,env,openAlexArxivPaper){
 const history=[];let data=await dArxiv(request,query,limit,corpus,env,history);if(data)return {...data,source_attempts:history};
 // Retry a fast transient arXiv HTTP error once, observing the official 3-second pacing.
 if(request.signal.aborted)throw request.signal.reason;const first=history[0];if(dRetryStatus(first.status)&&first.code!=='UPSTREAM_TIMEOUT'&&(first.retry_after_seconds===null||first.retry_after_seconds<=3)){data=await dArxiv(request,query,limit,corpus,env,history);if(data)return {...data,source_attempts:history};}
 if(dPlain(query)){
  const target='https://api.datacite.org/dois?'+new URLSearchParams({query,'client-id':'arxiv.content','page[size]':String(limit),sort:'relevance'}),r=await dJSON('datacite',target,{signal:request.signal});history.push(...r.history);
  if(r.value&&Array.isArray(r.value.data)){const items=[...new Map(r.value.data.map(dataciteArxivPaper).filter(Boolean).map(p=>[p.id,p])).values()];if(items.length||r.value.meta?.total===0)return {items,total:r.value.meta?.total??items.length,provider:'datacite',scope:'REAL_DATACITE_ARXIV_REGISTRY',upstream_notice:'arXiv 查询暂不可用；本次使用 DataCite 登记的真实 arXiv 元数据，全文仍从 arXiv 获取。',source_attempts:history};history.push(dAttempt('datacite',200,'NO_VALID_ARXIV_RECORDS'));}
  const alternative='https://api.openalex.org/works?'+new URLSearchParams({search:query,filter:'locations.source.id:S4306400194','per-page':String(limit),sort:'relevance_score:desc'}),a=await dJSON('openalex',alternative,{attempts:1,timeout:5500,signal:request.signal});history.push(...a.history);
  if(a.value&&Array.isArray(a.value.results)){const items=[...new Map(a.value.results.map(openAlexArxivPaper).filter(Boolean).map(p=>[p.id,p])).values()];if(items.length||a.value.meta?.count===0)return {items,total:a.value.meta?.count??items.length,provider:'openalex',scope:'REAL_OPENALEX_ARXIV_LOCATIONS',upstream_notice:'arXiv 查询暂不可用；本次使用 OpenAlex 的真实聚合元数据，仅保留具有 arXiv 原文位置的论文。',source_attempts:history};}
 }
 const labels={arxiv:'arXiv',datacite:'DataCite',openalex:'OpenAlex'},last=[...new Map(history.map(x=>[x.provider,x])).values()],why=x=>/TIMEOUT/.test(x.code)?'超时':/RATE_LIMITED/.test(x.code)?'请求限流':x.status===503?'暂不可用':x.code==='INVALID_RESPONSE'?'响应格式异常':'连接失败';return {error:'检索暂未完成（'+last.map(x=>labels[x.provider]+'：'+why(x)).join('；')+'）。已有文献仍可导出，请重试。',code:'DISCOVERY_UNAVAILABLE',retryable:true,source_attempts:history};
}
async function dKey(query,limit){const bytes=new TextEncoder().encode(JSON.stringify({provider:'arxiv',query,limit})),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');return 'discovery/v1/'+hash+'.json';}
export async function discoverArxiv(request,query,limit,corpus,env,openAlexArxivPaper){
 if(request.signal.aborted)throw request.signal.reason;const key=await dKey(query,limit);let cached=null;try{const obj=await env.BUCKET?.get(key);if(obj){const v=JSON.parse(await obj.text());if(v.schema_version===D_CACHE_SCHEMA&&v.query===query&&v.limit===limit&&Array.isArray(v.data?.items)&&v.data.items.every(p=>p.source==='arxiv'&&ARXIV_ID.test(p.id))&&Number.isFinite(Date.parse(v.fetched_at)))cached=v;}}catch{}
 const age=cached?Date.now()-Date.parse(cached.fetched_at):Infinity,cacheResult=state=>({...cached.data,cache:{state,fetched_at:cached.fetched_at,age_seconds:Math.max(0,Math.floor(age/1000))}});
 if(cached&&age>=0&&age<D_FRESH_MS&&!new URL(request.url).searchParams.has('refresh'))return cacheResult('fresh');
 let task=dPending.get(key);if(!task){task=dLive(request,query,limit,corpus,env,openAlexArxivPaper);dPending.set(key,task);}
 let data;try{data=await task;}catch(error){if(request.signal.aborted)throw error;data={error:'检索连接超时或中断，请重试。已保存的文献仍可使用。',code:'DISCOVERY_UNAVAILABLE',retryable:true,source_attempts:[]};}finally{if(dPending.get(key)===task)dPending.delete(key);}
 if(!data.error){const fetched_at=new Date().toISOString();if(data.items.length){try{await env.BUCKET?.put(key,JSON.stringify({schema_version:D_CACHE_SCHEMA,query,limit,fetched_at,data}),{httpMetadata:{contentType:'application/json'}});}catch{}}return {...data,fetched_at};}
 if(cached&&age>=0&&age<D_STALE_MS)return {...cacheResult('stale'),source_attempts:data.source_attempts,upstream_notice:'实时来源暂不可用，正在显示相同检索词此前取得的真实结果；不是本次实时更新。'};
 return data;
}
