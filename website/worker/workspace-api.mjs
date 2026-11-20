import {api,ARXIV_ID} from './api.mjs';
import {discoverArxiv} from './discovery.mjs';
const workspaceReply = (value, status=200) => Response.json(value, {status, headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});

function crossrefPaper(x) {
 const parts=x.published?.['date-parts']?.[0]||x.issued?.['date-parts']?.[0]||[];
 return {id:'doi:'+x.DOI,doi:x.DOI,title:String(x.title?.[0]||'Untitled').replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim(),authors:(x.author||[]).map(a=>[a.given,a.family].filter(Boolean).join(' ')),
  year:parts[0]||null,source:'crossref',url:'https://doi.org/'+x.DOI,abstract:String(x.abstract||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim(),
  venue:x['container-title']?.[0]||'',fulltext_status:'METADATA_ONLY',pdf_url:null};
}

export function openAlexArxivPaper(x){const locations=(x.locations||[]).filter(l=>l.source?.id==='https://openalex.org/S4306400194');for(const l of locations){const raw=l.landing_page_url||l.pdf_url||'',m=raw.match(/(?:arxiv\.org\/(?:abs|pdf)\/|10\.48550\/arxiv\.)([^?#]+)$/i);const id=m?.[1]?.replace(/\.pdf$/,'');if(!id||!ARXIV_ID.test(id))continue;const licences={'cc-by':'https://creativecommons.org/licenses/by/','cc-by-sa':'https://creativecommons.org/licenses/by-sa/','cc0':'https://creativecommons.org/publicdomain/zero/','cc-by-nc':'https://creativecommons.org/licenses/by-nc/','cc-by-nc-sa':'https://creativecommons.org/licenses/by-nc-sa/','cc-by-nd':'https://creativecommons.org/licenses/by-nd/','cc-by-nc-nd':'https://creativecommons.org/licenses/by-nc-nd/'};return {id,source:'arxiv',metadata_source:'OpenAlex',metadata_url:x.id,title:x.title||x.display_name||id,authors:(x.authorships||[]).map(a=>a.author?.display_name).filter(Boolean),year:x.publication_year||null,doi:x.doi?.replace(/^https?:\/\/doi.org\//,''),url:'https://arxiv.org/abs/'+id,pdf_url:'https://arxiv.org/pdf/'+id,license_url:licences[l.license]||null,license_source:l.license?'OpenAlex arXiv location; license version unverified':null,license_identifier:l.license||null,source_version:'LATEST_AT_FETCH',abstract:''};}return null;}


export async function workspaceApi(request, env, corpus, index) {
 const url=new URL(request.url),path=url.pathname;
 if(path==='/api/health')return workspaceReply({status:'ok',product:'PaperLens',version:'0.6.0-oneclick',storage:!!env.BUCKET,
  parser:'PDF.js in browser',record_format:'research-1',llm:'NOT_CONFIGURED',scientific_accuracy:'NOT_INDEPENDENTLY_EVALUATED',seed_count:index.records.length});
 if(path==='/api/discovery') {
  if(request.method!=='GET')return workspaceReply({error:'GET required'},405);
  const query=(url.searchParams.get('q')||'').trim(),provider=url.searchParams.get('provider')||'arxiv';
  if(!query||query.length>500||!['arxiv','crossref'].includes(provider))return workspaceReply({error:'请输入有效的检索词或文献标识。'},400);
  const limit=Number(url.searchParams.get('limit')||20);if(!Number.isInteger(limit)||limit<1||limit>50)return workspaceReply({error:'文献数量须为 1–50。'},400);
  try {
   const doi=query.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'');
   if(provider==='crossref'||/^10\.\d{4,9}\//.test(doi)) {
    const single=/^10\.\d{4,9}\//.test(doi);
    const target=single?'https://api.crossref.org/works/'+encodeURIComponent(doi):'https://api.crossref.org/works?'+new URLSearchParams({query,rows:String(limit)});
    const response=await fetch(target,{headers:{'User-Agent':'PaperLens/0.3.1 (scientific literature discovery)'},signal:AbortSignal.timeout(45000)});
    if(!response.ok)return workspaceReply({error:response.status===429?'Crossref 请求较多，请稍后重试。':'Crossref 暂时无法响应，请重试或切换 arXiv。',source_status:response.status},502);
    const value=await response.json(),items=(single?[value.message]:value.message.items).map(crossrefPaper);
    return workspaceReply({items,total:single?items.length:value.message['total-results'],provider:'crossref',scope:'REAL_UPSTREAM_METADATA'});
   }
   const id=query.replace(/^arxiv\s*:\s*/i,'').replace(/^https?:\/\/arxiv\.org\/(?:abs|pdf)\//,'').replace(/\.pdf$/,'');
   const ids=id.split(/[\s,;，；]+/).filter(Boolean);
   if(ids.length>1&&ids.length<=20&&ids.every(v=>ARXIV_ID.test(v))){const pinned=ids.map(v=>corpus.papers.find(p=>p.id===v||p.id.replace(/v\d+$/,'')===v));if(pinned.every(Boolean))return workspaceReply({items:pinned.slice(0,limit),total:pinned.length,provider:'arxiv',scope:'PINNED_REAL_CORPUS_ID_LIST_LOOKUP'});const target=new URL('/api/identify',url);target.searchParams.set('ids',ids.join(','));const response=await api(new Request(target),env,corpus);if(!response.ok)return workspaceReply({error:'arXiv 标识批量查询失败，请稍后重试。'},502);return workspaceReply({...await response.json(),provider:'arxiv',scope:'REAL_UPSTREAM_ID_LIST'});}
   const known=corpus.papers.find(p=>p.id===id||p.id.replace(/v\d+$/,'')===id);
   if(known)return workspaceReply({items:[known],total:1,provider:'arxiv',scope:'PINNED_REAL_CORPUS_ID_LOOKUP'});
   const data=await discoverArxiv(request,id,limit,corpus,env,openAlexArxivPaper);return workspaceReply(data,data.error?503:200);
  }catch{return workspaceReply({error:'检索服务连接失败。已有文献和导出仍可使用，请稍后重试。'},502);}
 }
 if(path==='/api/research/download') {
  if(request.method!=='GET')return workspaceReply({error:'GET required'},405);
  const name=url.searchParams.get('name'),known=index.artifacts?.[name];
  if(!known||!env.BUCKET)return workspaceReply({error:'文件不存在。'},404);
  let object=await env.BUCKET.get('research/artifact_versions/'+known.sha256+'/'+name);
  if(!object){const legacy=await env.BUCKET.get('research/artifacts/'+name);if(legacy){const bytes=await legacy.arrayBuffer(),sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(bytes.byteLength===known.bytes&&sha===known.sha256)object={body:bytes};}}
  if(!object)return workspaceReply({error:'示例文件尚未准备好，请稍后重试。'},503);
  const mime=name.endsWith('.pdf')?'application/pdf':name.endsWith('.xlsx')?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':name.endsWith('.csv')?'text/csv;charset=utf-8':name.endsWith('.html')?'text/html;charset=utf-8':'application/x-ndjson;charset=utf-8';
  return new Response(object.body,{headers:{'Content-Type':mime,'Content-Disposition':'attachment; filename="PaperLens-'+name+'"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
 }
 return null;
}
