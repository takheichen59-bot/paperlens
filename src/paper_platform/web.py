"""Loopback browser UI for the unchanged Python pipeline; no cloud PDF upload."""
import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse,parse_qs
from uuid import uuid4
import webbrowser

from contracts import *
from storage import Database,PaperRepository
from fetchers import ArxivFetcher
from fetchers.arxiv import arxiv_ref
from fetchers.pdf_download import DownloadSizeLimit
from extractors.composite import CompositeExtractor
from pipeline import PaperPipeline
from checkpoints import ResumeStore,fingerprint
from exports import (export_results,open_current_snapshot,read_current_results,
    read_current_warnings_by_severity,read_current_failures,read_current_review)
from exports.jsonl import save_skip_info
from .cli import OfflineFetcher

ASSETS=Path(__file__).with_name('web_assets')


class WebEngine:
    def __init__(self,root,*,online=False,max_pdf_mib=100,methods_max_chars=3000):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.online=online;self.limit=max_pdf_mib*1024*1024;self.methods_max_chars=methods_max_chars
        self.lock=Lock();self.output=self.root/'results'
    def metadata(self,params):
        sid,version=arxiv_ref(params.get('arxiv_id',[''])[0])
        return PaperMeta(paper_id='arxiv:'+sid,source_id=sid,doi=params.get('doi',[None])[0] or None,
            title=params.get('title',['Imported arXiv paper '+sid])[0] or 'Imported arXiv paper '+sid,
            page_url='https://arxiv.org/abs/'+sid+(version or ''),pdf_url='https://arxiv.org/pdf/'+sid+(version or ''),
            version=version,fetched_at=datetime.now(timezone.utc))
    def reject_size(self,meta,size):
        with self.lock,Database(self.root/'state.sqlite3') as db:
            PaperRepository(db).upsert(meta,source=Source.ARXIV)
            store=ResumeStore(db,self.root/'cache/checkpoints')
            store.start(meta.paper_id,Stage.DOWNLOAD,fingerprint(meta.paper_id,'web-size',self.limit))
            error=DownloadSizeLimit(self.limit,file_bytes=size,file_bytes_source='content_length')
            store.finish(meta.paper_id,Stage.DOWNLOAD,error=error,skipped=True)
            save_skip_info(db,meta.paper_id,error.audit());export_results(db,self.output)
            return error.audit()
    def extract(self,meta,path):
        with self.lock,Database(self.root/'state.sqlite3') as db:
            pipeline=PaperPipeline(db,self.root/'cache',OfflineFetcher(max_pdf_bytes=self.limit),
                extractor=CompositeExtractor(max_methods_chars=self.methods_max_chars))
            record=asyncio.run(pipeline.run(meta.source_id,meta=meta,local_pdf=path))
            return self.response(db,meta,record)
    def response(self,db,meta,record):
        export_results(db,self.output)
        with open_current_snapshot(self.output) as snapshot:
            messages=next(w for w in read_current_warnings_by_severity(self.output,snapshot=snapshot) if w.paper_id==meta.paper_id)
            return {'record':record.model_dump(mode='json'),'warnings':asdict(messages),
                'version_id':snapshot.version_id,'published_at':snapshot.published_at,'engine':'python'}
    async def process(self,reference):
        fetcher=ArxivFetcher(max_pdf_bytes=self.limit)
        try:
            meta=await fetcher.fetch(reference)
            with self.lock,Database(self.root/'state.sqlite3') as db:
                pipeline=PaperPipeline(db,self.root/'cache',fetcher,extractor=CompositeExtractor(max_methods_chars=self.methods_max_chars))
                try:record=await pipeline.run(reference,meta=meta)
                except DownloadSizeLimit as exc:
                    export_results(db,self.output);return exc.audit()
                return self.response(db,meta,record)
        finally:await fetcher.aclose()
    async def search(self,query):
        fetcher=ArxivFetcher()
        try:
            q=query.strip()
            if not q:return {'items':[],'total':0}
            if len(q)>500:raise ValueError('Query too long')
            try:arxiv_ref(q);is_id=True
            except (ContractError,ValueError):is_id=False
            refs=(PaperRef(source=Source.ARXIV,source_id=arxiv_ref(q)[0],version=arxiv_ref(q)[1]),) if is_id else await fetcher.search(PaperQuery(
                input_type=InputType.QUERY,query_value=q,category=None,max_results=12,date_from=None,date_to=None))
            items=[]
            for ref in refs:
                meta=await fetcher.fetch(ref.source_id+(ref.version or ''))
                items.append({'id':meta.source_id+(meta.version or ''),'doi':meta.doi,'title':meta.title,
                    'url':meta.page_url,'pdf_url':meta.pdf_url,'authors':'arXiv','abstract':'','year':None})
            return {'items':items,'total':len(items)}
        finally:await fetcher.aclose()


def handler_for(engine):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Never log paper text, query bodies or headers.
        def send(self,value,status=200,content_type='application/json; charset=utf-8'):
            body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            url=urlparse(self.path)
            try:
                if url.path=='/api/status':return self.send({'engine':'python','version':'0.1.2','online':engine.online,'max_pdf_mib':engine.limit//1024//1024})
                if url.path=='/api/search':
                    if not engine.online:return self.send({'error':'本地在线检索未开启；使用 paperlens-web --online，或直接上传 PDF。'},403)
                    return self.send(asyncio.run(engine.search(parse_qs(url.query).get('q',[''])[0])))
                if url.path=='/api/results':
                    if not (engine.output/'CURRENT').exists():return self.send({'papers':[]})
                    with open_current_snapshot(engine.output) as s:
                        rows=read_current_results(engine.output,snapshot=s)
                        warnings={w.paper_id:asdict(w) for w in read_current_warnings_by_severity(engine.output,snapshot=s)}
                        return self.send({'papers':[{'id':r.source_url.rsplit('/',1)[-1],'title':r.title,'url':r.source_url,'doi':r.doi,'record':r.model_dump(mode='json'),'status':r.status.value,'warnings':warnings[ident[0]]} for ident,r in zip(s.results_index,rows)],'version_id':s.version_id})
                if url.path.startswith('/api/export/'):
                    name=url.path.rsplit('/',1)[1]
                    readers={'results':read_current_results,'warnings':read_current_warnings_by_severity,'failures':read_current_failures,'review':read_current_review}
                    if name not in readers:return self.send({'error':'Not found'},404)
                    with open_current_snapshot(engine.output) as s:
                        rows=readers[name](engine.output,snapshot=s)
                        values=[r.model_dump(mode='json') if hasattr(r,'model_dump') else asdict(r) if hasattr(r,'__dataclass_fields__') else r for r in rows]
                    return self.send((''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in values)).encode(),content_type='application/x-ndjson; charset=utf-8')
                name='index.html' if url.path=='/' else url.path.removeprefix('/')
                if name not in {'index.html','app.js','style.css','preview.js','policy.json','corpus.json'}:return self.send({'error':'Not found'},404)
                path=ASSETS/name
                mime='text/html; charset=utf-8' if name.endswith('.html') else 'text/css; charset=utf-8' if name.endswith('.css') else 'text/javascript; charset=utf-8' if name.endswith('.js') else 'application/json; charset=utf-8'
                return self.send(path.read_bytes(),content_type=mime)
            except (OSError,ValueError,ContractError):return self.send({'error':'请求或来源不可用，请核对 arXiv ID、输入和网络。'},400)
        def do_POST(self):
            if urlparse(self.path).path=='/api/process':
                if not engine.online:return self.send({'error':'在线处理未开启；使用 paperlens-web --online。'},403)
                try:return self.send(asyncio.run(engine.process(parse_qs(urlparse(self.path).query).get('arxiv_id',[''])[0])))
                except (OSError,ValueError,ContractError):return self.send({'error':'arXiv 来源暂不可用。'},502)
            if urlparse(self.path).path!='/api/extract':return self.send({'error':'Not found'},404)
            try:
                meta=engine.metadata(parse_qs(urlparse(self.path).query))
                size=int(self.headers.get('Content-Length','0'))
                if size<=0:return self.send({'error':'请选择非空 PDF。'},400)
                if size>engine.limit:return self.send(engine.reject_size(meta,size),413)
                if self.headers.get('Content-Type','').split(';')[0]!='application/pdf':return self.send({'error':'仅接受 application/pdf。'},415)
                incoming=engine.root/'incoming';incoming.mkdir(exist_ok=True)
                path=incoming/(uuid4().hex+'.pdf');remaining=size
                with path.open('xb') as f:
                    while remaining:
                        chunk=self.rfile.read(min(1024*1024,remaining))
                        if not chunk:raise ValueError('Incomplete upload')
                        f.write(chunk);remaining-=len(chunk)
                return self.send(engine.extract(meta,path))
            except (OSError,ValueError,ContractError):return self.send({'error':'PDF 或元信息不可用，请核对输入。'},400)
    return Handler


def main():
    parser=argparse.ArgumentParser(description='MatterLens 本地浏览器工作台：原文在本机由 Python 处理。')
    parser.add_argument('--port',type=int,default=8765);parser.add_argument('--workdir',type=Path,default=Path('work/paperlens-web'))
    parser.add_argument('--online',action='store_true');parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--max-pdf-mib',type=int,default=100);parser.add_argument('--methods-max-chars',type=int,default=3000)
    args=parser.parse_args()
    if min(args.port,args.max_pdf_mib,args.methods_max_chars)<1 or args.port>65535:parser.error('Positive limits and valid port required')
    engine=WebEngine(args.workdir,online=args.online,max_pdf_mib=args.max_pdf_mib,methods_max_chars=args.methods_max_chars)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(engine))
    url=f'http://127.0.0.1:{args.port}/';print(url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
