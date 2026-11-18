// Browser-only rule candidates. This is not model output or scientific validation.
// Quoted text stays raw; every stored offset counts Unicode code points, as Python does.
export const ATTRIBUTION_VERSION='browser-context-roles-v1.2';
export const MATERIAL_ROLE_LABELS={study_subject:'本文研究对象（规则候选）',background:'背景提及',comparator:'本文对照材料（规则候选）',reagent_or_environment:'试剂 / 环境',uncertain:'归属不确定'};
export const NUMERIC_ROLE_LABELS={own_result:'本文结果（规则候选）',simulation_parameter:'模拟参数',experimental_condition:'实验条件',cited_result:'引用 / 背景数值',uncertain:'归属不确定'};
const PRIOR=/\b(?:in (?:recent|previous|prior|earlier) (?:work|studies|research)|(?:previous|prior|earlier|other) (?:stud\w*|work|report\w*)|(?:[A-Z][a-z]+ et al\.|collaborators)\s*(?:\[.{1,25}?\])?\s*(?:have |has )?(?:report\w*|investigat\w*|found|show\w*)|(?:has|have) been (?:reported|demonstrated|found)|previous record|best known|well known|canonical example)\b/i;
const OWN=/\b(?:we (?:have )?(?:stud\w*|investigat\w*|analy[sz]\w*|explor\w*|observ\w*|find|found|show\w*|report\w*|synthesi[sz]\w*|compar\w*|simulat\w*|measur\w*|calculat\w*|characteriz\w*|combin\w*|used?)|(?:this|our) (?:paper|work|study|results?|simulations?|measurements?)\s+(?:\w+\s+){0,3}(?:analy[sz]\w*|investigat\w*|show\w*|demonstrat\w*|reveal\w*|report\w*))\b/i;
const CITATION=/\[\d[\d\s,–−-]*\]/;
const PARAMETER=/\b(?:chosen|set to|used|using|cutoff|cut-off|basis|sampling|thermaliz\w*|time step|excitation|laser|temperature.dependent|growth conditions|anneal\w*|dried|ampul\w*|rod|diameter|wavelength|filter|kept constant)\b/i;
const COMPUTATIONAL=/\b(?:simulat\w*|molecular dynamics|comput\w*|plane.wave|cutoff|cut-off|supercell|Brillouin|density functional|relaxation|thermal noise)\b/i;
const RESULT=/\b(?:we (?:have )?(?:observ\w*|find|found|show\w*)|(?:our|these|the) results? (?:show|reveal|indicate)|volume (?:of .{0,60}is .{0,30})?(?:increas\w*|decreas\w*|smaller|larger)|(?:is|was) (?:lower|higher) in energy|(?:is|was) found|we observed)\b/i;
const normalize=s=>String(s??'').replace(/([\p{L}\p{N}_])-\s*\n\s*([\p{L}\p{N}_])/gu,'$1$2').replace(/\s+/gu,' ');
const escape=s=>String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const materialPattern=name=>new RegExp('(?<![\\p{L}\\p{N}_])'+escape(name)+'(?![\\p{L}\\p{N}_])','iu');
const matches=(re,text)=>[...text.matchAll(new RegExp(re.source,re.flags+'g'))];
function resetPrior(preceding){const text=normalize(preceding),own=matches(OWN,text),prior=matches(PRIOR,text);return own.length&&(!prior.length||own.at(-1).index>prior.at(-1).index)?'':preceding;}

// Return UTF-16 indices for JS slicing; add() converts these indices to code points.
export function sentenceRanges(text){
 const ranges=[];let start=0;
 for(const match of text.matchAll(/[.!?](?=\s+[A-Z]|\s*$)/g)){
  const end=match.index+match[0].length;let a=start;while(a<end&&/\s/u.test(text[a]))a++;
  if(end>a)ranges.push([a,end]);start=end;
 }
 while(start<text.length&&/\s/u.test(text[start]))start++;
 const end=text.trimEnd().length;if(end>start)ranges.push([start,end]);return ranges;
}

export function materialRole(name,sentence,preceding,section,title){
 const text=normalize(sentence),own=OWN.test(text),prior=PRIOR.test(text)||(PRIOR.test(normalize(preceding))&&!own);
 if(prior)return own?['uncertain','mixed_current_and_prior_work']:['background','explicit_prior_work_context'];
 const escaped=escape(name);
 if(new RegExp('(?:compar\\w* .{0,100}?\\b(?:with|to)|versus|against|control(?: material)?(?: of)?)\\s+(?:\\w+\\s+){0,2}'+escaped,'i').test(text)||new RegExp(escaped+'.{0,30}\\bas (?:a |the )?(?:control|reference sample)\\b','i').test(text))return ['comparator','explicit_current_comparison'];
 if(new RegExp('\\b(?:washed|rinsed|dissolved|sealed|atmosphere|solvent)\\b.{0,45}'+escaped,'i').test(text))return ['reagent_or_environment','procedural_reagent_or_environment'];
 if(section==='introduction'&&!own)return ['background','background_without_current_action'];
 if(materialPattern(name).test(normalize(title).replace(/[$_{}\\]/g,'')))return ['study_subject','material_in_paper_title'];
 if(own&&new RegExp('\\b(?:stud\\w*|investigat\\w*|analy[sz]\\w*|explor\\w*|synthesi[sz]\\w*|compar\\w*)\\b.{0,100}'+escaped,'i').test(text))return ['study_subject','explicit_current_study_action'];
 if(section==='methods'&&new RegExp(escaped+'.{0,45}\\b(?:samples?|crystals?|nanoparticles?)\\b.{0,35}\\b(?:grown|prepared|synthesi[sz]ed|measured)\\b','i').test(text))return ['study_subject','current_sample_preparation'];
 if(CITATION.test(text)&&!own)return ['background','background_or_citation_without_current_action'];
 return ['uncertain','insufficient_role_context'];
}

export function numericRole(sentence,preceding,section,methodsContext=''){
 const text=normalize(sentence),originalBefore=normalize(preceding),previousOwn=matches(OWN,originalBefore),previousPrior=matches(PRIOR,originalBefore),inheritedOwn=previousOwn.length&&(!previousPrior.length||previousOwn.at(-1).index>previousPrior.at(-1).index),before=normalize(resetPrior(preceding)),own=OWN.test(text),prior=PRIOR.test(text)||(PRIOR.test(before)&&!own);
 if(prior)return own?['uncertain','mixed_current_and_prior_work']:['cited_result','explicit_prior_work_context'];
 if(own&&CITATION.test(text))return ['uncertain','current_statement_with_citation_requires_review'];
 if(section==='introduction'&&CITATION.test(text))return ['cited_result','background_citation'];
 if((RESULT.test(text)&&PARAMETER.test(text))||/\b(?:resulting in|experimental value|compared with|compared to|versus)\b/i.test(text))return ['uncertain','mixed_result_condition_or_comparison'];
 if((own||inheritedOwn)&&!CITATION.test(text)&&/\b(?:find|found|possesses|has an internal transition)\b/i.test(text)&&section!=='methods')return ['own_result','current_work_result_with_local_context'];
 if(RESULT.test(text)&&(own||['results','discussion','conclusions','inferred_results'].includes(section)))return ['own_result','current_result_statement'];
 if(PARAMETER.test(text)&&section==='methods'){
  if(/\b(?:laser|growth|anneal\w*|dried|ampul\w*|rod|diameter|filter|wavelength)\b/i.test(text))return ['experimental_condition','experimental_procedure'];
  if(COMPUTATIONAL.test(text)||COMPUTATIONAL.test(normalize(methodsContext)))return ['simulation_parameter','computational_procedure'];
  return ['experimental_condition','method_condition'];
 }
 if(['results','discussion','conclusions'].includes(section)&&!CITATION.test(text))return ['own_result','result_section_without_external_attribution'];
 return ['uncertain','insufficient_or_mixed_numeric_context'];
}

export function buildAttribution(record,body,add){
 const firstMethods=body.findIndex(b=>b.kind==='methods'),methodsContext=body.filter(b=>b.kind==='methods').map(b=>b.text).join(' '),mentions=new Map(record.materials.map(name=>[name,[]]));
 for(const [index,block] of body.entries()){
  let section=block.kind;if(section==='unknown'&&firstMethods>=0&&index<firstMethods&&block.page>1)section='introduction';
  for(const [start,end] of sentenceRanges(block.text)){
   const sentence=block.text.slice(start,end),preceding=resetPrior(block.text.slice(0,start));
   for(const [name,items] of mentions){
    if(!materialPattern(name).test(sentence))continue;
    const [role,reason]=materialRole(name,sentence,preceding,section,record.meta.title||''),ev=add(block,'material_roles',start,end),context=[];
    if(preceding.trim()&&['explicit_prior_work_context','mixed_current_and_prior_work'].includes(reason))context.push(add(block,'attribution_context',0,start).evidence_id);
    items.push({role,reason,evidence_ids:[ev.evidence_id],context_evidence_ids:context});
   }
  }
 }
 // Preserve legacy keyword fragments (for example GeTe inside Fe₅GeTe₂) as
 // uncertain audit candidates, never as a standalone material or study sample.
 for(const [name,items] of mentions){if(items.length)continue;for(const block of body){for(const [start,end] of sentenceRanges(block.text)){const sentence=block.text.slice(start,end);if(!sentence.toLowerCase().includes(name.toLowerCase()))continue;const ev=add(block,'material_roles',start,end);items.push({role:'uncertain',reason:'partial_token_candidate_not_standalone_material',match_status:'partial_token',evidence_ids:[ev.evidence_id],context_evidence_ids:[]});if(items.length>=2)break;}if(items.length>=2)break;}}
 const byId=new Map(record.source_snippets.map(s=>[s.evidence_id,s])),numeric=[];
 for(const [candidateIndex,candidate] of record.experimental_data.entries()){
  const ev=byId.get(candidate.evidence_ids[0]),index=body.findIndex(b=>b.block_id===ev?.block_id),block=body[index];
  if(!block)throw Error('Numeric candidate outside extraction view');
  // Stored offsets count code points; slicing JS strings needs UTF-16 positions.
  const before=Array.from(block.text).slice(0,ev.start_offset).join(''),preceding=resetPrior(before);let section=block.kind;
  if(section==='unknown'&&firstMethods>=0)section=index<firstMethods?'introduction':'inferred_results';
  const [role,reason]=numericRole(candidate.text,preceding,section,methodsContext),context=[];
  if(preceding.trim()&&['explicit_prior_work_context','mixed_current_and_prior_work'].includes(reason))context.push(add(block,'attribution_context',0,before.length).evidence_id);
  numeric.push({candidate_index:candidateIndex,role,reason,evidence_ids:[...candidate.evidence_ids],context_evidence_ids:context});
 }
 const materials=[...mentions].map(([name,items])=>{
  const roles=new Set(items.map(x=>x.role)),current=[...roles].filter(role=>['study_subject','comparator','reagent_or_environment'].includes(role));
  const role=current.length===1?current[0]:roles.size===1&&roles.has('background')?'background':'uncertain';
  return {name,role,mentions:items,evidence_ids:[...new Set(items.flatMap(x=>x.evidence_ids))]};
 });
 return {version:ATTRIBUTION_VERSION,mode:'rule_candidates_not_scientific_validation',review_status:'unreviewed',materials,numeric,limitations:[
  'Only existing browser chemical candidates are classified; missing species are not inferred.',
  'Browser PDF layout and rules differ from the Python parser; this is not model output or an accuracy evaluation.',
  'Mixed attribution, unknown sections and cross-block citations require manual review.'
 ]};
}

export function validateAttribution(record){
 const layer=record.attribution;if(!layer)return record;
 if(![ATTRIBUTION_VERSION,'browser-context-roles-v1.1','browser-context-roles-v1','context-roles-v1','context-roles-v1.1'].includes(layer.version)||layer.review_status!=='unreviewed')throw Error('Unsupported attribution layer');
 const byId=new Map(record.source_snippets.map(s=>[s.evidence_id,s]));
 if(!Array.isArray(layer.materials)||JSON.stringify(layer.materials.map(m=>m.name))!==JSON.stringify(record.materials))throw Error('Attribution material candidate mismatch');
 function context(item){for(const eid of item.context_evidence_ids||[])if(byId.get(eid)?.field!=='attribution_context')throw Error('Attribution context evidence mismatch');}
 for(const material of layer.materials){
  if(!Object.hasOwn(MATERIAL_ROLE_LABELS,material.role)||!Array.isArray(material.mentions)||!material.mentions.length)throw Error('Invalid material role');
  const expected=[...new Set(material.mentions.flatMap(m=>m.evidence_ids))];if(JSON.stringify(expected)!==JSON.stringify(material.evidence_ids))throw Error('Material evidence aggregation mismatch');
  for(const mention of material.mentions){
   if(!Object.hasOwn(MATERIAL_ROLE_LABELS,mention.role)||!Array.isArray(mention.evidence_ids)||!mention.evidence_ids.length)throw Error('Invalid material mention');
   for(const eid of mention.evidence_ids){const ev=byId.get(eid);if(ev?.field!=='material_roles')throw Error('Material mention evidence mismatch');if(mention.match_status==='partial_token'){if(layer.version!==ATTRIBUTION_VERSION||material.role!=='uncertain'||mention.role!=='uncertain'||mention.reason!=='partial_token_candidate_not_standalone_material'||materialPattern(material.name).test(ev.text)||!ev.text.toLowerCase().includes(material.name.toLowerCase()))throw Error('Invalid partial material candidate');}else if(!materialPattern(material.name).test(ev.text))throw Error('Material mention evidence mismatch');}
   context(mention);
  }
 }
 if(!Array.isArray(layer.numeric)||layer.numeric.length!==record.experimental_data.length)throw Error('Numeric attribution coverage mismatch');
 for(const [i,item] of layer.numeric.entries()){
  if(item.candidate_index!==i||!Object.hasOwn(NUMERIC_ROLE_LABELS,item.role)||JSON.stringify(item.evidence_ids)!==JSON.stringify(record.experimental_data[i].evidence_ids))throw Error('Numeric attribution evidence mismatch');
  context(item);
 }
 return record;
}
