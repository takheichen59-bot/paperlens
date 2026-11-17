import {validateResearch,researchSummary} from '../web_assets/research-shared.js';
import {makeZipStream} from './api.mjs';
const rReply=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'}});
const rKey=id=>encodeURIComponent(id);
const rRecord=id=>'research/records/'+rKey(id)+'.json';
const rSummary=id=>'research/summaries/'+rKey(id)+'.json';
const rReview=id=>'research/reviews/'+rKey(id)+'.json';
async function rRead(bucket,key){const object=await bucket.get(key);if(!object)return null;const value=JSON.parse(await object.text());if(value.storage_schema!=='research-pointer-1')return value;if(value.deleted)return null;if(!/^research\/(?:record_versions|review_versions)\//.test(value.object_key))throw Error('Invalid stored pointer');const version=await bucket.get(value.object_key);if(!version)throw Error('Missing immutable version');return JSON.parse(await version.text());}
async function rPublish(bucket,key,bytes,{expectedReviewRevision=undefined}={}){
 const prior=await bucket.get(key),parsed=prior?JSON.parse(await prior.text()):null;
 if(expectedReviewRevision!==undefined){const existing=await rRead(bucket,key);if((existing?.revision||null)!==expectedReviewRevision)return false;}
 const folder=key.startsWith('research/reviews/')?'review_versions':'record_versions';const id=key.split('/').pop();
 if(prior&&parsed.storage_schema!=='research-pointer-1')await bucket.put('research/'+folder+'/'+id+'/legacy-'+prior.etag+'.json',JSON.stringify(parsed));
 const object_key='research/'+folder+'/'+id+'/'+crypto.randomUUID()+'.json';await bucket.put(object_key,bytes,{httpMetadata:{contentType:'application/json'}});
 const pointer={storage_schema:'research-pointer-1',object_key,updated_at:new Date().toISOString()};
 const published=await bucket.put(key,JSON.stringify(pointer),{onlyIf:prior?{etagMatches:prior.etag}:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/json'}});
 return !!published;
}
async function rHash(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
async function rBody(request,max=3000000){if(Number(request.headers.get('content-length'))>max)throw Error('Request too large');const reader=request.body?.getReader();if(!reader)throw Error('Body required');let size=0,text='';const decoder=new TextDecoder('utf-8',{fatal:true});try{for(;;){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>max){await reader.cancel();throw Error('Request too large');}text+=decoder.decode(value,{stream:true});}text+=decoder.decode();return {text,value:JSON.parse(text)};}finally{reader.releaseLock();}}

export async function researchApi(request,env={},index={records:[],artifacts:{}}){
 const url=new URL(request.url),bucket=env.BUCKET,path=url.pathname,id=url.searchParams.get('id')||url.searchParams.get('paper_id')||'';
 if(!bucket)return rReply({error:'Research storage unavailable'},503);
 try{
  if(path==='/api/research/index'&&request.method==='GET'){
   const listed=await bucket.list({prefix:'research/records/',limit:20,...(url.searchParams.get('cursor')?{cursor:url.searchParams.get('cursor')}:{})});
   const rows=await Promise.all(listed.objects.map(o=>rRead(bucket,o.key)));const storedIds=new Set(listed.objects.map(o=>decodeURIComponent(o.key.split('/').pop().replace(/\.json$/,''))));const merged=new Map();for(const r of [...(!url.searchParams.get('cursor')?index.records.filter(r=>!storedIds.has(r.id)):[]),...rows.filter(Boolean).map(researchSummary)])merged.set(r.paper_id,r);
   const records=[...merged.values()];for(const r of records){const review=await rRead(bucket,rReview(r.paper_id));r.review=review?(review.pdf_hash===r.pdf_hash?review:{...review,edits:{},decision:'needs_review',stale:true,note:'PDF 版本已变更；旧修订未应用，请重新复核。'}):null;}return rReply({records,cursor:listed.truncated?listed.cursor:null,seed_count:index.records.length});
  }
  if(path==='/api/research/record'&&request.method==='GET'){
   if(!id||id.length>160)return rReply({error:'Invalid paper ID'},400);const record=await rRead(bucket,rRecord(id));return record?rReply(record):rReply({error:'Scientific record not found'},404);
  }
  if(path==='/api/research/record'&&request.method==='DELETE'){
   if(index.records.some(r=>r.id===id))return rReply({error:'Curated corpus deletion is protected'},409);
   const prior=await bucket.get(rRecord(id));if(!prior)return rReply({error:'Unknown record'},404);const previous=JSON.parse(await prior.text());if(previous.storage_schema!=='research-pointer-1')await bucket.put('research/record_versions/'+rKey(id)+'.json/legacy-'+prior.etag+'.json',JSON.stringify(previous));
   const ok=await bucket.put(rRecord(id),JSON.stringify({storage_schema:'research-pointer-1',deleted:true,updated_at:new Date().toISOString()}),{onlyIf:{etagMatches:prior.etag}});return ok?rReply({status:'removed_from_current',history_preserved:true}):rReply({error:'Concurrent change'},409);
  }
  if(path==='/api/research/record'&&request.method==='PUT'){
   const {value:r}=await rBody(request);validateResearch(r);if(!/^[\w:./-]{1,160}$/.test(r.id)||!r.meta||typeof r.meta.title!=='string'||r.meta.title.length>2000||!r.paper_id||!/^[a-f0-9]{64}$/.test(r.pdf_hash))return rReply({error:'Invalid record identity'},400);
   if(!await rPublish(bucket,rRecord(r.id),JSON.stringify(r)))return rReply({error:'Record changed concurrently; reload and retry.'},409);return rReply({id:r.id,paper_id:r.paper_id,status:'stored'},201);
  }
  if(path==='/api/research/ingest'&&request.method==='PUT'){
   const known=index.records.find(r=>r.id===id),artifactName=url.searchParams.get('artifact'),artifact=index.artifacts?.[artifactName];if(!known&&!artifact)return rReply({error:'Not a registered corpus artifact'},400);
   const {text,value}=await rBody(request,artifact?12000000:3000000); // JSON artifacts use the same bounded parser.
   const bytes=new TextEncoder().encode(text),expected=known||artifact;const size=known?known.artifact_bytes:artifact.bytes,sha=known?known.artifact_sha256:artifact.sha256;
   if(bytes.length!==size||await rHash(bytes)!==sha)return rReply({error:'Artifact checksum mismatch'},400);
   if(known){validateResearch(value);if(value.id!==id)return rReply({error:'Record identity mismatch'},400);if(!await rPublish(bucket,rRecord(id),bytes))return rReply({error:'Record changed concurrently'},409);}
   else await bucket.put('research/artifacts/'+artifactName,bytes);
   return rReply({stored:true,id,artifact:artifactName||null},201);
  }
  if(path==='/api/research/artifact'&&request.method==='PUT'){
   const name=url.searchParams.get('name'),a=index.artifacts?.[name];if(!a||a.bytes>12000000)return rReply({error:'Unknown artifact'},400);const bytes=await request.arrayBuffer();if(bytes.byteLength!==a.bytes||await rHash(bytes)!==a.sha256)return rReply({error:'Artifact checksum mismatch'},400);await bucket.put('research/artifacts/'+name,bytes);return rReply({stored:true,name},201);
  }
  if(path==='/api/research/review'){
   if(!id||id.length>160)return rReply({error:'Invalid paper ID'},400);
   if(request.method==='GET')return rReply(await rRead(bucket,rReview(id)));
   if(request.method==='PUT'){
    const {value:r}=await rBody(request,20000);if(!['reviewed','needs_review'].includes(r.decision)||!r.edits||typeof r.edits!=='object'||Array.isArray(r.edits)||Object.keys(r.edits).some(f=>!['materials','methods','findings','conclusions'].includes(f))||Object.entries(r.edits).some(([f,v])=>f==='materials'?(!Array.isArray(v)||v.length>200||v.some(t=>typeof t!=='string'||t.length>500)):(typeof v!=='string'||v.length>12000))||typeof (r.note||'')!=='string'||(r.note||'').length>4000)return rReply({error:'Invalid review fields'},400);
    if(!index.records.some(p=>p.paper_id===id)){const record=await rRead(bucket,rRecord(r.record_id||''));if(!record||record.paper_id!==id)return rReply({error:'Unknown paper'},404);}
    const existing=await rRead(bucket,rReview(id));if((r.revision||null)!==(existing?.revision||null))return rReply({error:'Review changed in another session; reload before saving.'},409);const next={paper_id:id,decision:r.decision,edits:r.edits,note:r.note||'',revision:crypto.randomUUID(),updated_at:new Date().toISOString(),source:'human',pdf_hash:(index.records.find(p=>p.paper_id===id)?.pdf_hash||(await rRead(bucket,rRecord(r.record_id||'')))?.pdf_hash)};if(!await rPublish(bucket,rReview(id),JSON.stringify(next),{expectedReviewRevision:r.revision||null}))return rReply({error:'Review changed concurrently; reload and retry.'},409);return rReply(next);
   }
  }
  if(path==='/api/research/bundle'&&request.method==='GET'){
   const pdfs=index.records.map(r=>r.meta),artifacts=Object.entries(index.artifacts||{});const objects=[...pdfs.map(p=>({name:p.file,key:'phase1/'+p.sha256+'.pdf',size:p.bytes})),...artifacts.map(([name,a])=>({name:a.filename,key:'research/artifacts/'+name,size:a.bytes}))];const checks=await Promise.all(objects.map(o=>bucket.head(o.key)));if(checks.some((v,i)=>!v||v.size!==objects[i].size))return rReply({error:'Full research bundle is still being prepared.'},503);const entries=objects.map(o=>({name:o.name,size:o.size,open:async()=>{const v=await bucket.get(o.key);if(!v)throw Error('Object unavailable');return v.body;}}));return new Response(makeZipStream(entries),{headers:{'Content-Type':'application/zip','Content-Disposition':'attachment; filename="materials-research-20-full.zip"','Cache-Control':'private, no-store'}});
  }
  return rReply({error:'Method or route not supported'},405);
 }catch{return rReply({error:'Record or evidence validation failed. Original data was preserved; check input and retry.'},400);}
}
