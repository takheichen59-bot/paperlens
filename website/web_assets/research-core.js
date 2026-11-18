import {buildBrowserReading} from './research-reading.js';
import {analyzeBlocks,headingKind} from './screening.js';
import {validateResearch} from './research-shared.js';
import {buildAttribution,validateAttribution,sentenceRanges} from './research-attribution.js';
const CP=s=>Array.from(s).length;
export const BROWSER_SCIENTIFIC_VERSION='browser-scientific-rules-v1.6';
const ALG={'density functional theory':/\b(?:DFT|density[ -]functional theory)\b/i,'molecular dynamics':/\bmolecular dynamics\b/i,'Monte Carlo':/\bMonte[ -]Carlo\b/i,'finite element method':/\b(?:finite element|FEM)\b/i,'random forest':/\brandom forests?\b/i,'neural network':/\b(?:neural networks?|deep learning)\b/i,'support vector machine':/\b(?:support vector machines?|SVM)\b/i,'Gaussian process':/\bGaussian process(?:es)?\b/i,'gradient boosting':/\b(?:gradient boosting|XGBoost)\b/i,'PBE functional':/\bPBE\b/i};
export function scientificFromBlocks(blocks,meta,policy,pdfHash){
 const base=analyzeBlocks(blocks,meta,policy),body=[];let kind='unknown',title=null,terminal=false;
 for(const b of blocks){if(b.margin||b.caption)continue;const h=headingKind(b.text,policy);if(h){kind=h;title=b.text.trim();if(['references','supplement'].includes(h))terminal=true;continue;}if(terminal)continue;if(b.heading){kind='unknown';title=b.text.trim();continue;}body.push({...b,kind,section_title:title});}
 const evidence=base.record.source_snippets.map(s=>({...s,section_kind:body.find(b=>b.block_id===s.block_id)?.kind||'unknown',evidence_id:''}));for(const s of evidence)s.evidence_id='e'+(evidence.indexOf(s)+1);
 function add(b,field,a=0,z=b.text.length){const s={evidence_id:'e'+(evidence.length+1),field,text:b.text.slice(a,z),block_id:b.block_id,start_offset:CP(b.text.slice(0,a)),end_offset:CP(b.text.slice(0,z)),page_start:b.page,page_end:b.page,section:b.section_title,section_kind:b.kind,strategy:BROWSER_SCIENTIFIC_VERSION};evidence.push(s);return s;}
 for(const s of base.findings_evidence){const b=body.find(b=>b.block_id===s.block_id);if(!b)continue;evidence.push({...s,evidence_id:'e'+(evidence.length+1),field:'findings',page_start:s.page,page_end:s.page,section_kind:b.kind,strategy:BROWSER_SCIENTIFIC_VERSION});}
 const algorithms=[];for(const [name,re] of Object.entries(ALG)){const b=body.find(b=>re.test(b.text));if(b){const match=b.text.match(re),s=add(b,'algorithms',match.index,match.index+match[0].length);algorithms.push({name,evidence_ids:[s.evidence_id]});}}
 const formulas=[],experimental_data=[],limitations=[];for(const b of body){let offset=0;for(const line of b.text.split(/(?<=\n)/)){const text=line.trim();if(formulas.length<12&&text.length<180&&/[=≡≈∝].*(?:\d|[α-ωΑ-Ω∂∇Σ∑∫]|\b[A-Za-z]\b)/.test(text)){const a=offset+line.indexOf(text),s=add(b,'formulas',a,a+text.length);formulas.push({text,format:'pdf_text_candidate',evidence_ids:[s.evidence_id]});}offset+=line.length;}
 for(const [a,z] of sentenceRanges(b.text)){const text=b.text.slice(a,z);if(text.length<12||text.length>900)continue;const values=[...text.matchAll(/(?<!\w)([−-]?\d+(?:\.\d+)?)\s*(GPa|MPa|kPa|meV|eV|nm|μm|µm|mm|mV|GHz|THz|MHz|Hz|°C|K|%|Å)(?!\w)/g)].slice(0,8).map(n=>({value:n[1],unit:n[2]}));if(values.length&&experimental_data.length<16){const s=add(b,'experimental_data',a,z);experimental_data.push({text,value:values[0].value,unit:values[0].unit,values,kind:'measurement_candidate',evidence_ids:[s.evidence_id]});}if(limitations.length<4&&/\b(?:limitation|limited by|future work|not considered|beyond the scope)\b/i.test(text)){limitations.push(add(b,'limitations',a,z));}}}
 const record={schema_version:'research-1',paper_id:meta.paper_id||(meta.source==='local'?'local:'+pdfHash:'arxiv:'+meta.id.replace(/v\d+$/,'')),id:meta.id,meta,pdf_hash:pdfHash,parser_version:'pdfjs-layout-v1.1',extractor_version:BROWSER_SCIENTIFIC_VERSION,created_at:new Date().toISOString(),materials:base.record.chemicals,methods:base.record.methods,conclusions:base.record.conclusions,findings:[...new Set(evidence.filter(s=>s.field==='findings').map(s=>s.text))].join('\n\n'),algorithms,formulas,experimental_data,limitations:[...new Set(limitations.map(s=>s.text))].join('\n\n'),source_snippets:evidence,raw_blocks:blocks.map(b=>({block_id:b.block_id,page:b.page,text:b.text,...(b.bbox?{bbox:b.bbox}:{})})),eligible_ranges:body.map(b=>({block_id:b.block_id,start:0,end:CP(b.text),section_kind:b.kind})),status:base.record.status,review_status:'unreviewed',warnings:base.notes,legacy_record:base.record};
 record.attribution=buildAttribution(record,body,add);
 const fragments=record.attribution.materials.filter(m=>m.mentions.some(x=>x.match_status==='partial_token')).map(m=>m.name);if(fragments.length)record.warnings.push('原始材料候选 '+fragments.join('、')+' 仅命中复合词片段；保留候选与证据，归属未确认，不能当作独立材料。');
 record.reading_card=buildBrowserReading(record);
 // This new extraction version populates the three core prose fields from the
 // generic reading selection. The historical baseline stays in legacy_record.
 const upgraded=new Set(['methods','findings','conclusions']);
 record.source_snippets=record.source_snippets.filter(s=>!upgraded.has(s.field));
 for(const field of upgraded){const values=[];for(const id of record.reading_card.fields[field].evidence_ids){const sentence=record.reading_card.evidence.find(e=>e.id===id),parts=sentence.parts.map(p=>({...p,text:Array.from(record.raw_blocks.find(b=>b.block_id===p.block_id).text).slice(p.start,p.end).join('')}));
 if(field==='methods'&&[...values,...parts.map(p=>p.text)].join('\n\n').length>3000)continue;
 for(const p of parts){if(values.includes(p.text))continue;values.push(p.text);record.source_snippets.push({evidence_id:'auto-v2-'+field+'-'+values.length,field,text:p.text,block_id:p.block_id,start_offset:p.start,end_offset:p.end,page_start:p.page,page_end:p.page,section:null,section_kind:sentence.section_kind,strategy:BROWSER_SCIENTIFIC_VERSION});}}
 record[field]=values.join('\n\n');}
 const filled=['materials','methods','findings','conclusions'].filter(f=>record[f].length).length;record.status=filled===4?'success':filled?'partial':'failed';
 return validateAttribution(validateResearch(record));
}
