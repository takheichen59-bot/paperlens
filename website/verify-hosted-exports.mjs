// File-level export regressions. Fixtures and optional real records stay local;
// none of these checks is a scientific-accuracy or browser-UI evaluation.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {scientificCSV,scientificXLSX,scientificPackage,researchJSONL,scientificEvidenceCSV,scientificMaterialRolesCSV,scientificNumericCSV,SCI_COLUMNS,sciRow} from './web_assets/research-exports.js';

const root=dirname(fileURLToPath(import.meta.url)),out=resolve(root,'work/hosted-exports');
const fixture=JSON.parse(await readFile(resolve(root,'fixtures/research-sample.json'),'utf8'));
const decoder=new TextDecoder();
let passed=0,failed=0;
await mkdir(out,{recursive:true});
async function test(name,fn){try{await fn();passed++;console.log('PASS '+name);}catch(error){failed++;console.log('FAIL '+name+': '+error.message);}}
async function unzipStored(blob){
 const bytes=new Uint8Array(await blob.arrayBuffer()),view=new DataView(bytes.buffer),files=new Map();let offset=0;
 while(offset+30<=bytes.length&&view.getUint32(offset,true)===0x04034b50){
  assert.equal(view.getUint16(offset+8,true),0,'reader expects the existing stored ZIP format');
  const size=view.getUint32(offset+18,true),nameSize=view.getUint16(offset+26,true),extraSize=view.getUint16(offset+28,true),name=decoder.decode(bytes.slice(offset+30,offset+30+nameSize)),start=offset+30+nameSize+extraSize;
  files.set(name,bytes.slice(start,start+size));offset=start+size;
 }
 assert.equal(view.getUint32(offset,true),0x02014b50,'ZIP central directory follows the local entries');
 return files;
}
function text(files,name){assert.ok(files.has(name),'missing '+name);return decoder.decode(files.get(name));}
function unescapeXML(value){return value.replace(/&(lt|gt|amp|quot|apos);/g,(_,key)=>({lt:'<',gt:'>',amp:'&',quot:'"',apos:"'"}[key]));}
function cells(xml,rowNumber){const row=xml.match(new RegExp('<row r="'+rowNumber+'"[^>]*>([\\s\\S]*?)</row>'));assert.ok(row,'row '+rowNumber);return [...row[1].matchAll(/<t xml:space="preserve">([\s\S]*?)<\/t>/g)].map(m=>unescapeXML(m[1]));}

await test('six worksheets preserve original column positions and declare valid relationships',async()=>{
 const files=await unzipStored(await scientificXLSX([fixture])),book=text(files,'xl/workbook.xml');
 assert.equal((book.match(/<sheet name=/g)||[]).length,6);
 for(const name of ['科研汇总','原始自动结果','材料角色','数值归属','证据','说明'])assert.ok(book.includes(name));
 assert.equal(cells(text(files,'xl/worksheets/sheet1.xml'),1).length,SCI_COLUMNS.length);
 assert.deepEqual(cells(text(files,'xl/worksheets/sheet1.xml'),2),sciRow(fixture).map(String));
 assert.ok(text(files,'[Content_Types].xml').includes('/xl/worksheets/sheet6.xml'));
 assert.ok(text(files,'xl/_rels/workbook.xml.rels').includes('rId7'));
});
await test('human edits are visible while exact automatic fields and review JSON remain available',async()=>{
 const r=structuredClone(fixture),original=r.findings;
 r.review={decision:'reviewed',edits:{findings:'Human revision for export fixture only.'},note:'Fixture review note',revision:'fixture-1'};
 const before=JSON.stringify(r),files=await unzipStored(await scientificXLSX([r]));
 assert.equal(cells(text(files,'xl/worksheets/sheet1.xml'),2)[3],r.review.edits.findings);
 const automatic=cells(text(files,'xl/worksheets/sheet2.xml'),2);
 assert.equal(automatic[4],original);assert.equal(JSON.parse(automatic[10]).findings,r.review.edits.findings);
 assert.equal(JSON.stringify(r),before);
});
await test('historical records explicitly mark attribution as not executed',async()=>{
 const r=structuredClone(fixture);delete r.attribution;
 const files=await unzipStored(await scientificXLSX([r]));
 assert.ok(text(files,'xl/worksheets/sheet1.xml').includes('NOT_EXECUTED_HISTORICAL_RECORD'));
 assert.ok(text(files,'xl/worksheets/sheet3.xml').includes('未执行（历史记录）'));
 assert.ok(scientificMaterialRolesCSV([r]).includes('NOT_EXECUTED_HISTORICAL_RECORD'));
});
await test('CSV formulas are escaped and every Excel cell remains an inline string',async()=>{
 const r=structuredClone(fixture);r.meta.title='   =SUM(1,2)';r.review={edits:{findings:'\t@formula'},note:'+note'};
 const csv=scientificCSV([r]);assert.ok(csv.includes("'   =SUM(1,2)"));assert.ok(csv.includes("'\t@formula"));
 const files=await unzipStored(await scientificXLSX([r]));
 for(let i=1;i<=6;i++){const sheet=text(files,'xl/worksheets/sheet'+i+'.xml');assert.ok(!sheet.includes('<f>'));assert.equal((sheet.match(/<c /g)||[]).length,(sheet.match(/t="inlineStr"/g)||[]).length);}
});
await test('long Unicode cells are visibly truncated and JSONL remains complete',async()=>{
 const r=structuredClone(fixture);r.review={edits:{findings:'😀'.repeat(33000)}};
 const files=await unzipStored(await scientificXLSX([r])),value=cells(text(files,'xl/worksheets/sheet1.xml'),2)[3];
 assert.ok(value.includes('[截断；完整内容见JSONL]'));assert.ok(value.length<32767);assert.ok(!value.includes('\uFFFD'));
 assert.equal(JSON.parse(researchJSONL([r])).review.edits.findings.length,r.review.edits.findings.length);
});
await test('workbook captures one immutable export snapshot before async ZIP work',async()=>{
 const r=structuredClone(fixture),expected=r.findings,pending=scientificXLSX([r]);
 r.findings='Changed after export began';r.review={edits:{findings:'Later human edit'}};
 const files=await unzipStored(await pending);assert.equal(cells(text(files,'xl/worksheets/sheet1.xml'),2)[3],expected);
});
await test('selected package excludes unrelated PDF jobs and preserves review overlays',async()=>{
 const r=structuredClone(fixture);r.review={decision:'reviewed',edits:{findings:'Human text'},note:'Retained note'};
 const second=structuredClone(fixture);second.id='local:without-pdf';second.paper_id=second.id;delete second.meta.id;
 const files=await unzipStored(await scientificPackage([r,second],[{id:r.id,meta:{paper_id:r.paper_id},pdf:new Blob(['selected actual-byte fixture'])},{id:'unselected-paper',meta:{paper_id:'other'},pdf:new Blob(['excluded bytes']),error:'excluded error',state:'failed'}]));
 assert.ok(files.has('PDF/'+r.id.replace(/[^\w.-]/g,'_')+'.pdf'));
 assert.ok(!files.has('PDF/unselected-paper.pdf'));assert.equal(text(files,'failures.jsonl'),'');
 assert.equal(JSON.parse(text(files,'reviews.jsonl')).review.note,'Retained note');
 for(const name of ['material_roles.csv','numeric_attribution.csv','evidence.csv','LICENSE-MANIFEST.json'])assert.ok(files.has(name));
 const manifest=JSON.parse(text(files,'LICENSE-MANIFEST.json'));assert.equal(manifest[0].pdf_included,true);assert.equal(manifest[1].pdf_included,false);
 assert.ok(!text(files,'README.txt').includes('固定20篇'));
});

const flag=process.argv.indexOf('--records');
if(flag>=0){
 const recordPath=resolve(process.argv[flag+1]),records=(await readFile(recordPath,'utf8')).split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
 await test('actual supplied research records export matching core fields and exact source locations',async()=>{
  assert.ok(records.length>0);const workbook=await scientificXLSX(records),files=await unzipStored(workbook),summary=text(files,'xl/worksheets/sheet1.xml');
  for(let i=0;i<records.length;i++){
   const row=cells(summary,i+2),r=records[i],expected=sciRow(r).map(String);assert.deepEqual(row,expected);
   assert.equal(row[2],r.review?.edits?.methods??r.methods);assert.equal(row[3],r.review?.edits?.findings??r.findings);assert.equal(row[4],r.review?.edits?.conclusions??r.conclusions);
   const evidence=text(files,'xl/worksheets/sheet5.xml');for(const s of r.source_snippets){assert.ok(evidence.includes(s.block_id));assert.ok(evidence.includes(s.evidence_id));}
  }
  const example=records.find(r=>r.id==='2501.00680v1');
  if(example){assert.ok(summary.includes('BiFeO3'));assert.ok(summary.includes('MoS2; Bi4Ti3O12'));assert.ok(text(files,'xl/worksheets/sheet4.xml').includes('引用 / 背景数值'));assert.ok(text(files,'xl/worksheets/sheet4.xml').includes('97%'));}
  await writeFile(resolve(out,'actual-research.xlsx'),new Uint8Array(await workbook.arrayBuffer()));
  await writeFile(resolve(out,'actual-research.csv'),scientificCSV(records));
  await writeFile(resolve(out,'actual-research.jsonl'),researchJSONL(records));
  await writeFile(resolve(out,'actual-evidence.csv'),scientificEvidenceCSV(records));
  await writeFile(resolve(out,'actual-material-roles.csv'),scientificMaterialRolesCSV(records));
  await writeFile(resolve(out,'actual-numeric-attribution.csv'),scientificNumericCSV(records));
  await writeFile(resolve(out,'actual-research-package.zip'),new Uint8Array(await(await scientificPackage(records)).arrayBuffer()));
 });
}
await writeFile(resolve(out,'report.json'),JSON.stringify({status:failed?'FAIL':'PASS',passed,failed,scope:'FILE_STRUCTURE_FIELD_AND_SCOPE_CONSISTENCY',scientific_accuracy:'NOT_EVALUATED'},null,2)+'\n');
console.log(`HOSTED EXPORTS: ${passed} passed, ${failed} failed (file consistency; not scientific accuracy or browser UI)`);
process.exitCode=failed?1:0;
