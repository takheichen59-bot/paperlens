import {renderChineseReport} from './reading-layout.js';
import {chineseReadingPlan} from './reading-chinese.js';
// Selectable, source-linked PDF. Automatic candidates remain separate from
// authored source_review and from historical/manual research-1 fields.
import {PDFDocument,PDFName,PDFString,PDFHexString,rgb} from './vendor/pdf-lib.esm.min.js';
import fontkit from './vendor/fontkit.es.min.js';

const PAGE=[595.28,841.89],LEFT=42,RIGHT=553.28,TOP=800,BOTTOM=48;
const BODY=11,LEADING=15.6,INK=rgb(.09,.18,.23),MUTED=rgb(.34,.43,.47),ACCENT=rgb(.09,.36,.39);
const clean=value=>String(value??'').replace(/\s+/gu,' ').trim();
const cpLength=text=>Array.from(text).length;
const typeLabels={perspective_or_review:'综述或观点文章（初步判断）',computational:'计算研究（初步判断）',mixed_computational_experimental:'计算与实验研究（初步判断）',experimental_or_unresolved:'实验研究（初步判断）',unresolved:'类型尚未判定'};
const roleLabels={material_family:'材料类别候选',study_subject_variant:'组分变体候选',component_or_termination:'组分 / 表面终止候选',study_subject:'本文对象（规则候选）',background:'背景提及',uncertain:'角色待核实',comparator:'本文对照候选',impurity_in_host:'杂质 / 宿主候选',research_topic_not_sample:'研究主题，非样品',title_study_object_candidate:'标题对象候选',impurity_in_host_candidate:'杂质 / 宿主候选'};

/** Wrap at words and Unicode code points, never at UTF-16 surrogate halves. */
export function wrapReportText(text,font,size,width){
 const value=clean(text);if(!value)return [''];
 const tokens=value.match(/[\p{Script=Latin}\p{Script=Greek}\p{N}\u0300-\u036F]+(?:[-’'.,][\p{Script=Latin}\p{Script=Greek}\p{N}\u0300-\u036F]+)*|\s+|[^\s]/gu)||[];
 const lines=[];let line='';
 for(const token of tokens){
  if(!line&&/^\s+$/u.test(token))continue;
  const next=line+token;
  if(font.widthOfTextAtSize(next,size)<=width){line=next;continue;}
  if(/^[，。！？；：、）》】」』”’、,.!?;:)\]]+$/u.test(token)&&line.trim()){
   const chars=Array.from(line.trimEnd()),closing=[];while(chars.length&&/^[，。！？；：、）》】」』”’、,.!?;:)\]]$/u.test(chars.at(-1)))closing.unshift(chars.pop());
   const base=chars.join(''),tail=base.match(/[\p{Script=Latin}\p{Script=Greek}\p{N}]+(?:[-’'.,][\p{Script=Latin}\p{Script=Greek}\p{N}]+)*$|.$/u)?.[0]||'';
   const prefix=base.slice(0,-tail.length);if(prefix)lines.push(prefix.trimEnd());line=tail+closing.join('')+token;if(font.widthOfTextAtSize(line,size)>width)throw Error('单词和句末标点无法完整放入一行，请调整显示内容；原文保持不变。');continue;
  }
  const opening=line.match(/[（《【「『“‘]$/u)?.[0]||'';if(opening){line=line.slice(0,-opening.length);if(line.trim())lines.push(line.trimEnd());line=opening+token;continue;}
  if(line.trim())lines.push(line.trimEnd());line=/^\s+$/u.test(token)?'':token;
  if(line&&font.widthOfTextAtSize(line,size)>width)throw Error('报告含无法完整排入一行的单词；原文保留在 JSONL，请缩短显示字段或使用可换行标题。');
 }
 if(line.trim())lines.push(line.trimEnd());return lines;
}

function sourceMap(record){return new Map((record.reading_card?.evidence||[]).map(e=>[e.id,e]));}
function citedPages(ids,byId){return [...new Set(ids.flatMap(id=>byId.get(id)?.pages||[]))].sort((a,b)=>a-b);}
function titleOf(r){return clean(r.reading_card?.title||r.meta?.title||r.id||r.paper_id||'未提供论文标题').replace(/\\beta/g,'β').replace(/\$_?\{?([0-9x]+)\}?\$/g,(_,s)=>Array.from(s).map(c=>'₀₁₂₃₄₅₆₇₈₉'['0123456789'.indexOf(c)]||'ₓ').join('')).replace(/\$/g,'');}
const complete=text=>/[.!?。！？][”'”"]?$|(?<![0-9])[.!?][0-9,–−-]+$/u.test(clean(text));

function selectEvidence(ids,byId,{limit=2,maxCharacters=340,used=new Set()}={}){
 const selected=[],seen=new Set();let omitted=0;
 for(const id of ids||[]){
  const evidence=byId.get(id);if(!evidence)throw Error('PDF 阅读字段引用不存在的证据：'+String(id));
  const text=clean(evidence.text);if(seen.has(text)){omitted++;continue;}seen.add(text);
  if(used.has(id)){omitted++;continue;}
  if(selected.length>=limit||cpLength(text)>maxCharacters||!complete(text)){omitted++;continue;}
  selected.push({text,evidence_ids:[id]});used.add(id);
 }
 return {selected,omitted};
}

function fieldContent(c,name,byId,used,limit=2){
 const f=c?.fields?.[name];
 if(!f)return {items:[],reason:'阅读层未执行或未提供该字段，未从历史原文推断补写。'};
 if(f.status==='not_applicable')return {items:[],reason:'不适用：'+clean(f.reason||'文章类型不适用此栏目。')};
 const picked=selectEvidence(f.evidence_ids||[],byId,{limit,used});
 let reason=picked.selected.length?'':clean(f.reason)||((f.evidence_ids||[]).length?'本字段候选与已列证据重复、过长或不完整；完整候选及原句见 JSONL。':'未定位完整候选，未将空白解释为论文没有报告。');
 if(picked.omitted)reason+=(reason?' ':'')+'另有 '+picked.omitted+' 条未在报告重复展开的候选，完整内容见 JSONL；未截断原句。';
 return {items:picked.selected,reason};
}

/** A bounded display plan; raw evidence, source reviews and human history stay untouched. */
export function readingReportPlan(records,{language='source'}={}){
 return Array.from(records,r=>{
  const c=r.reading_card||{},byId=sourceMap(r),used=new Set(),fields={};
  if(language==='zh-CN'){
   const chinese=chineseReadingPlan(r),evidence=[...new Set(Object.values(chinese.fields).flatMap(f=>f.items.flatMap(i=>i.evidence_ids||[])).concat(chinese.numbers.flatMap(n=>n.evidence_ids||[])))];
   return {record:r,c,byId,title:chinese.title,id:clean(r.id||r.paper_id),fields:chinese.fields,numbers:chinese.numbers,unbound:0,usedEvidence:evidence,sourceReview:chinese.guide,chinese};
  }

  fields.question=fieldContent(c,'question',byId,used,1);
  const objects=(c.objects||[]).filter(o=>o.evidence_ids?.length&&['study_subject','study_subject_variant','material_family','impurity_in_host','title_study_object_candidate','impurity_in_host_candidate','research_topic_not_sample'].includes(o.role)).slice(0,5).map(o=>({text:clean(o.name)+' — '+(roleLabels[o.role]||clean(o.role)||'角色未核实'),evidence_ids:o.evidence_ids}));
  for(const o of objects)for(const id of o.evidence_ids)if(!byId.has(id))throw Error('PDF 研究对象缺少对应来源证据。');
  fields.objects={items:objects,reason:objects.length?((c.objects||[]).length>5?'更多材料及角色见 JSONL；未将全部材料提及都当作本文样品。':''):'未定位有来源的研究对象 / 主题；未使用背景材料自动补齐。'};
  const routes=(c.method_routes||[]).filter(m=>m.evidence_ids?.length).slice(0,4).map(m=>({text:clean(m.label||m.name||m.category),evidence_ids:m.evidence_ids}));
  for(const m of routes)for(const id of m.evidence_ids)if(!byId.has(id))throw Error('PDF 方法路线缺少来源证据。');
  fields.methods=fieldContent(c,'methods',byId,used,routes.length?1:2);
  if(routes.length)fields.methods.items.push({text:'规则路线分类：'+routes.map(m=>m.text).join('；'),evidence_ids:[...new Set(routes.flatMap(m=>m.evidence_ids))]});
  const techniques=(c.techniques||[]).filter(t=>t.evidence_ids?.length);if(techniques.length)fields.methods.items.unshift({text:'技术词候选：'+techniques.map(t=>clean(t.label||t.name)).join('；'),evidence_ids:[...new Set(techniques.flatMap(t=>t.evidence_ids))]});
 const steps=[];let omittedSteps=0;
  for(const step of c.procedure_steps||[]){
   if(!step.evidence_ids?.length)throw Error('PDF 操作候选缺少来源证据。');
   for(const id of step.evidence_ids||[])if(!byId.has(id))throw Error('PDF 操作候选缺少来源证据。');
   const text=clean(step.text);if(steps.length>=3||cpLength(text)>320||!complete(text)||steps.some(s=>s.text===text)||(step.evidence_ids||[]).some(id=>used.has(id))){omittedSteps++;continue;}
   // These are source-order candidates, not a verified protocol or an inferred sequence.
   steps.push({text,evidence_ids:step.evidence_ids||[]});for(const id of step.evidence_ids||[])used.add(id);
  }
  fields.steps={items:steps,reason:c.article_type?.label==='perspective_or_review'?'观点 / 综述候选，不套用实验操作步骤。':!steps.length?'未形成完整操作候选；原文出现顺序不能自动视为可复现实验流程。':'按来源出现顺序排列；尚未核实步骤完整性及实际先后。'};
  if(omittedSteps)fields.steps.reason+=' 另有 '+omittedSteps+' 条候选保留在 JSONL，未截断原句。';
  fields.findings=c.article_type?.label==='perspective_or_review'?{...selectEvidence((c.argument_candidates||[]).flatMap(a=>a.evidence_ids),byId,{limit:3,used}),reason:'文章论点与方法挑战的原文候选，不是原创实验结果。'}:fieldContent(c,'findings',byId,used,2);if(fields.findings.selected){fields.findings.items=fields.findings.selected;delete fields.findings.selected;}
  fields.conclusions=fieldContent(c,'conclusions',byId,used,2);
  fields.limitations=fieldContent(c,'limitations',byId,used,1);
  const numbers=[];let unbound=0;
  for(const n of c.numeric_bindings||[]){
   if(!['object','quantity','value','unit','conditions','ownership'].every(k=>clean(n[k]))||!n.evidence_ids?.length){unbound++;continue;}
   if(n.evidence_ids.some(id=>!byId.has(id)))throw Error('PDF 数值绑定缺少来源证据。');
   if(numbers.length<3)numbers.push({...n});else unbound++;
  }
  return {record:r,c,byId,title:titleOf(r),id:clean(r.id||r.paper_id),fields,numbers,unbound:unbound+(c.numeric_candidates||[]).length,
   usedEvidence:[...new Set([...['question','methods','steps','findings','conclusions','objects','limitations'].flatMap(name=>fields[name].items.flatMap(i=>i.evidence_ids||[])),...numbers.flatMap(n=>n.evidence_ids)])],
   sourceReview:c.source_review||null};
 });
}

function annotation(doc,page,rect,{uri,destination}){
 const value={Type:'Annot',Subtype:'Link',Rect:rect,Border:[0,0,0]};
 if(uri)value.A={Type:'Action',S:'URI',URI:PDFString.of(uri)};
 else value.Dest=[destination.ref,PDFName.of('Fit')];
 page.node.addAnnot(doc.context.register(doc.context.obj(value)));
}
function bookmarks(doc,entries){
 const root=doc.context.obj({Type:'Outlines',Count:entries.length}),rootRef=doc.context.register(root);
 const items=entries.map(({title,page})=>doc.context.obj({Title:PDFHexString.fromText(title),Parent:rootRef,Dest:[page.ref,PDFName.of('Fit')]}));
 const refs=items.map(item=>doc.context.register(item));
 items.forEach((item,i)=>{if(i)item.set(PDFName.of('Prev'),refs[i-1]);if(i+1<refs.length)item.set(PDFName.of('Next'),refs[i+1]);});
 if(refs.length){root.set(PDFName.of('First'),refs[0]);root.set(PDFName.of('Last'),refs.at(-1));doc.catalog.set(PDFName.of('Outlines'),rootRef);}
}

/**
 * readingPDF(records, {fontBytes?, batch?, fetchImpl?, fontUrl?, title?}) -> PDF Blob.
 * By default the pinned, privately seeded font is fetched from /api/report-font.
 * No paper or report text is sent to that endpoint or any external service.
 */
export async function readingPDF(records,{fontBytes,batch,fetchImpl=globalThis.fetch,fontUrl='/api/report-font?revision=2',title='PaperLens 中文文献阅读报告',language='zh-CN'}={}){
 const input=Array.from(records),completedIds=batch?.items?new Set(batch.items.filter(i=>i.state==='done').flatMap(i=>[i.id,i.record_id,i.meta?.id,i.meta?.paper_id].filter(Boolean))):null;
 const completed=input.filter(r=>!completedIds||[r.id,r.paper_id,r.meta?.id,r.meta?.paper_id].some(id=>completedIds.has(id)));
 const plan=readingReportPlan(completed,{language});const chinese=language==='zh-CN';
 if(fontBytes===undefined){
  if(typeof fetchImpl!=='function')throw Error('没有可用的字体读取能力；请传入 fontBytes。');
  const response=await fetchImpl(fontUrl,{credentials:'same-origin'});
  if(!response.ok)throw Error('报告字体读取失败（HTTP '+response.status+'）；请先配置固定字体资产后重试。');
  fontBytes=new Uint8Array(await response.arrayBuffer());
 }else if(fontBytes?.arrayBuffer)fontBytes=new Uint8Array(await fontBytes.arrayBuffer());
 else if(fontBytes instanceof ArrayBuffer)fontBytes=new Uint8Array(fontBytes);
 if(!(fontBytes instanceof Uint8Array)||!fontBytes.byteLength)throw Error('fontBytes 必须是非空 TTF 字节。');
 if(String.fromCharCode(...fontBytes.subarray(0,4))==='wOF2')throw Error('报告字体要求静态 TTF；fontkit 可解析 WOFF2，但当前动态子集不能可靠绘制，请先将测试字体转换为 TTF。');
 const doc=await PDFDocument.create();doc.registerFontkit(fontkit);
 // fontkit 1.1.1 runtime subsets of the tested CJK TTF lose visible outlines
 // despite retaining extractable text. Embed one complete, compressed static
 // TTF per PDF instead. It is fetched as an asset, never bundled into Worker JS.
 const font=await doc.embedFont(fontBytes,{subset:false});const supported=new Set(font.getCharacterSet());
 if(chinese)return renderChineseReport({doc,font,plan,batch,title,wrap:wrapReportText});
 doc.setTitle(title);doc.setAuthor('PaperLens');doc.setSubject('Automatic source candidates; unreviewed; scientific accuracy not independently evaluated');
 const allPages=[],overviewPages=[],entryLinks=[],outlines=[];let page,y,phase='overview';
 function checkGlyphs(text){for(const ch of Array.from(text))if(!supported.has(ch.codePointAt(0)))throw Error('报告字体缺少 Unicode U+'+ch.codePointAt(0).toString(16).toUpperCase()+'；原文未改写，请补齐字体覆盖后重试。');}
 function addPage(label=''){
  page=doc.addPage(PAGE);allPages.push(page);y=TOP;
  page.drawText('PAPERLENS · '+label,{x:LEFT,y:y-9,size:9,font,color:MUTED});y-=29;return page;
 }
 function linesFor(text,size=BODY,width=RIGHT-LEFT){checkGlyphs(clean(text));return wrapReportText(text,font,size,width);}
 function ensure(height,label='研究卡片 · 续页'){if(y-height<BOTTOM){addPage(phase==='overview'?'批量概览 · 续页':label);if(phase==='overview')overviewPages.push(page);return true;}return false;}
 function text(text,{size=BODY,color=INK,leading=LEADING,after=6,indent=0,uri}={}){
  const lines=linesFor(text,size,RIGHT-LEFT-indent);let first;
  for(const line of lines){ensure(leading);const baseline=y-size;if(!first)first={page,y:baseline};page.drawText(line,{x:LEFT+indent,y:baseline,size,font,color});if(uri)annotation(doc,page,[LEFT+indent,baseline-2,LEFT+indent+font.widthOfTextAtSize(line,size),baseline+size],{uri});y-=leading;}
  y-=after;return first;
 }
 function heading(value){ensure(41);y-=6;text(value,{size:12.5,color:ACCENT,leading:18,after:4});}
 function citation(item,p){const pages=citedPages(item.evidence_ids||[],p.byId);return pages.length?'（原文第'+pages.join('、')+'页）':'';}
 function renderField(label,value,p){
  heading(label);
  for(const [index,item]of value.items.entries()){
   const marker=value.items.length>1?String(index+1)+'. ':'';
   text(marker+item.text+citation(item,p),{uri:(p.record.meta?.pdf_url||p.record.meta?.url)?(p.record.meta.pdf_url||p.record.meta.url)+'#page='+(citedPages(item.evidence_ids||[],p.byId)[0]||1):undefined});
  }
  if(value.reason)text(value.reason,{color:MUTED});
 }
 function fitFirstPage(p){
  const names=['question','objects','methods','steps','findings'];
  const fields=Object.fromEntries(names.map(name=>{const f=p.fields[name];return [name,{items:[...f.items],reason:f.items.length&&/另有|更多|来源出现顺序/.test(f.reason)?(name==='steps'?'来源顺序候选，非已验证流程；其余完整原句见 JSONL。':'更多完整候选见 JSONL；原句未截断。'):f.reason}];}));
  const height=()=>names.reduce((sum,name)=>sum+28+fields[name].items.reduce((n,item,i)=>n+linesFor((fields[name].items.length>1?String(i+1)+'. ':'')+item.text+citation(item,p)).length*LEADING+6,0)+(fields[name].reason?linesFor(fields[name].reason).length*LEADING+6:0),0);
  for(let count=0;height()>y-BOTTOM-4&&count<40;count++){
   const name=['objects','methods','steps','findings'].find(n=>fields[n].items.length>({objects:2,methods:2,steps:2,findings:1}[n]))||['objects','methods','steps','findings'].find(n=>fields[n].items.length>1);
   if(!name)break;
   fields[name].items.pop();fields[name].reason='报告未展开其余候选；完整原句见 JSONL，未截断。';
  }
  return fields;
 }
 function cardHeader(p,continued=false){
  const start=addPage(continued?'研究卡片 · 结论与证据':'研究卡片 · 中文说明');
  text(p.title,{size:17,color:ACCENT,leading:22,after:8});
  text(p.id+' · '+(typeLabels[p.c.article_type?.label]||'类型尚未判定'),{size:9.5,color:MUTED,leading:13,after:5});
  text(continued?'接着看：作者的结论、适用条件和原文出处。':chinese?p.chinese.notice:'以下为英文原句，尚未经过人工核对。',{color:MUTED,after:7});
  return start;
 }
 addPage('批量概览');overviewPages.push(page);outlines.push({title:'批量概览',page});
 text(title,{size:21,color:ACCENT,leading:28,after:12});
 text(chinese?'按这几个问题读论文：研究什么？怎么做？发现了什么？作者怎么总结？还有哪些地方要核对？':'阅读顺序：问题、对象、方法、步骤、发现、结论、条件和证据。');
 text(chinese?'本报告帮助你读论文。中文说明、自动提取原句和用户复核分开保存；正文的页码可回到原论文。没有中文导读的文章会明确提示待补充。':'本文件是处理报告，原始论文另附。原句存在不代表科研解释已经核实。',{color:MUTED});
 if(batch){
  const items=batch.items||[],requested=Number.isFinite(Number(batch.requested_count))?Math.max(0,Number(batch.requested_count)):items.length;
  const returned=Number.isFinite(Number(batch.source_returned))?Math.max(0,Number(batch.source_returned)):items.length;
  const failed=items.filter(i=>i.state==='failed'||i.error),pending=items.filter(i=>i.state!=='done'&&i.state!=='duplicate'&&i.state!=='failed'&&!i.error),missing=Math.max(0,requested-items.length);
  text('检索词：'+clean(batch.query||'未提供'));
  if(batch.source_notice)text('元数据来源：'+clean(batch.source_notice),{color:MUTED});
  text('目标 '+requested+' 篇 · 来源实际返回 '+returned+' 篇 · 本批保留 '+items.length+' 篇 · 已提取并纳入正文 '+plan.length+' 篇 · 失败 '+failed.length+' 篇 · 内容去重 '+items.filter(i=>i.state==='duplicate').length+' 条 · 未完成 '+pending.length+' 篇 · 未取得目标名额 '+missing+' 篇。');
  if(batch.error)text('批次异常：'+clean(batch.error),{color:MUTED});
  for(const item of failed)text('失败：'+clean(item.id||item.meta?.id||'未提供ID')+' · 阶段 '+clean(item.stage||'未提供')+' · '+clean(typeof item.error==='object'?item.error?.message||JSON.stringify(item.error):item.error||'未记录具体原因'),{color:MUTED});
  if(items.filter(i=>i.state==='done').length>plan.length)text('另有完成状态条目尚未提供对应研究记录，未生成其正文；请回查批次检查点。',{color:MUTED});
 }
 if(!plan.length)text('本次没有可导出的记录。');
 for(const [i,p]of plan.entries()){
  const needed=linesFor(p.title,12.5).length*18+56;
  if(y-needed<BOTTOM){addPage('批量概览 · 续页');overviewPages.push(page);}
  const first=text(String(i+1)+'. '+p.title,{size:12.5,color:ACCENT,leading:18,after:4});
  text(p.id+' · '+(typeLabels[p.c.article_type?.label]||'类型尚未判定')+' · 原文证据 '+p.byId.size+' 句',{size:10,color:MUTED,leading:14,after:12});
  entryLinks.push({page:first.page,rect:[LEFT,first.y-3,RIGHT,first.y+14],plan:p});
 }
 const starts=new Map();
 phase='cards';
 for(const p of plan){
  const start=cardHeader(p);starts.set(p,start);outlines.push({title:p.title,page:start});
  const firstFields=fitFirstPage(p);
  renderField('这篇文章想弄清什么',firstFields.question,p);
  renderField('主要研究什么材料或对象',firstFields.objects,p);
  renderField('作者是怎么做的',firstFields.methods,p);
  renderField('大致做了哪几步',firstFields.steps,p);
  renderField('最值得注意的发现',firstFields.findings,p);
  // A deliberate second-page boundary keeps the same report framework for
  // every paper without reducing body size or leaving headings at page ends.
  cardHeader(p,true);
  renderField('作者最后得出了什么结论',p.fields.conclusions,p);
  heading('关键数值、对象与条件');
  if(!p.numbers.length)text('暂时没有把数值、对应对象和测试条件一起核对清楚。请结合上面的中文发现和原文理解。',{color:MUTED});
  for(const n of p.numbers){
   text(clean(n.object)+' · '+clean(n.quantity)+'：'+clean(n.value)+' '+clean(n.unit)+citation(n,p));
   const condition=clean(n.conditions);
   text('条件：'+(cpLength(condition)<=250?condition:'完整条件原句较长，保留在 JSONL；不得脱离该条件使用此数值。')+'；归属：'+clean(n.ownership),{color:MUTED});
  }
  if(p.unbound)text(p.unbound+' 条其余数值候选 / 未绑定条目完整保留在 JSONL 审计层，不用于跨条件比较。',{color:MUTED});
  const numeric=chinese?[]:p.c.numeric_candidates||[];if(numeric.length){const labels={own_result:'本文结果候选，待核实',simulation_parameter:'模拟参数候选',experimental_condition:'实验条件候选',cited_result:'引用 / 背景结果',uncertain:'归属未确认',needs_review:'归属未确认'},rank={simulation_parameter:0,own_result:1,experimental_condition:2,uncertain:3,cited_result:4};const sample=[...numeric].sort((a,b)=>(rank[a.ownership]??3)-(rank[b.ownership]??3)).slice(0,2);for(const n of sample){text('数值候选：'+(n.values||[{value:n.value,unit:n.unit}]).map(v=>v.value+' '+v.unit).join('；')+' · '+(labels[n.ownership]||'归属未确认')+citation(n,p));}text('以上对象 / 条件仍需结合原句核对；点击页码或查阅 Excel，不据此直接比较性能。',{color:MUTED});}
  renderField('读这篇文章时，要留意什么',p.fields.limitations,p);
  heading('证据与回查');
  const shown=p.usedEvidence.slice(0,5);if(!chinese){
  for(const [index,id]of shown.entries()){
   const e=p.byId.get(id);if(!e)throw Error('报告证据索引缺少原句。');
   const parts=(e.parts||[]).slice(0,2).map(s=>'p.'+s.page+' / '+s.block_id+' ['+s.start+','+s.end+')').join('; ');
   text('E'+(index+1)+' · '+id+' · '+(parts||'原始部分映射未提供'),{size:BODY,color:MUTED});
   if((e.parts||[]).length>2)text('该句跨 '+e.parts.length+' 个来源部分，完整映射见 JSONL。',{color:MUTED});
  }
  text('本卡只展开短且完整的来源句，未截断原文。全部 '+p.byId.size+' 条英文证据、原始块和 Unicode 字符偏移及未展开候选见 research.jsonl / Excel 证据表。',{color:MUTED});
  }
  if(chinese){for(const item of p.chinese.boundaries)text(item.text+citation(item,p),{color:MUTED});text('要核对原句，可以点击各段后的页码。英文原句、字符位置和原始自动结果保留在配套表格和完整记录文件中。',{color:MUTED});}
  heading('这些中文说明从哪里来');
  if(p.sourceReview)text(chinese?'本篇中文内容由助手根据所列原文整理，来源句已绑定，尚未经过用户或领域专家确认。原来的自动提取内容保持不变。':'另有独立的助手导读，本英文原句报告没有用它替换自动结果。',{color:MUTED});
  else text(chinese?'这篇还没有完整中文导读。报告只列出已识别的线索，其他部分需要继续补充。':'本篇尚无助手导读。',{color:MUTED});
  const meta=p.record.meta||{};
  if(meta.pdf_url||meta.url)text('打开原始论文 PDF / 来源页面',{color:ACCENT,uri:meta.pdf_url||meta.url});
  if(meta.license_url)text('原文许可（点击查看）',{color:ACCENT,uri:meta.license_url});
 }
 for(const link of entryLinks)annotation(doc,link.page,link.rect,{destination:starts.get(link.plan)});
 bookmarks(doc,outlines);
 const total=allPages.length;
 allPages.forEach((p,i)=>{
  p.drawLine({start:{x:LEFT,y:34},end:{x:RIGHT,y:34},thickness:.5,color:rgb(.77,.84,.83)});
  p.drawText(chinese?'PaperLens · 中文阅读说明 · 尚待核对':'PaperLens · 原文摘录 · 尚待核对',{x:LEFT,y:20,size:8.5,font,color:MUTED});
  const number=(i+1)+' / '+total;p.drawText(number,{x:RIGHT-font.widthOfTextAtSize(number,8.5),y:20,size:8.5,font,color:MUTED});
  p.drawText('返回概览',{x:265,y:20,size:8.5,font,color:ACCENT});annotation(doc,p,[262,17,310,30],{destination:overviewPages[0]});
 });
 return new Blob([await doc.save()],{type:'application/pdf'});
}
