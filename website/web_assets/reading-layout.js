// Chinese editorial layout. Analogy and fact blocks have separate labels and colors.
import {PDFName,PDFString,PDFHexString,rgb} from './vendor/pdf-lib.esm.min.js';
import {drawReadingDiagram} from './report-illustrations.js';
const PAGE=[595.28,841.89],L=44,R=551,W=507,BOTTOM=52;
const C={ink:rgb(.12,.22,.28),muted:rgb(.36,.43,.47),accent:rgb(.12,.37,.45),line:rgb(.79,.85,.87),fact:rgb(.94,.97,.985),warm:rgb(.995,.958,.88),neutral:rgb(.965,.97,.975)};
export async function renderChineseReport({doc,font,plan,batch,title,wrap}){
 doc.setTitle(title);doc.setAuthor('PaperLens');doc.setSubject('中文要点、助手生活比喻与理解示意，均待核对');
 const supported=new Set(font.getCharacterSet()),pages=[],outlines=[],nav=[];let page,y,current=null,phase='overview';
 function lines(s,size=11.5,width=W){const text=String(s??'').replace(/\s+/gu,' ').trim();for(const c of text)if(!supported.has(c.codePointAt(0)))throw Error('报告字体缺少 Unicode U+'+c.codePointAt(0).toString(16).toUpperCase());return wrap(text,font,size,width);}
 function link(rect,uri,dest){const a={Type:'Annot',Subtype:'Link',Rect:rect,Border:[0,0,0]};if(uri)a.A={Type:'Action',S:'URI',URI:PDFString.of(uri)};else a.Dest=[dest.ref,PDFName.of('Fit')];page.node.addAnnot(doc.context.register(doc.context.obj(a)));}
 function newPage(label='阅读概览'){
  page=doc.addPage(PAGE);pages.push(page);y=794;
  page.drawText('PAPERLENS',{x:L,y,size:9,font,color:C.accent});page.drawText(label,{x:R-font.widthOfTextAtSize(label,9),y,size:9,font,color:C.muted});
  page.drawLine({start:{x:L,y:782},end:{x:R,y:782},thickness:.7,color:C.line});y=761;return page;
 }
 function ensure(h){if(h>690)throw Error('一个报告分区过长，请拆分说明后导出，原文不会被截断。');if(y-h<BOTTOM){newPage(phase==='overview'?'阅读概览 · 续页':'继续读 · '+current.id);if(current)small(current.title,{size:13,color:C.accent,after:12});}}
 function small(s,{size=10,color=C.muted,after=5,width=W,x=L,leading=size+5,uri}={}){const rows=lines(s,size,width);for(const t of rows){ensure(leading+after);const b=y-size;page.drawText(t,{x,y:b,size,font,color});if(uri)link([x,b-2,x+font.widthOfTextAtSize(t,size),b+size],uri);y-=leading;}y-=after;}
 function source(ids,p){const rows=ids.map(id=>p.byId.get(id));if(rows.some(x=>!x))throw Error('图解或比喻缺少可回查的来源。');return [...new Set(rows.flatMap(x=>x.pages||[]))].sort((a,b)=>a-b);}
 function section(label){ensure(42);y-=4;small(label,{size:13.5,color:C.accent,after:8,leading:19});}
 function card(label,items,p,{tone='fact',reason='',note=''}={}){
  const width=W-28,blocks=items.map(i=>({item:i,rows:lines(i.text,11.5,width),sources:source(i.evidence_ids||[],p)}));
  const extra=reason?lines(reason,10.5,width):[];const notes=note?lines(note,10,width):[];
  const h=18+19+(blocks.length?blocks.reduce((s,b)=>s+b.rows.length*18+(b.sources.length?15:0)+9,0):extra.length*16)+notes.length*15+9;
  ensure(h+12);page.drawRectangle({x:L,y:y-h,width:W,height:h,color:C[tone],borderColor:C.line,borderWidth:.5});page.drawRectangle({x:L,y:y-h,width:3,height:h,color:tone==='warm'?rgb(.75,.51,.22):C.accent});
  let yy=y-17;page.drawText(label,{x:L+14,y:yy-11,size:11,font,color:C.accent});yy-=26;
  if(blocks.length)for(const b of blocks){for(const row of b.rows){page.drawText(row,{x:L+14,y:yy-11.5,size:11.5,font,color:C.ink});yy-=18;}if(b.sources.length){const s='原文第 '+b.sources.join('、')+' 页';page.drawText(s,{x:L+14,y:yy-9,size:9,font,color:C.muted});const uri=p.record.meta?.pdf_url||p.record.meta?.url;if(uri)link([L+14,yy-11,R-14,yy+2],uri+'#page='+b.sources[0]);yy-=15;}yy-=9;}
  else for(const row of extra){page.drawText(row,{x:L+14,y:yy-10.5,size:10.5,font,color:C.muted});yy-=16;}
  for(const row of notes){page.drawText(row,{x:L+14,y:yy-10,size:10,font,color:C.muted});yy-=15;}
  y-=h+12;
 }
 function field(label,f,p,opts){card(label,f.items,p,{reason:f.reason,...opts});}
 function steps(p){const items=p.fields.steps.items;if(!items.length){field('把方法拆开看',p.fields.steps,p);return;}section('把方法拆开看');
  for(let at=0;at<items.length;at+=2){const row=items.slice(at,at+2),width=(W-12)/2,content=row.map(i=>({item:i,rows:lines(i.text,11,width-24),sources:source(i.evidence_ids||[],p)})),h=34+Math.max(...content.map(b=>b.rows.length*17+17))+12;ensure(h+10);
   content.forEach((b,j)=>{const x=L+j*(width+12);page.drawRectangle({x,y:y-h,width,height:h,color:C.fact,borderColor:C.line,borderWidth:.5});page.drawText('第 '+(at+j+1)+' 步',{x:x+12,y:y-21,size:10,font,color:C.accent});let yy=y-42;for(const t of b.rows){page.drawText(t,{x:x+12,y:yy,size:11,font,color:C.ink});yy-=17;}if(b.sources.length){const s='原文第 '+b.sources.join('、')+' 页';page.drawText(s,{x:x+12,y:yy-2,size:9,font,color:C.muted});const uri=p.record.meta?.pdf_url||p.record.meta?.url;if(uri)link([x+10,yy-5,x+width-10,yy+10],uri+'#page='+b.sources[0]);}});y-=h+12;
  }
 }
 function analogy(a,p){card(a.title,[a],p,{tone:'warm',note:'比喻只帮助理解：'+a.limit});}
 function diagram(d,p){if(!d)return;const caption=lines(d.caption,10,W-28),limit=lines(d.limit,9.5,W-28),h=162+caption.length*15+limit.length*14;ensure(h+12);page.drawRectangle({x:L,y:y-h,width:W,height:h,color:C.neutral,borderColor:C.line,borderWidth:.5});page.drawText('看图理解 · 助手示意',{x:L+14,y:y-21,size:10,font,color:C.accent});drawReadingDiagram(page,d.type,{x:L+18,y:y-128,width:W-36,height:92,font});let yy=y-144;for(const t of caption){page.drawText(t,{x:L+14,y:yy,size:10,font,color:C.ink});yy-=15;}for(const t of limit){page.drawText(t,{x:L+14,y:yy,size:9.5,font,color:C.muted});yy-=14;}const ss=source(d.evidence_ids||[],p);if(ss.length){const st='对应概念：原文第 '+ss.join('、')+' 页';page.drawText(st,{x:L+14,y:yy-4,size:9,font,color:C.muted});const uri=p.record.meta?.pdf_url||p.record.meta?.url;if(uri)link([L+14,yy-7,R-14,yy+8],uri+'#page='+ss[0]);}y-=h+12;}
 function header(p,part){current=p;phase='article';const first=newPage(part);small(p.title,{size:18,color:C.ink,leading:25,after:7});small(p.id+' · 中文导读，尚待核对',{size:9,after:12});return first;}
 const overview=newPage();outlines.push({title:'从这里开始读',page:overview});
 small(title,{size:24,color:C.accent,leading:32,after:10});small('先把论文读明白，再回原文看细节。',{size:14,color:C.ink,after:14});
 small('每篇按同一条线来读：研究什么 → 怎么做 → 发现什么 → 怎么理解。',{size:11.5,color:C.ink,after:14});
 card('三种分区，别混在一起看',[{text:'浅蓝色写论文要点；浅黄色放生活比喻；浅灰色提醒适用条件和需要核对的地方。',evidence_ids:[]}],{byId:new Map(),record:{}},{tone:'neutral'});
 small('中文说明和生活比喻由助手整理，尚待用户或专家核对。示意图帮助理解，不是论文原图或实验数据。',{size:10,after:14});
 if(batch){const failed=(batch.items||[]).filter(i=>i.state==='failed'||i.error),pending=(batch.items||[]).filter(i=>!['done','duplicate','failed'].includes(i.state));small('本次整理 '+plan.length+' 篇；失败 '+failed.length+' 篇，未完成 '+pending.length+' 篇。',{size:11.5,color:C.ink,after:8});if(failed.length)for(const f of failed)small(f.id+'：'+String(f.error?.message||f.error||'请查看批次记录'));small('检索式：'+String(batch.query||'未记录'),{size:10,after:12});}
 section('这一组论文，各自在看什么');
 for(const p of plan){const rows=lines(p.title,12,W-25),h=rows.length*18+26;ensure(h+8);const top=y;page.drawRectangle({x:L,y:y-h,width:W,height:h,color:C.fact});small(p.title,{size:12,color:C.accent,width:W-24,x:L+12,leading:18,after:3});small(p.id,{size:9,x:L+12,after:9});nav.push({page,rect:[L,top-h,R,top],plan:p});y-=8;}
 const starts=new Map();
 for(const p of plan){const first=header(p,'先看懂 · 研究与方法');starts.set(p,first);outlines.push({title:p.title,page:first});
  field('这篇想弄清什么',p.fields.question,p);field('主要看什么对象',p.fields.objects,p);field('作者怎么做',p.fields.methods,p);steps(p);
  const aids=p.chinese.aids;
  if(aids&&(aids.diagram||aids.analogies?.length)){
   header(p,'换个角度 · 图解与生活比喻');diagram(aids.diagram,p);
   for(const a of aids.analogies||[])analogy(a,p);
   small('这一页帮助入门。具体发现和结论请看下一页，并回到原文核对。',{size:10,after:12});
  }
  header(p,'回到论文 · 发现、结论与边界');
  const findings=p.fields.findings;card(p.c.article_type?.label==='perspective_or_review'?'论文的主要观点':'论文报告了哪些发现',findings.items.map((item,i)=>({...item,text:findings.items.length>1?(i+1)+'）'+item.text:item.text})),p,{reason:findings.reason});
  field('作者最后怎么总结',p.fields.conclusions,p);
  if(p.chinese.boundaries.length)card('读到这里，记住这些边界',p.chinese.boundaries,p,{tone:'neutral'});
  field('作者有没有说研究还缺什么',p.fields.limitations,p,{tone:'neutral'});
  section('想核对时，从这里回到原文');small('蓝色要点旁的页码都可以点击。完整英文原句、自动提取结果和处理记录保留在配套表格与记录文件中。',{size:10.5});
  const uri=p.record.meta?.pdf_url||p.record.meta?.url;if(uri)small('打开这篇原始论文',{size:11,color:C.accent,uri,after:10});
 }
 for(const n of nav){page=n.page;link(n.rect,null,starts.get(n.plan));}
 const root=doc.context.obj({Type:'Outlines',Count:outlines.length}),rootRef=doc.context.register(root),items=outlines.map(o=>doc.context.obj({Title:PDFHexString.fromText(o.title),Parent:rootRef,Dest:[o.page.ref,PDFName.of('Fit')]})),refs=items.map(i=>doc.context.register(i));items.forEach((a,i)=>{if(i)a.set(PDFName.of('Prev'),refs[i-1]);if(i+1<refs.length)a.set(PDFName.of('Next'),refs[i+1]);});if(refs.length){root.set(PDFName.of('First'),refs[0]);root.set(PDFName.of('Last'),refs.at(-1));doc.catalog.set(PDFName.of('Outlines'),rootRef);}
 pages.forEach((p,i)=>{page=p;p.drawLine({start:{x:L,y:34},end:{x:R,y:34},thickness:.6,color:C.line});p.drawText('论文要点与生活比喻分开阅读',{x:L,y:20,size:8.5,font,color:C.muted});const number=(i+1)+' / '+pages.length;p.drawText(number,{x:R-font.widthOfTextAtSize(number,8.5),y:20,size:8.5,font,color:C.muted});p.drawText('回到目录',{x:270,y:20,size:8.5,font,color:C.accent});link([267,17,315,31],null,overview);});
 return new Blob([await doc.save()],{type:'application/pdf'});
}
