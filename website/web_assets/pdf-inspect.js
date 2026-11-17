let library;
export async function inspectPDF(blob,meta={}, {signal}={}){
 const canceled=()=>{if(signal?.aborted)throw new DOMException('已暂停','AbortError');};canceled();
 if(!(await blob.slice(0,5).text()).startsWith('%PDF-'))throw Error('文件不是有效的 PDF');
 const bytes=await blob.arrayBuffer();const digest=await crypto.subtle.digest('SHA-256',bytes);const sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
 if(!library){library=await import('/vendor/pdf.min.mjs');library.GlobalWorkerOptions.workerSrc='/vendor/pdf.worker.min.mjs';}
 const task=library.getDocument({data:bytes,isEvalSupported:false,useSystemFonts:true}),cancel=()=>task.destroy();signal?.addEventListener('abort',cancel,{once:true});let doc;
 try{doc=await task.promise;if(doc.numPages>300)throw Error('超过浏览器 300 页检查上限，请分篇或使用本地获取脚本。');let chars=0;for(let n=1;n<=doc.numPages;n++){canceled();const page=await doc.getPage(n),text=await page.getTextContent();chars+=text.items.reduce((s,x)=>s+(x.str||'').length,0);}if(chars<200)throw Error('可读取文本不足，可能是扫描件，需要 OCR 后再处理。');if(meta.sha256&&meta.sha256!==sha256)throw Error('PDF 与已核验索引哈希不符，请重新下载。');return {sha256,pages:doc.numPages,text_characters:chars,bytes:blob.size};}
 finally{signal?.removeEventListener('abort',cancel);if(doc)await doc.destroy();else await task.destroy();}
}
