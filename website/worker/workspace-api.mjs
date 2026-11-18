import {api} from './api.mjs';
const workspaceReply = (value, status=200) => Response.json(value, {status, headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});

function crossrefPaper(x) {
 const parts=x.published?.['date-parts']?.[0]||x.issued?.['date-parts']?.[0]||[];
 return {id:'doi:'+x.DOI,doi:x.DOI,title:String(x.title?.[0]||'Untitled').replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim(),authors:(x.author||[]).map(a=>[a.given,a.family].filter(Boolean).join(' ')),
  year:parts[0]||null,source:'crossref',url:'https://doi.org/'+x.DOI,abstract:String(x.abstract||'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim(),
  venue:x['container-title']?.[0]||'',fulltext_status:'METADATA_ONLY',pdf_url:null};
}

export async function workspaceApi(request, env, corpus, index) {
 const url=new URL(request.url),path=url.pathname;
 if(path==='/api/health')return workspaceReply({status:'ok',product:'PaperLens',version:'0.3.1-hosted',storage:!!env.BUCKET,
  parser:'PDF.js in browser',record_format:'research-1',llm:'NOT_CONFIGURED',scientific_accuracy:'NOT_INDEPENDENTLY_EVALUATED',seed_count:index.records.length});
 if(path==='/api/discovery') {
  if(request.method!=='GET')return workspaceReply({error:'GET required'},405);
  const query=(url.searchParams.get('q')||'').trim(),provider=url.searchParams.get('provider')||'arxiv';
  if(!query||query.length>500||!['arxiv','crossref'].includes(provider))return workspaceReply({error:'请输入有效的检索词或文献标识。'},400);
  try {
   const doi=query.replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'');
   if(provider==='crossref'||/^10\.\d{4,9}\//.test(doi)) {
    const single=/^10\.\d{4,9}\//.test(doi);
    const target=single?'https://api.crossref.org/works/'+encodeURIComponent(doi):'https://api.crossref.org/works?'+new URLSearchParams({query,rows:'20'});
    const response=await fetch(target,{headers:{'User-Agent':'PaperLens/0.3.1 (scientific literature discovery)'},signal:AbortSignal.timeout(45000)});
    if(!response.ok)return workspaceReply({error:response.status===429?'Crossref 请求较多，请稍后重试。':'Crossref 暂时无法响应，请重试或切换 arXiv。',source_status:response.status},502);
    const value=await response.json(),items=(single?[value.message]:value.message.items).map(crossrefPaper);
    return workspaceReply({items,total:single?items.length:value.message['total-results'],provider:'crossref',scope:'REAL_UPSTREAM_METADATA'});
   }
   const id=query.replace(/^arxiv\s*:\s*/i,'').replace(/^https?:\/\/arxiv\.org\/(?:abs|pdf)\//,'').replace(/\.pdf$/,'');
   const known=corpus.papers.find(p=>p.id===id||p.id.replace(/v\d+$/,'')===id);
   if(known)return workspaceReply({items:[known],total:1,provider:'arxiv',scope:'PINNED_REAL_CORPUS_ID_LOOKUP'});
   const upstream=new URL('/api/search',url);upstream.searchParams.set('q',id);upstream.searchParams.set('limit','20');upstream.searchParams.set('sort','relevance');
   const result=await api(new Request(upstream),env,corpus);
   if(!result.ok)return workspaceReply({error:'arXiv 暂时无法响应，请重试、切换 Crossref，或导入已有授权 PDF。'},502);
   const data=await result.json();return workspaceReply({...data,provider:'arxiv',scope:'REAL_UPSTREAM_METADATA'});
  }catch{return workspaceReply({error:'检索服务连接失败。已有文献和导出仍可使用，请稍后重试。'},502);}
 }
 if(path==='/api/research/download') {
  if(request.method!=='GET')return workspaceReply({error:'GET required'},405);
  const name=url.searchParams.get('name'),known=index.artifacts?.[name];
  if(!known||!env.BUCKET)return workspaceReply({error:'文件不存在。'},404);
  const object=await env.BUCKET.get('research/artifact_versions/'+known.sha256+'/'+name)||await env.BUCKET.get('research/artifacts/'+name);
  if(!object)return workspaceReply({error:'示例文件尚未准备好，请稍后重试。'},503);
  const mime=name.endsWith('.pdf')?'application/pdf':name.endsWith('.xlsx')?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':name.endsWith('.csv')?'text/csv;charset=utf-8':name.endsWith('.html')?'text/html;charset=utf-8':'application/x-ndjson;charset=utf-8';
  return new Response(object.body,{headers:{'Content-Type':mime,'Content-Disposition':'attachment; filename="PaperLens-'+name+'"','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
 }
 return null;
}
