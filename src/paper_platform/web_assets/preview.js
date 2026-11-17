// Browser-only quick screening. It is deliberately NOT the measured Python engine.
const escapeRE=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export function formula(value,policy,context=''){
 if(/^[HKL]{2,}\d*$/.test(value)&&/\b(?:planes?|reflections?|peaks?|facets?|orientations?|precession|indices)\b/i.test(context))return false;
 if(policy.known_formulas.includes(value))return true;
 if(!/[a-z0-9]/.test(value))return false;
 const parts=[...value.matchAll(/([A-Z][a-z]?)(\d*)/g)];
 if(parts.map(m=>m[0]).join('')!==value||parts.length<2||parts.length>8)return false;
 const counts=parts.map(m=>Number(m[2]||1));if(counts.some(n=>n<1||n>999)||parts.some(m=>!policy.oxidation[m[1]]))return false;
 const solve=(i,total,positive,negative)=>i===parts.length?total===0&&positive&&negative:policy.oxidation[parts[i][1]].some(v=>solve(i+1,total+counts[i]*v,positive||v>0,negative||v<0));
 return solve(0,0,false,false);
}
export function extractPreview(blocks,meta,policy){
 let kind='unknown',section=null,terminal=false;const eligible=[];
 for(const b of blocks){
  const heading=b.text.trim().replace(/^(?:\d+(?:\.\d+)*[.)]?|[IVXLCDM]+\.|[A-Z]\.)\s+/i,'').replace(/[.:]$/,'').toLowerCase();
  const found=policy.headings[heading];
  if(found){if(!terminal||['references','supplement'].includes(found)){kind=found;section=b.text.trim();if(['references','supplement'].includes(kind))terminal=true;}continue;}
  if(terminal||b.margin||/^\s*(?:fig(?:ure)?\.?|table|scheme)\s*(?:S?\d+|[IVXLCDM]+)\b/i.test(b.text))continue;
  eligible.push({...b,kind,section});
 }
 const chemicals=[],chemicalBlocks=[],seen=new Set();
 for(const b of eligible){const hits=[];
  for(const term of policy.terms){for(const m of b.text.matchAll(new RegExp('(?<!\\w)'+escapeRE(term)+'(?!\\w)','gi')))hits.push({index:m.index,text:m[0]});}
  for(const m of b.text.matchAll(/\b(?:[A-Z][a-z]?\d*)+\b/g)){if(formula(m[0],policy,b.text.slice(Math.max(0,m.index-100),m.index+m[0].length+100)))hits.push({index:m.index,text:m[0]});}
  if(hits.length)chemicalBlocks.push(b);
  for(const m of hits.sort((a,b)=>a.index-b.index)){if(!seen.has(m.text.toLowerCase())){seen.add(m.text.toLowerCase());chemicals.push(m.text);}}
 }
 const methods=[];let length=0;
 for(const b of eligible.filter(b=>b.kind==='methods'&&b.text.length>25)){const added=b.text.length+(methods.length?2:0);if(length+added>3000)break;methods.push(b);length+=added;}
 const conclusions=eligible.filter(b=>b.kind==='conclusions'&&b.text.length>20);
 const snippet=(b,field)=>({field,text:b.text,page_start:b.page,page_end:b.page,section:b.section,block_id:b.block_id,start_offset:0,end_offset:Array.from(b.text).length,strategy:'browser-preview-0.1.2'});
 const record={doi:meta.doi||null,title:meta.title||meta.id,source_url:meta.url||'https://arxiv.org/abs/'+meta.id,chemicals,
  conclusions:conclusions.map(b=>b.text).join('\n\n'),methods:methods.map(b=>b.text).join('\n\n'),extraction_method:'browser-preview-0.1.2',
  source_snippets:[...chemicalBlocks.map(b=>snippet(b,'chemicals')),...methods.map(b=>snippet(b,'methods')),...conclusions.map(b=>snippet(b,'conclusions'))],status:'failed'};
 const n=Number(chemicals.length>0)+Number(!!record.methods)+Number(!!record.conclusions);record.status=n===3?'success':n?'partial':'failed';return record;
}
