import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {PDFDocument,PDFName} from './web_assets/vendor/pdf-lib.esm.min.js';
import fontkit from './web_assets/vendor/fontkit.es.min.js';
import {readingPDF,readingReportPlan,wrapReportText} from './web_assets/reading-pdf.js';

const results=[];
async function check(name,fn){await fn();results.push({name,status:'PASS'});console.log('PASS '+name);}
function sample(id='SYNTHETIC-PDF'){
 const texts=['We used a synthetic Raman method to study the β-Ga₂O₃ sample at 4.2 K.','We measured the synthetic signal under the stated conditions.','We observed a synthetic signal in the sample.','In conclusion, we report a synthetic result for this renderer test.'];
 const evidence=texts.map((text,i)=>({id:'e'+i,text,pages:[i+1],parts:[{page:i+1,block_id:'synthetic-block-'+i,start:0,end:Array.from(text).length}]}));
 const f=ids=>({status:'candidate_extracted',evidence_ids:ids,reason:null});
 return {id,paper_id:id,meta:{title:'SYNTHETIC β-Ga₂O₃ 🄀 Unicode renderer test ˜',pdf_url:'https://example.org/SYNTHETIC.pdf',license_url:'https://example.org/SYNTHETIC-license'},methods:'HISTORICAL raw methods',findings:'HISTORICAL raw findings',conclusions:'HISTORICAL raw conclusion',review:{decision:'unreviewed',edits:{methods:'MANUAL old overlay'}},reading_card:{title:'SYNTHETIC β-Ga₂O₃ 🄀 Unicode renderer test ˜',article_type:{label:'synthetic_fixture'},origin:'browser_rule_candidates',review_status:'unreviewed',fields:{question:f(['e0']),methods:f(['e0','e1']),findings:f(['e2']),conclusions:f(['e3']),limitations:{status:'not_identified',evidence_ids:[],reason:'未定位作者明确局限；不代表没有局限。'}},objects:[{name:'β-Ga₂O₃',role:'study_subject',evidence_ids:['e0']}],method_routes:[{name:'characterization',label:'测量与表征',evidence_ids:['e0']}],procedure_steps:[{text:texts[1],evidence_ids:['e1']}],numeric_bindings:[],numeric_candidates:[{value:'97',unit:'%',evidence_ids:['e2']}],evidence,source_review:{origin:'assistant_source_review',text:'ASSISTANT overlay must stay separate',human_review_status:'unreviewed'}}};
}

await check('automatic plan preserves original/manual history and keeps assistant overlay separate',()=>{
 const r=sample(),before=JSON.stringify(r),p=readingReportPlan([r])[0];
 assert.equal(JSON.stringify(r),before);assert.equal(p.sourceReview.origin,'assistant_source_review');
 assert.ok(!JSON.stringify(p.fields).includes('ASSISTANT'));assert.ok(!JSON.stringify(p.fields).includes('HISTORICAL'));
 assert.equal(p.numbers.length,0);assert.equal(p.unbound,1);
});
await check('long or incomplete source candidates are omitted with an explicit JSONL reason',()=>{
 const r=sample();r.reading_card.evidence.push({id:'long',text:'We observed '+('a synthetic condition '.repeat(30))+'.',pages:[1],parts:[]},{id:'fragment',text:'A source fragment without an ending',pages:[1],parts:[]});
 r.reading_card.fields.findings.evidence_ids=['long','fragment'];const f=readingReportPlan([r])[0].fields.findings;
 assert.equal(f.items.length,0);assert.match(f.reason,/JSONL/);assert.match(f.reason,/未截断/);
});
await check('source-less operation claims and dangling evidence references are rejected',()=>{
 const r=sample();r.reading_card.procedure_steps[0].evidence_ids=[];assert.throws(()=>readingReportPlan([r]),/来源证据/);
 const x=sample();x.reading_card.method_routes[0].evidence_ids=['missing'];assert.throws(()=>readingReportPlan([x]),/来源证据/);
});
await check('only fully bound numeric records can enter the key-numbers section',()=>{
 const r=sample();r.reading_card.numeric_bindings=[{value:'1.8',unit:'eV',evidence_ids:['e2']},{object:'SYNTHETIC sample',quantity:'SYNTHETIC energy',value:'1.8',unit:'eV',conditions:'SYNTHETIC condition',ownership:'own_result',evidence_ids:['e2']}];
 const p=readingReportPlan([r])[0];assert.equal(p.numbers.length,1);assert.equal(p.unbound,2);
});
await check('line wrapping preserves Unicode scalar characters rather than UTF16 halves',()=>{
 const font={widthOfTextAtSize:t=>Array.from(t).length};const lines=wrapReportText('🄀🄀🄀 🄀🄀🄀',font,11,4);
 assert.equal(lines.join('').replace(/ /g,''),'🄀🄀🄀🄀🄀🄀');for(const line of lines)assert.ok(!/[\uD800-\uDBFF]$|^[\uDC00-\uDFFF]/u.test(line));
});
await check('WOFF2 parsing works but reports reject it in favor of a reliable static TTF',async()=>{
 const bytes=new Uint8Array(await readFile(new URL('./web_assets/fonts/paperlens-noto-sans-sc-ui.woff2',import.meta.url)));
 const f=fontkit.create(bytes);assert.ok(f.characterSet.includes(80));
 await assert.rejects(()=>readingPDF([],{fontBytes:bytes}),/静态 TTF/);
});

const fontPath=process.env.PAPERLENS_REPORT_FONT;
if(fontPath){
 const fontBytes=new Uint8Array(await readFile(fontPath));
 const out=resolve(process.env.PAPERLENS_REPORT_OUTPUT||'/tmp/paperlens-reading-pdf-checks');await mkdir(out,{recursive:true});
 await check('a real selectable PDF uses the default same-origin font API and preserves inputs',async()=>{
  const r=sample(),before=JSON.stringify(r),calls=[];
  const pdf=await readingPDF([r],{fetchImpl:async(url,options)=>{calls.push({url,options});return new Response(fontBytes);}});
  assert.equal(pdf.type,'application/pdf');assert.equal(JSON.stringify(r),before);assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/report-font?revision=2');assert.equal(calls[0].options.credentials,'same-origin');assert.equal(calls[0].options.body,undefined);
  const bytes=new Uint8Array(await pdf.arrayBuffer()),doc=await PDFDocument.load(bytes);assert.equal(doc.getPageCount(),3);assert.ok(doc.catalog.get(PDFName.of('Outlines')));assert.ok(doc.getPage(0).node.Annots());await writeFile(out+'/synthetic-selectable.pdf',bytes);
 });
 await check('batch overview retains failures and only completed records receive cards',async()=>{
  const r=sample('SYNTHETIC-DONE'),failed=sample('SYNTHETIC-FAILED'),pending=sample('SYNTHETIC-PENDING');
  const batch={query:'SYNTHETIC QUERY',requested_count:5,source_returned:3,items:[{id:r.id,state:'done'},{id:failed.id,state:'failed',stage:'download',error:'SYNTHETIC download failure'},{id:pending.id,state:'queued'}]};
  const before=JSON.stringify(batch),pdf=await readingPDF([r,failed,pending],{fontBytes,batch});assert.equal(JSON.stringify(batch),before);
  const bytes=new Uint8Array(await pdf.arrayBuffer()),d=await PDFDocument.load(bytes);assert.equal(d.getPageCount(),3);await writeFile(out+'/synthetic-partial-batch.pdf',bytes);
 });
 await check('missing Unicode glyphs fail explicitly instead of silently replacing characters',async()=>{
  const r=sample();r.reading_card.title='Unsupported emoji 😀';await assert.rejects(()=>readingPDF([r],{fontBytes}),/U\+1F600/);
 });
 await check('font endpoint errors report the actual status',async()=>{
  await assert.rejects(()=>readingPDF([],{fetchImpl:async()=>new Response('',{status:401})}),/HTTP 401/);
 });
 await writeFile(out+'/checks.json',JSON.stringify({scope:'renderer_only_not_scientific_accuracy',checks:results},null,2)+'\n');
}else console.log('NOT_EXECUTED PDF artifact checks: set PAPERLENS_REPORT_FONT to the pinned or CI-subset font path.');
console.log('READING PDF: '+results.length+' checks passed.');
