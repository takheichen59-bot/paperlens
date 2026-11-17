// File usability only. No scientific field extraction in Phase 1.
export async function inspectPDF(blob,meta,{signal}={}){
 if(signal?.aborted)throw new DOMException('已暂停','AbortError');
 if(!(await blob.slice(0,1024).text()).includes('%PDF-'))throw Error('文件不是有效 PDF');
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');
 if(meta.sha256&&hash!==meta.sha256)throw Error('PDF 与已核验 SHA256 不符');
 const pdfjs=await import('/vendor/pdf.min.mjs');pdfjs.GlobalWorkerOptions.workerSrc='/vendor/pdf.worker.min.mjs';
 const task=pdfjs.getDocument({data:await blob.arrayBuffer(),isEvalSupported:false,useSystemFonts:true,stopAtErrors:true});
 const cancel=()=>task.destroy();signal?.addEventListener('abort',cancel,{once:true});let doc;
 try{doc=await task.promise;if(doc.numPages>300)throw Error('网页最多检查 300 页；请下载后人工核验。');let characters=0;for(let n=1;n<=doc.numPages;n++){if(signal?.aborted)throw new DOMException('已暂停','AbortError');const page=await doc.getPage(n);const content=await page.getTextContent();characters+=content.items.map(x=>x.str||'').join(' ').trim().length;page.cleanup();}if(characters<200)throw Error('可读取文本不足 200 字符，可能为扫描件，需人工核验。');return {sha256:hash,bytes:blob.size,pages:doc.numPages,text_characters:characters};}
 finally{signal?.removeEventListener('abort',cancel);if(doc)await doc.destroy();else await task.destroy();}
}
