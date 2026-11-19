import {chineseReadingPlan} from './reading-chinese.js';
import {READING_COLUMNS,readingRow,READING_NUMBERS,readingNumbers,READING_SOURCES,readingSources} from './reading-export.js';
import {ZipArchive} from './exports.js';
import {effectiveFields,researchGraph} from './research-shared.js';

export const MATERIAL_ROLE_LABELS={study_subject:'本文研究对象（规则候选）',background:'背景提及',comparator:'本文对照材料（规则候选）',reagent_or_environment:'试剂 / 环境',uncertain:'归属不确定'};
export const NUMERIC_ROLE_LABELS={own_result:'本文结果（规则候选）',simulation_parameter:'模拟参数',experimental_condition:'实验条件',cited_result:'引用 / 背景数值',uncertain:'归属不确定'};
const UNCLASSIFIED='NOT_EXECUTED_HISTORICAL_RECORD';
const ROLE_COLUMNS=['本文研究对象（规则候选）','背景材料','本文对照材料（规则候选）','试剂 / 环境','材料归属不确定','本文数值结果（规则候选）','模拟参数','实验条件','引用 / 背景数值','数值归属不确定','归属规则版本','归属复核状态'];
// Keep the original fifteen columns in order; append explicit role/provenance columns.
export const SCI_COLUMNS=['论文标题','材料候选（含背景）','研究方法','主要发现','结论','算法 / 计算方法','公式候选（PDF原文）','数值 / 实验数据候选（PDF原文）','作者局限性候选','arXiv / 本地 ID','DOI','原文链接','证据条数','原字段复核状态','人工备注',...ROLE_COLUMNS,'论文ID','原PDF SHA256','解析器版本','提取器版本'];

function snapshot(records){return typeof structuredClone==='function'?structuredClone(records):JSON.parse(JSON.stringify(records));}
function attributionVersion(r){return r.attribution?.version||UNCLASSIFIED;}
function roleLabel(labels,role){return labels[role]||'待核实：'+String(role||'未分类');}
function numericCandidate(r,item){
 const candidate=r.experimental_data[item.candidate_index];
 if(!candidate)throw Error('数值归属无法对应原始候选，请检查记录后重试。');
 return candidate;
}
function roleCells(r){
 const layer=r.attribution;
 if(!layer)return [...Array(10).fill(''),UNCLASSIFIED,'未执行（历史记录）'];
 const cells=['study_subject','background','comparator','reagent_or_environment','uncertain'].map(role=>(layer.materials||[]).filter(m=>m.role===role).map(m=>m.name).join('; '));
 for(const role of ['own_result','simulation_parameter','experimental_condition','cited_result','uncertain'])cells.push((layer.numeric||[]).filter(n=>n.role===role).map(n=>numericCandidate(r,n).text).join('\n\n'));
 return [...cells,attributionVersion(r),layer.review_status==='unreviewed'?'待人工复核':String(layer.review_status||'待人工复核')];
}
export function sciRow(r){
 const f=effectiveFields(r,r.review);
 return [r.meta.title,f.materials.join('; '),f.methods,f.findings,f.conclusions,r.algorithms.map(a=>a.name).join('; '),r.formulas.map(x=>x.text).join('\n'),r.experimental_data.map(x=>x.text).join('\n'),r.limitations,r.id,r.meta.doi||'',r.meta.url||'',r.source_snippets.length,r.review?.decision==='reviewed'?'已人工复核（原字段）':'待人工复核',r.review?.note||'',...roleCells(r),r.paper_id,r.pdf_hash,r.parser_version||'',r.extractor_version||''];
}

function csvText(rows){
 const safe=value=>{let text=String(value??'');if(/^\s*[=+@-]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';};
 return '\ufeff'+rows.map(row=>row.map(safe).join(',')).join('\r\n')+'\r\n';
}
export function scientificCSV(records){return csvText([SCI_COLUMNS,...records.map(sciRow)]);}

const MATERIAL_HEADERS=['论文ID','材料','材料总体角色','本次提及角色','规则理由','原句','原句证据ID','原论文页码 / 块 / 字符区间','归属上下文原文','上下文证据ID','上下文定位','归属复核状态'];
const NUMERIC_HEADERS=['论文ID','候选序号','数值归属','规则理由','原始值与单位（未归一化）','原句','原句证据ID','原论文页码 / 块 / 字符区间','归属上下文原文','上下文证据ID','上下文定位','归属复核状态'];
const EVIDENCE_HEADERS=['论文ID','证据ID','字段','原论文页码','块ID','起始偏移（含）','结束偏移（不含）','章节候选','原文','策略 / 版本','原PDF SHA256'];

function evidenceFor(r,ids=[]){
 const byId=new Map(r.source_snippets.map(s=>[s.evidence_id,s]));
 return ids.map(id=>{const value=byId.get(id);if(!value)throw Error('导出记录引用了不存在的证据：'+id);return value;});
}
function location(r,ids=[]){return evidenceFor(r,ids).map(s=>`${s.evidence_id}: p${s.page_start}, ${s.block_id}, ${s.start_offset}:${s.end_offset}`).join('; ');}
function quotation(r,ids=[]){return evidenceFor(r,ids).map(s=>s.text).join('\n\n');}

function materialRows(r){
 if(!r.attribution)return (r.materials.length?r.materials:['']).map(name=>[r.paper_id,name,'未执行（历史记录）','','NOT_EXECUTED_HISTORICAL_RECORD','','','','','','','未执行']);
 return (r.attribution.materials||[]).flatMap(material=>(material.mentions||[]).map(mention=>{
  const ids=mention.evidence_ids||[],context=mention.context_evidence_ids||[];
  return [r.paper_id,material.name,roleLabel(MATERIAL_ROLE_LABELS,material.role),roleLabel(MATERIAL_ROLE_LABELS,mention.role),mention.reason||'',quotation(r,ids),ids.join('; '),location(r,ids),quotation(r,context),context.join('; '),location(r,context),'待人工复核'];
 }));
}
function numericValues(candidate){return JSON.stringify(candidate.values||(candidate.value!==undefined?[{value:candidate.value,unit:candidate.unit||''}]:[]));}
function numericRows(r){
 if(!r.attribution)return r.experimental_data.map((candidate,i)=>[r.paper_id,i,'未执行（历史记录）',UNCLASSIFIED,numericValues(candidate),candidate.text,(candidate.evidence_ids||[]).join('; '),location(r,candidate.evidence_ids||[]),'','','','未执行']);
 return (r.attribution.numeric||[]).map(item=>{
  const candidate=numericCandidate(r,item),ids=item.evidence_ids||[],context=item.context_evidence_ids||[];
  return [r.paper_id,item.candidate_index,roleLabel(NUMERIC_ROLE_LABELS,item.role),item.reason||'',numericValues(candidate),candidate.text,ids.join('; '),location(r,ids),quotation(r,context),context.join('; '),location(r,context),'待人工复核'];
 });
}
function evidenceRows(r){return r.source_snippets.map(s=>[r.paper_id,s.evidence_id,s.field,s.page_start,s.block_id,s.start_offset,s.end_offset,s.section_kind||'unknown',s.text,s.strategy||'',r.pdf_hash]);}
export function scientificMaterialRolesCSV(records){return csvText([MATERIAL_HEADERS,...records.flatMap(materialRows)]);}
export function scientificNumericCSV(records){return csvText([NUMERIC_HEADERS,...records.flatMap(numericRows)]);}
export function scientificEvidenceCSV(records){return csvText([EVIDENCE_HEADERS,...records.flatMap(evidenceRows)]);}

const ORIGINAL_HEADERS=['论文ID','论文标题','自动材料候选（含背景）','自动方法原文','自动发现原文','自动结论原文','自动局限候选','结构状态','自动复核状态','原字段人工复核状态','人工修订JSON（原文不覆盖）','人工备注','解析器版本','提取器版本','归属规则版本','原PDF SHA256','原文链接'];
function originalRow(r){return [r.paper_id,r.meta.title,r.materials.join('; '),r.methods,r.findings,r.conclusions,r.limitations,r.status,r.review_status,r.review?.decision||'unreviewed',JSON.stringify(r.review?.edits||{}),r.review?.note||'',r.parser_version||'',r.extractor_version||'',attributionVersion(r),r.pdf_hash,r.meta.url||''];}
const NOTES=[
 ['用途','规则预筛与人工复核。没有独立科研准确率金标准；结构success不代表科研内容正确。'],
 ['汇总与自动原文','科研汇总展示已有人工修订覆盖后的四核心字段。原始自动结果完整保留在第二表和JSONL；人工修订单独保留，不静默重写。'],
 ['材料归属','本文对象、背景、本文对照、试剂/环境、不确定分列。角色只覆盖已识别的材料候选；空白不代表论文没有该类材料。'],
 ['数值归属','本文结果、模拟参数、实验条件、引用/背景和不确定分列。数值句与原始单位保留，未作归一化，不应跨实验条件直接排名。'],
 ['复核边界','原字段人工复核不代表新归属已经复核。自动归属层仍待人工复核；规则标签和原句存在不能证明科学主张正确。'],
 ['历史记录','无attribution解释层的历史research-1记录明确显示NOT_EXECUTED_HISTORICAL_RECORD，不自动补写或当成已经分类。'],
 ['证据定位','页码来自原始论文。字符区间左闭右开，按Unicode字符计数；可用JSONL中的raw_blocks逐字切片回查。'],
 ['文件边界','本文件为research-1规则记录，不等同于ScientificRecord，也不迁移或混用数据库。'],
 ['长单元格','Excel单元格过长时显示明确的截断标记；JSONL仍包含完整内容。'],
 ['PDF与来源','PDF目录只含当前浏览器实际获取且属于所选记录的文件。来源、作者和许可保留在JSONL与LICENSE-MANIFEST.json。']
];
const sx=value=>String(value??'').replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g,'').replace(/[<>&"']/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&apos;'}[c]));
const letter=index=>{let n=index+1,result='';while(n){result=String.fromCharCode(65+(n-1)%26)+result;n=Math.floor((n-1)/26);}return result;};
function excelText(value){
 const text=String(value??'');
 if(text.length<=32760)return text;
 // Excel's string ceiling is conservative in UTF-16 code units. Never cut a
 // surrogate pair; the complete value remains in research.jsonl.
 const prefix=text.slice(0,32700).replace(/[\uD800-\uDBFF]$/,'');
 return prefix+' [截断；完整内容见JSONL]';
}
function sheetXML(headers,rows){
 const all=[headers,...rows],data=all.map((row,i)=>`<row r="${i+1}"${i?'':' ht="36" customHeight="1"'}>`+row.map((value,j)=>`<c r="${letter(j)}${i+1}" t="inlineStr" s="${i?0:1}"><is><t xml:space="preserve">${sx(excelText(value))}</t></is></c>`).join('')+'</row>').join('');
 return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>'+headers.map((_,i)=>`<col min="${i+1}" max="${i+1}" width="${i===0||i===1?38:52}" customWidth="1"/>`).join('')+`</cols><sheetData>${data}</sheetData><autoFilter ref="A1:${letter(headers.length-1)}${all.length}"/></worksheet>`;
}
const STYLES='<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF173E4A"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';
export async function scientificXLSX(records,{batch=null}={}){
 const rows=snapshot(records),zip=new ZipArchive();
 const sheets=[['科研汇总',SCI_COLUMNS,rows.map(sciRow)],['原始自动结果',ORIGINAL_HEADERS,rows.map(originalRow)],['材料角色',MATERIAL_HEADERS,rows.flatMap(materialRows)],['数值归属',NUMERIC_HEADERS,rows.flatMap(numericRows)],['证据',EVIDENCE_HEADERS,rows.flatMap(evidenceRows)],['说明',['项目','说明'],NOTES]];
 if(batch)sheets.unshift(['批次执行',['论文ID','标题','执行状态','处理阶段','失败原因','原PDF SHA256','原文许可','来源','元数据来源与缓存'],batch.items.map(j=>[j.id,j.meta?.title||'',j.state,j.stage,j.error||'',j.pdf_hash||'',j.meta?.license_url||'',j.meta?.url||'',batch.source_notice||''])]);
 if(rows.some(r=>r.reading_card))sheets.push(['中文导读',['论文ID','中文标题','研究什么','研究对象','怎么做','大致步骤','发现什么','作者结论','还要核对什么','说明来源'],rows.filter(r=>r.reading_card).map(r=>{const p=chineseReadingPlan(r);return [r.id,p.title,...['question','objects','methods','steps','findings','conclusions','limitations'].map(k=>p.fields[k].items.map(i=>i.text).join('\n')||p.fields[k].reason),p.notice];})]);
 if(rows.some(r=>r.reading_card))sheets.unshift(['阅读卡片',READING_COLUMNS,rows.map(readingRow)],['关键数值与条件',READING_NUMBERS,rows.flatMap(readingNumbers)],['阅读证据映射',READING_SOURCES,rows.flatMap(readingSources)]);
 await zip.add('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'+sheets.map((_,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')+'</Types>');
 await zip.add('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>');
 await zip.add('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+sheets.map(([name],i)=>`<sheet name="${sx(name)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join('')+'</sheets></workbook>');
 await zip.add('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+sheets.map((_,i)=>`<Relationship Id="rId${i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join('')+`<Relationship Id="rId${sheets.length+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`);
 await zip.add('xl/styles.xml',STYLES);
 for(let i=0;i<sheets.length;i++)await zip.add(`xl/worksheets/sheet${i+1}.xml`,sheetXML(sheets[i][1],sheets[i][2]));
 return zip.blob('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
}
export function researchJSONL(records){return records.map(r=>JSON.stringify(r)).join('\n')+(records.length?'\n':'');}
export async function scientificPackage(records,jobs=[]){
 const rows=snapshot(records),zip=new ZipArchive(),selected=new Set(rows.flatMap(r=>[r.id,r.paper_id,r.meta.id].filter(Boolean)));
 const includedJobs=jobs.filter(j=>[j.id,j.meta?.id,j.meta?.paper_id].some(id=>selected.has(id)));
 await zip.add('科研汇总.xlsx',await scientificXLSX(rows));
 await zip.add('科研汇总.csv',scientificCSV(rows));
 await zip.add('research.jsonl',researchJSONL(rows));
 if(rows.some(r=>r.reading_card)){await zip.add('阅读卡片.csv',csvText([READING_COLUMNS,...rows.map(readingRow)]));await zip.add('reading-evidence.csv',csvText([READING_SOURCES,...rows.flatMap(readingSources)]));await zip.add('reading.jsonl',rows.filter(r=>r.reading_card).map(r=>JSON.stringify({schema_version:'paperlens-reading-1',paper_id:r.paper_id,pdf_hash:r.pdf_hash,reading_card:r.reading_card})).join('\n')+'\n');}
 await zip.add('material_roles.csv',scientificMaterialRolesCSV(rows));
 await zip.add('numeric_attribution.csv',scientificNumericCSV(rows));
 await zip.add('evidence.csv',scientificEvidenceCSV(rows));
 await zip.add('knowledge_graph.json',JSON.stringify(researchGraph(rows),null,2));
 await zip.add('results.jsonl',rows.filter(r=>r.legacy_record).map(r=>JSON.stringify(r.legacy_record)).join('\n')+(rows.some(r=>r.legacy_record)?'\n':''));
 await zip.add('reviews.jsonl',rows.filter(r=>r.review).map(r=>JSON.stringify({paper_id:r.paper_id,review:r.review})).join('\n')+(rows.some(r=>r.review)?'\n':''));
 await zip.add('review.jsonl',rows.filter(r=>r.review?.decision!=='reviewed').map(r=>JSON.stringify({paper_id:r.paper_id,reason:'manual_scientific_review_required'})).join('\n'));
 await zip.add('failures.jsonl',includedJobs.filter(j=>j.error).map(j=>JSON.stringify({paper_id:j.meta?.paper_id||j.id,status:j.state,error:j.error})).join('\n'));
 for(const j of includedJobs)if(j.pdf)await zip.add('PDF/'+j.id.replace(/[^\w.-]/g,'_')+'.pdf',j.pdf);
 await zip.add('LICENSE-MANIFEST.json',JSON.stringify(rows.map(r=>({paper_id:r.paper_id,id:r.id,title:r.meta.title,authors:r.meta.authors||[],source_url:r.meta.url||'',license_url:r.meta.license_url||'',pdf_sha256:r.pdf_hash,pdf_included:includedJobs.some(j=>j.pdf&&[j.id,j.meta?.id,j.meta?.paper_id].filter(Boolean).some(id=>[r.id,r.paper_id,r.meta.id].filter(Boolean).includes(id)))})),null,2));
 await zip.add('README.txt','PaperLens 半自动科研记录导出。材料、方法、发现与结论需人工复核，不保证完整性。\n角色和数值归属为单独的规则解释层；原字段人工复核不等于归属层已复核。没有归属层的历史记录明确标记未执行。\n科研汇总展示人工修订覆盖后的四字段；原始自动结果在第二工作表和JSONL完整保留，reviews.jsonl保留修订与备注。\n来源证据包含原论文页码、原始块和Unicode字符区间（左闭右开）。字面匹配不证明科研解释正确。\n数值和单位未归一化；不能直接跨条件排名。Excel超长单元格有截断标记，JSONL保留全文。\nresults.jsonl保持旧三字段契约；research.jsonl是research-1规则记录，不是ScientificRecord。\nPDF目录仅包含当前浏览器实际取得且属于本次所选记录的PDF，不表示全库全文均已下载。作者、来源和许可见LICENSE-MANIFEST.json，请按各篇许可使用。\n');
 return zip.blob();
}

export function readingEvidenceCSV(records){return csvText([READING_SOURCES,...records.flatMap(readingSources)]);}
