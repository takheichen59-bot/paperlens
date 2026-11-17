export const ARXIV_ID=/^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?\/\d{7})(?:v\d+)?$/;
export const baseID=id=>String(id).replace(/v\d+$/,'');
const version=id=>Number(String(id).match(/v(\d+)$/)?.[1]||0);
export function parseIDs(value){const map=new Map(),invalid=[];for(const raw of value.split(/[\s,;，；]+/).filter(Boolean)){const id=raw.replace(/^https?:\/\/(?:www\.)?arxiv\.org\/(?:abs|pdf)\//i,'').replace(/\.pdf$/i,'').replace(/[?#].*$/,'');if(!ARXIV_ID.test(id)){invalid.push(raw);continue;}const old=map.get(baseID(id));if(!old||version(id)>version(old))map.set(baseID(id),id);}return {ids:[...map.values()],invalid};}
export function deduplicate(items){const result=[],ids=new Set(),dois=new Set();for(const item of items){const id=baseID(item.id),doi=(item.doi||'').toLowerCase();if(ids.has(id)||(doi&&dois.has(doi)))continue;ids.add(id);if(doi)dois.add(doi);result.push(item);}return result;}
export function createJob(meta){return {id:meta.id,meta:{...meta},state:'queued',progress:'等待获取',error:null,inspection:null,downloaded:false};}
const abort=signal=>{if(signal?.aborted)throw new DOMException('已暂停','AbortError');};
export async function fetchPDF(meta,{signal,onProgress=()=>{}}={}){
 abort(signal);onProgress('核验原文许可');const license=await fetch('/api/license?'+new URLSearchParams({id:meta.id}),{signal});const data=await license.json();if(!license.ok||!data.recognized)throw Error(data.error||'未能核验原文开放许可，请打开官方原文确认。');Object.assign(meta,{license_url:data.license_url,license_label:data.label});
 onProgress('连接官方 PDF');const response=await fetch('/api/pdf?'+new URLSearchParams({id:meta.id}),{signal});if(!response.ok){const error=await response.json().catch(()=>({}));const e=Error(error.error||'下载失败（HTTP '+response.status+'）');if(response.status===413)e.skipped=true;throw e;}
 const total=Number(response.headers.get('content-length'))||0,limit=100*1048576;if(total>limit){const e=Error('超过 100 MiB 上限');e.skipped=true;throw e;}const reader=response.body.getReader(),chunks=[];let size=0;try{for(;;){abort(signal);const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){const e=Error('超过 100 MiB 上限');e.skipped=true;throw e;}chunks.push(value);onProgress('下载中 '+(size/1048576).toFixed(1)+(total?' / '+(total/1048576).toFixed(1):'')+' MiB');}}catch(e){await reader.cancel().catch(()=>{});throw e;}return new Blob(chunks,{type:'application/pdf'});
}
export async function runJobs(jobs,{download=fetchPDF,inspect,onUpdate=()=>{},signal,maxBytes=300*1048576}={}){
 let used=jobs.reduce((n,j)=>n+(j.pdf?.size||0),0);const hashes=new Map(jobs.filter(j=>j.inspection?.sha256&&j.pdf).map(j=>[j.inspection.sha256,j.id]));
 // Serial official requests respect the source's rate limit and bound memory.
 for(const job of jobs){if(signal?.aborted)break;if(job.state==='verified'&&job.pdf)continue;try{job.error=null;if(!job.pdf){job.state='downloading';onUpdate();const pdf=await download(job.meta,{signal,onProgress:s=>{job.progress=s;onUpdate();}});if(used+pdf.size>maxBytes){const e=Error('暂存已达 300 MiB，请先保存资料包后分批下载。');e.skipped=true;throw e;}job.pdf=pdf;used+=pdf.size;job.downloaded=true;}
  job.state='checking';job.progress='检查 PDF 可读性与 SHA256';onUpdate();job.inspection=await inspect(job.pdf,job.meta,{signal});const duplicate=hashes.get(job.inspection.sha256);if(duplicate&&duplicate!==job.id){job.state='skipped';job.error='duplicate_pdf：与 '+duplicate+' 文件相同';used-=job.pdf.size;delete job.pdf;job.downloaded=false;}else{hashes.set(job.inspection.sha256,job.id);job.state='verified';job.progress='PDF 可读，已核验';job.downloaded_at=new Date().toISOString();}
 }catch(e){if(e.name==='AbortError'||signal?.aborted){job.state='paused';job.progress='已暂停，可继续';}else{job.state=e.skipped?'skipped':'failed';job.error=e.message||'处理失败';job.progress=job.error;}}onUpdate();}
 return summarize(jobs);
}
export function summarize(jobs){return {total:jobs.length,verified:jobs.filter(j=>j.state==='verified').length,failed:jobs.filter(j=>j.state==='failed').length,skipped:jobs.filter(j=>j.state==='skipped').length,paused:jobs.filter(j=>['paused','queued','needs_download'].includes(j.state)).length};}
export function serializableJobs(jobs){return jobs.map(({pdf,...job})=>({...job,state:job.state==='verified'?'needs_download':job.state,progress:job.state==='verified'?'索引已恢复，PDF 需重新获取':job.progress}));}
