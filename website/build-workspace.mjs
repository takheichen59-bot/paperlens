import {readFile,writeFile,mkdir,readdir,stat} from 'node:fs/promises';
import path from 'node:path';
const dataDirectory=process.env.PAPERLENS_SITE_DATA||'seed';
const corpus=JSON.parse(await readFile(path.join(dataDirectory,'corpus.json'),'utf8'));
const reportFont=JSON.parse(await readFile(path.join(dataDirectory,'report-font.json'),'utf8'));
const index=JSON.parse(await readFile(path.join(dataDirectory,'research-index.json'),'utf8'));
await mkdir('dist/server',{recursive:true});await mkdir('dist/.openai',{recursive:true});
const assets={};
for(const file of await readdir('web_assets',{recursive:true})){
 if(!(await stat(path.join('web_assets',file))).isFile()||['phase1-index.json','research-index.json','index.html'].includes(file))continue;
 const type=file.endsWith('.html')?'text/html;charset=utf-8':file.endsWith('.css')?'text/css;charset=utf-8':/\.m?js$/.test(file)?'text/javascript;charset=utf-8':file.endsWith('.woff2')?'font/woff2':file.endsWith('.svg')?'image/svg+xml':'application/json;charset=utf-8';
 assets['/'+file]={data:(await readFile(path.join('web_assets',file))).toString('base64'),mime:type};
}
assets['/']={data:(await readFile('web_assets/workspace.html')).toString('base64'),mime:'text/html;charset=utf-8'};
assets['/phase1-index.json']={data:Buffer.from(JSON.stringify(corpus)).toString('base64'),mime:'application/json;charset=utf-8'};
assets['/research-index.json']={data:Buffer.from(JSON.stringify(index)).toString('base64'),mime:'application/json;charset=utf-8'};
const sources=[];
for(const file of ['worker/api.mjs','web_assets/reading-chinese.js','web_assets/research-attribution.js','web_assets/research-reading.js','web_assets/reading-rules.js','web_assets/research-shared.js','worker/research-api.mjs','worker/discovery.mjs','worker/workspace-api.mjs','worker/batch-api.mjs']){
 sources.push((await readFile(file,'utf8')).replace(/^import .*;\s*$/gm,'').replace(/^export /gm,''));
}
const security={"X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin","Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; worker-src 'self' blob:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'"};
await writeFile('dist/server/index.js',sources.join('\n')+`\nconst ASSETS=${JSON.stringify(assets)};\nconst CORPUS=${JSON.stringify(corpus)};\nconst RESEARCH_INDEX=${JSON.stringify(index)};\nconst REPORT_FONT=${JSON.stringify(reportFont)};
const SECURITY=${JSON.stringify(security)};
export default {async fetch(request,env,ctx){
 const url=new URL(request.url),p=url.pathname;
 if(['PUT','POST','DELETE'].includes(request.method)&&request.headers.get('Origin')&&request.headers.get('Origin')!==url.origin)return Response.json({error:'Cross-origin write rejected'},{status:403});
 if(p.startsWith('/api/batches')||p==='/api/batch-pdf'||p==='/api/report-font')return batchApi(request,env,REPORT_FONT);
 if(p==='/api/health'||p==='/api/discovery'||p==='/api/research/download')return workspaceApi(request,env,CORPUS,RESEARCH_INDEX);
 if(p.startsWith('/api/research/'))return researchApi(request,env,RESEARCH_INDEX);
 if(p.startsWith('/api/'))return api(request,env,CORPUS);
 if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405});
 const item=ASSETS[p==='/index.html'?'/':p];if(!item)return new Response('Not found',{status:404,headers:SECURITY});
 return new Response(request.method==='HEAD'?null:Uint8Array.from(atob(item.data),c=>c.charCodeAt(0)),{headers:{...SECURITY,'Content-Type':item.mime,'Cache-Control':p.startsWith('/vendor/')||p.startsWith('/fonts/')?'private, max-age=86400':'private, no-store'}});
}};\n`);
await writeFile('dist/.openai/hosting.json',await readFile('.openai/hosting.json'));
console.log(JSON.stringify({worker:'dist/server/index.js',assets:Object.keys(assets).length,seed_papers:corpus.papers.length,records:index.records.length}));
