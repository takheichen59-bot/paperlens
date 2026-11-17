import {readFile,writeFile,mkdir,readdir} from 'node:fs/promises';
await mkdir('dist/server',{recursive:true});await mkdir('dist/.openai',{recursive:true});
const assets={};
for(const file of await readdir('web_assets',{recursive:true})){
 if((await import('node:fs/promises')).stat && !(await (await import('node:fs/promises')).stat('web_assets/'+file)).isFile())continue;
 const mime=file.endsWith('.html')?'text/html;charset=utf-8':file.endsWith('.css')?'text/css;charset=utf-8':(file.endsWith('.js')||file.endsWith('.mjs'))?'text/javascript;charset=utf-8':'application/json;charset=utf-8';
 assets['/'+(file==='index.html'?'':file)]={data:(await readFile('web_assets/'+file)).toString('base64'),mime};
}
for(const file of await readdir('downloads'))assets['/downloads/'+file]={data:(await readFile('downloads/'+file)).toString('base64'),mime:file.endsWith('.zip')?'application/zip':file.endsWith('.whl')?'application/octet-stream':'text/plain;charset=utf-8'};
const source=(await readFile('worker/api.mjs','utf8')).replace('export async function api','async function api')+'\n'+(await readFile('web_assets/research-shared.js','utf8'))+'\n'+(await readFile('worker/research-api.mjs','utf8')).replace(/^import .*;$/gm,'');
await writeFile('dist/server/index.js',`${source}\nconst assets=${JSON.stringify(assets)};\nconst CORPUS=${await readFile('web_assets/phase1-index.json','utf8')};\nconst RESEARCH_INDEX=${await readFile('web_assets/research-index.json','utf8')};\nexport default {async fetch(request,env){const p=new URL(request.url).pathname;if(p.startsWith('/api/research/'))return researchApi(request,env,RESEARCH_INDEX);if(p.startsWith('/api/'))return api(request,env,CORPUS);if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405});const a=assets[p==='/index.html'?'/':p];if(!a)return new Response('Not found',{status:404});const data=Uint8Array.from(atob(a.data),c=>c.charCodeAt(0));return new Response(request.method==='HEAD'?null:data,{headers:{'Content-Type':a.mime,'X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin',...(p.startsWith('/downloads/')?{'Content-Disposition':'attachment; filename="'+p.split('/').pop()+'"'}:{})}})}};\n`);
await writeFile('dist/.openai/hosting.json',await readFile('.openai/hosting.json'));
console.log('Built Worker with',Object.keys(assets).length,'assets');
