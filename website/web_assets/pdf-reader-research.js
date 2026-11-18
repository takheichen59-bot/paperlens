import {headingKind} from './screening.js';
const CAPTION=/^\s*(?:fig(?:ure)?\.?|table|scheme)\s*(?:S?\d+|[IVXLCDM]+)\b/i;
function abort(signal){if(signal?.aborted)throw new DOMException('已暂停','AbortError');}
export function layoutBlocks(pages,policy){
 const blocks=[];
 for(const page of pages){const items=page.items.filter(t=>t.str?.trim()).map(t=>({text:t.str,x:t.transform?.[4]??t.x,y:page.height-(t.transform?.[5]??(page.height-t.y)),w:t.width||t.w||0,h:Math.abs(t.height||t.transform?.[3]||t.h||10),font:t.font||t.fontName||''}));
  const left=items.filter(t=>t.text.length>=12&&t.x<page.width*.45&&t.x+t.w<page.width*.55),right=items.filter(t=>t.text.length>=12&&t.x>page.width*.48);const pairs=left.flatMap(l=>right.filter(r=>l.x+l.w+page.width*.02<r.x&&Math.abs(l.y-r.y)<Math.max(l.h,r.h)*.8));const two=left.length>=2&&right.length>=2&&pairs.length>=2;
  const middle=page.width*.5,wideRows=items.filter(t=>t.x<middle-2&&t.x+t.w>middle+2).map(t=>t.y);for(const l of items.filter(t=>t.x<middle&&t.x+t.w<=middle)){const r=items.find(t=>t.x>=middle&&Math.abs(t.y-l.y)<3&&t.x-(l.x+l.w)<Math.max(t.h,l.h));if(r)wideRows.push(l.y);}
  const sizes=items.map(t=>t.h).sort((a,b)=>a-b),bodySize=sizes[Math.floor(sizes.length/2)]||10;const lines=[];
  for(const t of items){const side=two?(t.w>page.width*.6||wideRows.some(y=>Math.abs(y-t.y)<3)?-1:(t.x+t.w/2>=page.width*.5?1:0)):0;let line=lines.filter(l=>l.side===side&&Math.abs(l.y-t.y)<=Math.max(3,Math.min(l.h,t.h)*.6)).sort((a,b)=>Math.abs(a.y-t.y)-Math.abs(b.y-t.y))[0];if(!line){line={side,y:t.y,h:t.h,items:[]};lines.push(line);}line.items.push(t);line.h=Math.max(line.h,t.h);}
  for(const l of lines){l.items.sort((a,b)=>a.x-b.x);l.x=l.items[0].x;l.font=l.items.map(t=>t.font).join(' ');l.text='';let last=null;for(const t of l.items){const gap=last?t.x-(last.x+last.w):0;const space=last&&gap>Math.min(last.h,t.h)*.18&&!/\s$/.test(l.text)&&!/^\s/.test(t.text);l.text+=(space?' ':'')+t.text;last=t;}l.text=l.text.trim().replace(/\bWe(?=(?:outline|discuss|study|investigate|present|report|observe|calculate|show|find)\b)/g,'We ').replace(/\bOur(?=results\b)/g,'Our ');}
  const ordered=[];const wide=lines.filter(l=>l.side===-1).sort((a,b)=>a.y-b.y);let narrow=lines.filter(l=>l.side!==-1);
  for(const w of wide){const before=narrow.filter(l=>l.y<w.y);ordered.push(...before.sort((a,b)=>a.side-b.side||a.y-b.y),w);narrow=narrow.filter(l=>l.y>=w.y);}ordered.push(...narrow.sort((a,b)=>a.side-b.side||a.y-b.y));
  let paragraph=null,index=0;const flush=()=>{if(paragraph){paragraph.text=paragraph.lines.map(l=>l.text).join('\n');paragraph.bbox=[paragraph.x,paragraph.firstY,paragraph.right,paragraph.lastY+paragraph.h];delete paragraph.firstY;delete paragraph.right;delete paragraph.lines;blocks.push(paragraph);paragraph=null;}};
  for(const l of ordered){const explicit=!!headingKind(l.text,policy);const strong=(/bold|cmbx|demi|medi|semibold/i.test(l.font)||l.h>bodySize*1.2)&&l.text.length<90&&l.text.split(/\s+/).length<=12&&!/[.!?;]$/.test(l.text)&&!/[=∑∂]/.test(l.text);const heading=explicit||strong;const pageNumber=/^(?:S?\d+|[ivxlcdm]+)$/i.test(l.text)&&(l.y<page.height*.08||l.y>page.height*.92);const caption=CAPTION.test(l.text);const edge=l.y<page.height*.08||l.y>page.height*.92;
   const newPara=!paragraph||heading||paragraph.heading||caption||paragraph.side!==l.side||l.y-paragraph.lastY>Math.max(l.h,paragraph.h)*1.7||Math.abs(l.x-paragraph.x)>l.h*1.5||pageNumber||paragraph.margin;
   if(newPara){flush();paragraph={block_id:'p'+page.number+'-b'+index++,page:page.number,text:'',lines:[],x:l.x,h:l.h,side:l.side,lastY:l.y,firstY:l.y,right:Math.max(...l.items.map(t=>t.x+t.w)),heading,caption,edge,margin:pageNumber};}
   paragraph.lines.push(l);paragraph.lastY=l.y;paragraph.right=Math.max(paragraph.right,...l.items.map(t=>t.x+t.w));
  }flush();
 }
 const repeated=new Map();for(const b of blocks)if(b.edge){const key=b.text.replace(/\d+/g,'#').trim();const set=repeated.get(key)||new Set();set.add(b.page);repeated.set(key,set);}
 for(const b of blocks)if(b.edge&&(repeated.get(b.text.replace(/\d+/g,'#').trim())?.size||0)>=2)b.margin=true;
 return blocks;
}
export async function readPDF(blob,policy,{signal,onProgress=()=>{}}={}){
 abort(signal);let pdfjs;
 try{pdfjs=await import('/vendor/pdf.min.mjs');}catch{throw Error('PDF 阅读器加载失败，请检查网络后重试；已下载的 PDF 可先导出。');}
 pdfjs.GlobalWorkerOptions.workerSrc='/vendor/pdf.worker.min.mjs';
 const task=pdfjs.getDocument({data:await blob.arrayBuffer(),isEvalSupported:false,useSystemFonts:true});const cancel=()=>task.destroy();signal?.addEventListener('abort',cancel,{once:true});let pdf;
 try{pdf=await task.promise;if(pdf.numPages>300)throw Error('这篇超过浏览器处理的 300 页上限；PDF 仍可下载。');const pages=[];for(let n=1;n<=pdf.numPages;n++){abort(signal);onProgress('读取第 '+n+'/'+pdf.numPages+' 页');const p=await pdf.getPage(n),v=p.getViewport({scale:1}),content=await p.getTextContent();pages.push({number:n,width:v.width,height:v.height,items:content.items.filter(i=>i.str)});p.cleanup();}const blocks=layoutBlocks(pages,policy);if(blocks.reduce((n,b)=>n+b.text.length,0)<80)throw Error('未读取到足够文本，可能是扫描件；需要 OCR，PDF 仍可下载。');return blocks;}finally{signal?.removeEventListener('abort',cancel);if(pdf)await pdf.destroy();else await task.destroy();}
}
