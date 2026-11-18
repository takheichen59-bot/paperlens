// Synthetic rule/offset safety checks, plus optional compatibility with legal real records.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {scientificFromBlocks,BROWSER_SCIENTIFIC_VERSION} from './web_assets/research-core.js';
import {analyzeBlocks} from './web_assets/screening.js';
import {validateResearch} from './web_assets/research-shared.js';
import {materialRole,numericRole,sentenceRanges,validateAttribution,ATTRIBUTION_VERSION} from './web_assets/research-attribution.js';

const policy=JSON.parse(await readFile(new URL('./web_assets/research-policy.json',import.meta.url),'utf8'));
let passed=0,failed=0;
const test=async(name,fn)=>{try{await fn();passed++;console.log('PASS '+name);}catch(e){failed++;console.log('FAIL '+name+': '+e.stack);}};
function record(rows,title='BiFeO3 nanoparticles — SYNTHETIC engineering fixture'){
 const blocks=rows.map(([text,heading=false,page=1,caption=false],i)=>({text,heading,page,caption,block_id:'p'+page+'-b'+i}));
 const meta={id:'synthetic:roles',paper_id:'synthetic:roles',title,url:''};
 return {blocks,meta,record:scientificFromBlocks(blocks,meta,policy,'a'.repeat(64))};
}
function sample(){return record([
 ['BiFeO3 nanoparticles — SYNTHETIC engineering fixture',true],['Introduction',true,2],
 ['In recent work, Amdouni and collaborators [1] investigated BiFeO3 nanoparticles with 60 nm size. The results show that BiFeO3 degraded 97% of a fictional dye. The previous record was observed with MoS2 [14] and Bi4Ti3O12 [15].',false,2],
 ['Methods',true,3],['To study BiFeO3 nanoparticles, we used molecular dynamics simulations.',false,3],
 ['A temperature of 1 K was chosen for relaxation with minimal thermal noise.',false,3],
 ['Results',true,4],['😀 We observed a strength of 26.5 GPa in this synthetic test. The results show a 3.25 eV peak.',false,4],
 ['Conclusions',true,5],['In summary, we observed no reduction in error in this synthetic test.',false,5],
 ['References',true,6],['[1] MoS2 improved a fictional result to 999 K.',false,6]
 ]).record;}

await test('handoff-style attribution keeps background material and 97% external',()=>{
 const r=sample(),roles=Object.fromEntries(r.attribution.materials.map(m=>[m.name,m.role]));
 assert.equal(roles.BiFeO3,'study_subject');assert.equal(roles.MoS2,'background');assert.equal(roles.Bi4Ti3O12,'background');
 const item=r.attribution.numeric.find(n=>r.experimental_data[n.candidate_index].text.includes('97%'));
 assert.equal(item.role,'cited_result');assert.ok(item.context_evidence_ids.length);
 const context=r.source_snippets.find(s=>s.evidence_id===item.context_evidence_ids[0]);assert.ok(context.text.includes('Amdouni'));
});
await test('current comparator and procedural reagent stay distinct',()=>{
 const sentence='We study graphene and compare graphene with MoS2.';
 assert.equal(materialRole('graphene',sentence,'','methods','Graphene study')[0],'study_subject');
 assert.equal(materialRole('MoS2',sentence,'','methods','Graphene study')[0],'comparator');
 assert.equal(materialRole('ethanol','The samples were washed with ethanol.','','methods','Graphene study')[0],'reagent_or_environment');
 assert.equal(materialRole('MoS2','MoS2 occurs here.','','unknown','Unrelated title')[0],'uncertain');
});
await test('result, simulation parameter, experimental condition and mixed remain separate',()=>{
 assert.equal(numericRole('A temperature of 1 K was chosen for relaxation.','','methods')[0],'simulation_parameter');
 assert.equal(numericRole('A 532 nm laser was used.','','methods','density functional calculations')[0],'experimental_condition');
 assert.equal(numericRole('We observed 26.5 GPa.','','results')[0],'own_result');
 assert.equal(numericRole('We observe asymmetry with a laser energy excitation of 2.3 eV.','','results')[0],'uncertain');
 assert.equal(numericRole('We found 3 eV compared with 2 eV in previous work [4].','','results')[0],'uncertain');
 assert.equal(numericRole('A peak near 3 eV.','','unknown')[0],'uncertain');
});
await test('explicit return to current work resets preceding prior ownership',()=>{
 assert.equal(numericRole('The results show a 97% rate.','In previous work, others studied catalysts.','introduction')[0],'cited_result');
 assert.equal(numericRole('We observed 3 eV.','In previous work, others studied defects.','results')[0],'own_result');
 assert.equal(numericRole('The results show 3 eV.','In previous work, others studied defects. We studied our samples.','results')[0],'own_result');
});
await test('sentence boundaries keep decimals and multiple values intact',()=>{
 const text='An energy of 26.5 eV was measured. A peak at 3.25 eV was found.';
 assert.deepEqual(sentenceRanges(text).map(([a,z])=>text.slice(a,z)),['An energy of 26.5 eV was measured.','A peak at 3.25 eV was found.']);
 const r=sample(),strength=r.experimental_data.find(x=>x.text.includes('26.5'));
 assert.equal(strength.value,'26.5');assert.deepEqual(strength.values,[{value:'26.5',unit:'GPa'}]);
 const multi=record([['Methods',true],['The simulations used a cutoff of 500 eV at 300 K.']]).record;
 assert.deepEqual(multi.experimental_data[0].values,[{value:'500',unit:'eV'},{value:'300',unit:'K'}]);
});
await test('all raw slices count Unicode code points, including supplementary characters',()=>{
 const r=sample(),raw=new Map(r.raw_blocks.map(b=>[b.block_id,b]));
 for(const s of r.source_snippets){const b=raw.get(s.block_id);assert.equal(Array.from(b.text).slice(s.start_offset,s.end_offset).join(''),s.text);assert.equal(s.page_start,b.page);}
 const material=record([['Methods',true],['😀 A graphene sample was prepared and measured.']],'Graphene — SYNTHETIC').record;
 const s=material.source_snippets.find(s=>s.field==='material_roles');assert.ok(s);validateAttribution(validateResearch(material));
});
await test('reference and caption candidates never enter the role layer',()=>{
 const r=sample();assert.ok(!r.source_snippets.some(s=>s.text.includes('999 K')));
 const c=record([['Methods',true],['Graphene samples were prepared and measured.'],['Fig. 1. TiO2 was measured at 999 K.',false,1,true],['Conclusions',true],['In conclusion, graphene was tested only in a synthetic fixture.']],'Graphene — SYNTHETIC').record;
 assert.ok(!c.materials.includes('TiO2'));assert.ok(!c.source_snippets.some(s=>s.text.includes('999 K')));
});
await test('past/perfect findings and negation survive without rewriting',()=>{
 for(const text of ['We observed stable domains within the synthetic test conditions.','We have observed stable domains within the synthetic test conditions.','We showed stable domains within the synthetic test conditions.','We have shown stable domains within the synthetic test conditions.','We observed no reduction in the synthetic test error.']){
  const r=record([['Conclusions',true],[text]],'SYNTHETIC tense fixture').record;assert.equal(r.findings,text);validateResearch(r);
 }
 const r=record([['Conclusions',true],['We will observe domains in a future synthetic experiment.']],'SYNTHETIC future fixture').record;assert.equal(r.findings,'');
});
await test('original baseline fields and input blocks remain unchanged',()=>{
 const rows=[['Methods',true],['Graphene was prepared with density functional theory at 300 K.'],['Results',true],['We observed stable domains within the synthetic test conditions.'],['Conclusions',true],['In conclusion, graphene is stable within this synthetic test.']];
 const {record:r,blocks,meta}=record(rows,'Graphene — SYNTHETIC');const before=JSON.stringify(blocks),base=analyzeBlocks(blocks,meta,policy).record;
 assert.deepEqual(r.materials,base.chemicals);assert.equal(r.methods,base.methods);assert.equal(r.conclusions,base.conclusions);assert.deepEqual(r.legacy_record,base);assert.equal(JSON.stringify(blocks),before);
 assert.equal(r.attribution.review_status,'unreviewed');assert.equal(r.review_status,'unreviewed');assert.equal(r.attribution.version,ATTRIBUTION_VERSION);assert.equal(r.extractor_version,BROWSER_SCIENTIFIC_VERSION);
});
await test('numeric-index, role, material and context evidence tampering are rejected',()=>{
 const r=sample();
 for(const mutate of [x=>x.attribution.numeric[0].candidate_index=99,x=>x.attribution.numeric[0].role='certified_result',x=>x.attribution.materials[0].mentions[0].evidence_ids=['missing'],x=>x.attribution.numeric[0].context_evidence_ids=['missing']]){
  const bad=structuredClone(r);mutate(bad);assert.throws(()=>validateAttribution(bad));
 }
 const historical=structuredClone(r);delete historical.attribution;assert.equal(validateAttribution(historical),historical);
});

const position=process.argv.indexOf('--real-jsonl');
if(position>=0)await test('five real Python records remain schema-compatible without reclassifying them',async()=>{
 const rows=(await readFile(process.argv[position+1],'utf8')).trim().split('\n').map(line=>JSON.parse(line));assert.equal(rows.length,5);
 for(const row of rows){const before=JSON.stringify(row);validateAttribution(validateResearch(row));assert.equal(JSON.stringify(row),before);assert.ok(['context-roles-v1','context-roles-v1.1'].includes(row.attribution.version));}
 console.log('REAL RECORD COMPATIBILITY: 5 actual records; source-span validation only, browser extraction not asserted.');
});
console.log(`HOSTED ATTRIBUTION: ${passed} passed, ${failed} failed; rule candidates, no scientific accuracy claim`);
process.exitCode=failed?1:0;
