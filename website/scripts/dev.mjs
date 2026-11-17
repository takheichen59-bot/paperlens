// Managed-preview adapter only. Production uses the native R2 binding.
import http from 'node:http';
import {readFile,writeFile,mkdir,readdir,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root='work/preview-objects';await mkdir(root,{recursive:true});
const file=key=>root+'/'+Buffer.from(key).toString('base64url');
const read=async key=>{try{return await readFile(file(key));}catch(e){if(e.code==='ENOENT')return null;throw e;}};
const etag=data=>createHash('sha256').update(data).digest('hex');
const bucket={
 async get(key){const bytes=await read(key);return bytes?{size:bytes.length,etag:etag(bytes),text:async()=>bytes.toString(),arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),body:new Blob([bytes]).stream()}:null;},
 async head(key){const bytes=await read(key);return bytes?{size:bytes.length,etag:etag(bytes)}:null;},
 async put(key,value,options={}){const prior=await read(key),condition=options.onlyIf;if(condition?.etagMatches&&(!prior||etag(prior)!==condition.etagMatches))return null;if(condition?.etagDoesNotMatch==='*'&&prior)return null;const bytes=typeof value==='string'?Buffer.from(value):Buffer.from(value);await writeFile(file(key),bytes);return {etag:etag(bytes),size:bytes.length};},
 async list({prefix='',limit=20,cursor}={}){const names=(await readdir(root)).map(x=>Buffer.from(x,'base64url').toString()).filter(x=>x.startsWith(prefix)).sort(),start=Number(cursor||0);const objects=[];for(const key of names.slice(start,start+limit)){const bytes=await read(key);objects.push({key,size:bytes.length,etag:etag(bytes)});}return {objects,truncated:start+limit<names.length,cursor:String(start+limit)};}
};
let worker,loaded=0;
const server=http.createServer(async(req,res)=>{try{
 const changed=(await stat('dist/server/index.js')).mtimeMs;if(changed!==loaded){worker=(await import(pathToFileURL(process.cwd()+'/dist/server/index.js')+'?v='+changed)).default;loaded=changed;}
 const chunks=[];for await(const chunk of req)chunks.push(chunk);
 const protocol=req.headers['x-forwarded-proto']||'http',host=req.headers['x-forwarded-host']||req.headers.host;
 const init={method:req.method,headers:req.headers};if(chunks.length)init.body=Buffer.concat(chunks);
 const response=await worker.fetch(new Request(protocol+'://'+host+req.url,init),{BUCKET:bucket},{});
 res.writeHead(response.status,Object.fromEntries(response.headers));if(response.body)for await(const bytes of response.body)res.write(bytes);res.end();
}catch(error){console.error('Preview request failed:',error.message);res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Preview request failed'}));}});
const argumentsList=process.argv.slice(2),argument=name=>{const i=argumentsList.indexOf(name);return i<0?null:argumentsList[i+1];};
const port=Number(argument('--port')||process.env.PORT||3000),host=argument('--host')||'0.0.0.0';server.listen(port,host,()=>console.log('PaperLens preview listening on '+host+':'+port));
