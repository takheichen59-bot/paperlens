import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..'),site=process.argv[2]||path.join(root,'website');
const load=async file=>import('data:text/javascript;base64,'+(await readFile(file)).toString('base64'));
const {extractPreview,formula}=await load(path.join(root,'src/paper_platform/web_assets/preview.js'));
const policy=JSON.parse(await readFile(path.join(root,'src/paper_platform/web_assets/policy.json')));
const meta={id:'2401.00001',title:'Synthetic browser fixture',url:'https://arxiv.org/abs/2401.00001'};
const blocks=lines=>lines.map((text,i)=>({text,block_id:'b'+i,page:1}));
let passed=0;
async function test(name,fn){await fn();passed++;console.log('PASS '+name);}
await test('browser_complete_and_raw_evidence',()=>{const b=blocks(['Methods','TiO2 was prepared and heated at 180 C.','Conclusions','The coating improved corrosion resistance.']);const r=extractPreview(b,meta,policy);assert.equal(r.status,'success');for(const s of r.source_snippets){assert.equal(s.text,b.find(x=>x.block_id===s.block_id).text);assert.equal(s.end_offset,Array.from(s.text).length);}assert.deepEqual(Object.keys(r).sort(),['doi','title','source_url','chemicals','conclusions','methods','extraction_method','source_snippets','status'].sort());});
await test('browser_crystal_noise',()=>{for(const s of ['HK0','HK1','HH','HPCC','H0'])assert.equal(formula(s,policy,'precession planes'),false);for(const s of ['TiO2','MoS2','NaCl'])assert.equal(formula(s,policy),true);});
await test('browser_unicode_offsets',()=>{const r=extractPreview(blocks(['Methods','Graphene was prepared at 180 C. Symbol: 𝛼.','Conclusions','The coating improved resistance.']),meta,policy);assert.ok(r.source_snippets.some(s=>s.text.includes('𝛼')));for(const s of r.source_snippets)assert.equal(s.end_offset,Array.from(s.text).length);});
await test('browser_references_excluded',()=>{const r=extractPreview(blocks(['Methods','Samples were prepared at 180 C.','References','Graphene and TiO2 were discussed in prior work.']),meta,policy);assert.deepEqual(r.chemicals,[]);assert.equal(r.status,'partial');});
await test('browser_missing_fields',()=>{const r=extractPreview(blocks(['An ordinary document has no technical evidence.']),meta,policy);assert.equal(r.status,'failed');assert.equal(r.methods,'');assert.equal(r.conclusions,'');assert.deepEqual(r.source_snippets,[]);});
const {api}=await load(path.join(site,'worker/api.mjs'));
const originalFetch=globalThis.fetch,originalNow=Date.now;let clock=originalNow();Date.now=()=>clock+=4000;
try{
 await test('worker_status',async()=>{const r=await api(new Request('https://test/api/status'));assert.equal((await r.json()).engine,'browser-preview');});
 await test('worker_invalid_id',async()=>{assert.equal((await api(new Request('https://test/api/pdf?id=https://evil.test'))).status,400);});
 await test('worker_arxiv_metadata',async()=>{globalThis.fetch=async url=>{assert.ok(String(url).startsWith('https://export.arxiv.org/'));return new Response('<feed><entry><id>http://arxiv.org/abs/2401.00001v1</id><title>Synthetic title</title><summary>Fixture only</summary><published>2024-01-01</published><author><name>A. Researcher</name></author></entry></feed>');};const r=await api(new Request('https://test/api/search?q=materials'));assert.equal(r.status,200);const d=await r.json();assert.equal(d.items[0].id,'2401.00001v1');assert.equal(d.items[0].doi,null);});
 await test('worker_size_limit',async()=>{globalThis.fetch=async()=>new Response('fixture',{headers:{'content-length':'200000000','content-type':'application/pdf'}});const r=await api(new Request('https://test/api/pdf?id=2401.00001'));assert.equal(r.status,413);assert.equal((await r.json()).skipped_reason,'size_limit');});
 await test('worker_source_failure',async()=>{globalThis.fetch=async()=>new Response('temporary unavailable',{status:503});const r=await api(new Request('https://test/api/search?q=materials'));assert.equal(r.status,502);assert.ok((await r.json()).error);});
}finally{globalThis.fetch=originalFetch;Date.now=originalNow;}
console.log('WEB ASSET SUMMARY: '+passed+' passed, 0 failed (logic/API, not browser interaction)');
