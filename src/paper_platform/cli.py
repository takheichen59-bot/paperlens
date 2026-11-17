"""Offline-first CLI. Online arXiv access requires an explicit --online flag."""
import asyncio,json,tomllib
from datetime import datetime,timezone
from pathlib import Path
import typer
from contracts import *
from storage import Database
from fetchers import ArxivFetcher
from fetchers.arxiv import arxiv_ref
from pipeline import PaperPipeline
from extractors.composite import CompositeExtractor
from pipeline.batch import BatchRunner,BatchItem
from exports import export_results

app=typer.Typer(help='Materials PDF extraction: arXiv source, offline PDF processing.',no_args_is_help=True,add_completion=False)


class OfflineFetcher(BaseFetcher):
    def __init__(self,*,max_pdf_bytes=100*1024*1024):self.max_pdf_bytes=max_pdf_bytes
    async def search(self,query):raise ContractError(Stage.SEARCH,ErrorKind.NOT_FOUND,False)
    async def fetch(self,doi_or_id):raise ContractError(Stage.METADATA,ErrorKind.NOT_FOUND,False)
    async def download(self,meta,destination):raise ContractError(Stage.DOWNLOAD,ErrorKind.NOT_FOUND,False)
    async def aclose(self):pass


def manifest_items(path):
    data=json.loads(path.read_text(encoding='utf-8'))
    if type(data) is not list:raise ValueError('Manifest must be a list')
    items=[]
    for value in data:
        if type(value) is not dict or set(value)-{'reference','meta','pdf'} or not isinstance(value.get('reference'),str) or not value['reference'].strip():
            raise ValueError('Invalid manifest item')
        meta=PaperMeta.model_validate_json(json.dumps(value['meta'])) if value.get('meta') is not None else None
        pdf=value.get('pdf')
        if pdf is not None and not isinstance(pdf,str):raise ValueError('Invalid PDF path')
        local=(path.parent/pdf).resolve() if pdf else None
        items.append(BatchItem(value['reference'],meta,local))
    return tuple(items)


def failure(message):typer.echo(message,err=True)


async def execute(items,db_path,workdir,output,online,concurrency,batch_size,retry_failed,*,max_pdf_mib=100,methods_max_chars=3000):
    if not online and any(item.meta is None or item.local_pdf is None for item in items):
        raise ValueError('Offline mode requires metadata and local PDF paths')
    db_path.parent.mkdir(parents=True,exist_ok=True)
    fetcher=ArxivFetcher(max_pdf_bytes=max_pdf_mib*1024*1024) if online else OfflineFetcher(max_pdf_bytes=max_pdf_mib*1024*1024)
    try:
        with Database(db_path) as db:
            if retry_failed:
                selected=[]
                for item in items:
                    pid=item.meta.paper_id if item.meta else 'arxiv:'+arxiv_ref(item.reference)[0]
                    row=db.connection.execute('SELECT status FROM extraction_results WHERE paper_id=? ORDER BY updated_at DESC,rowid DESC LIMIT 1',(pid,)).fetchone()
                    if row is None or row['status']=='failed':selected.append(item)
                items=tuple(selected)
            pipeline=PaperPipeline(db,workdir,fetcher,extractor=CompositeExtractor(max_methods_chars=methods_max_chars))
            report=await BatchRunner(pipeline,concurrency=concurrency,batch_size=batch_size).run(items)
            exported=export_results(db,output)
            typer.echo(json.dumps({'submitted':report.submitted,'duplicates':report.duplicates,'success':report.succeeded,'partial':report.partial,'failed':report.failed,'skipped':report.skipped,'exported':exported.records,'results':str(exported.results_path)},ensure_ascii=False))
            return 3 if report.failed or report.partial or report.skipped else 0
    finally:await fetcher.aclose()


def limits_from_config(config,max_pdf_mib,methods_max_chars):
    data=tomllib.loads(config.read_text()) if config else {}
    if set(data)-{'download','extraction'}:raise ValueError('Unknown config section')
    download=data.get('download',{});extraction=data.get('extraction',{})
    if set(download)-{'max_pdf_mib'} or set(extraction)-{'methods_max_chars'}:raise ValueError('Unsupported config key')
    size=max_pdf_mib if max_pdf_mib is not None else download.get('max_pdf_mib',100)
    length=methods_max_chars if methods_max_chars is not None else extraction.get('methods_max_chars',3000)
    if any(type(v)is not int or v<1 for v in (size,length)):raise ValueError('Positive integer limits required')
    return size,length


def run_command(manifest,arxiv_id,pdf,title,db,workdir,output,online,concurrency,batch_size,retry_failed=False,*,config=None,max_pdf_mib=None,methods_max_chars=None):
    try:
        if manifest:
            if arxiv_id or pdf:raise ValueError('Choose a manifest or a single paper')
            items=manifest_items(manifest)
        else:
            if not arxiv_id:raise ValueError('Provide a manifest or arXiv ID')
            sid,v=arxiv_ref(arxiv_id)
            meta=None
            if pdf:
                meta=PaperMeta(paper_id='arxiv:'+sid,source_id=sid,doi=None,title=title or ('Imported arXiv paper '+sid),page_url='https://arxiv.org/abs/'+sid+(v or ''),pdf_url='https://arxiv.org/pdf/'+sid+(v or ''),version=v,fetched_at=datetime.now(timezone.utc))
            items=(BatchItem(arxiv_id,meta,pdf.resolve() if pdf else None),)
        size,length=limits_from_config(config,max_pdf_mib,methods_max_chars)
        code=asyncio.run(execute(items,db,workdir,output,online,concurrency,batch_size,retry_failed,max_pdf_mib=size,methods_max_chars=length))
    except ContractError as exc:
        failure(json.dumps(exc.to_dict()));raise typer.Exit(1)
    except (OSError,ValueError):
        failure('Input/configuration or file operation failed. Check the manifest, paths and offline metadata.');raise typer.Exit(1)
    except KeyboardInterrupt:
        failure('Interrupted. Rerun with the same database and workdir to resume.');raise typer.Exit(130)
    except Exception:
        failure('Internal operation failed; no input data displayed.');raise typer.Exit(1)
    raise typer.Exit(code)


@app.command('run')
def run(manifest:Path=typer.Option(None,'--manifest'),arxiv_id:str=typer.Option('','--arxiv-id'),
        pdf:Path=typer.Option(None,'--pdf'),title:str=typer.Option('','--title'),
        db:Path=typer.Option(Path('state.sqlite3'),'--db'),workdir:Path=typer.Option(Path('cache'),'--workdir'),
        output:Path=typer.Option(Path('output'),'--output'),online:bool=typer.Option(False,'--online'),
        concurrency:int=typer.Option(2,'--concurrency',min=1,max=8),batch_size:int=typer.Option(10,'--batch-size',min=1,max=1000),
        config:Path=typer.Option(None,'--config'),max_pdf_mib:int=typer.Option(None,'--max-pdf-mib',min=1),
        methods_max_chars:int=typer.Option(None,'--methods-max-chars',min=1)):
    """Process local PDFs or explicitly enable online arXiv access."""
    run_command(manifest,arxiv_id,pdf,title,db,workdir,output,online,concurrency,batch_size,config=config,max_pdf_mib=max_pdf_mib,methods_max_chars=methods_max_chars)


@app.command('resume')
def resume(manifest:Path=typer.Option(...,'--manifest'),db:Path=typer.Option(Path('state.sqlite3'),'--db'),
           workdir:Path=typer.Option(Path('cache'),'--workdir'),output:Path=typer.Option(Path('output'),'--output'),
           online:bool=typer.Option(False,'--online'),concurrency:int=typer.Option(2,'--concurrency',min=1,max=8),
           batch_size:int=typer.Option(10,'--batch-size',min=1,max=1000),
        config:Path=typer.Option(None,'--config'),max_pdf_mib:int=typer.Option(None,'--max-pdf-mib',min=1),
        methods_max_chars:int=typer.Option(None,'--methods-max-chars',min=1)):
    """Resume a manifest, reusing valid stage artifacts."""
    run_command(manifest,'',None,'',db,workdir,output,online,concurrency,batch_size,config=config,max_pdf_mib=max_pdf_mib,methods_max_chars=methods_max_chars)


@app.command('retry-failed')
def retry_failed(manifest:Path=typer.Option(...,'--manifest'),db:Path=typer.Option(Path('state.sqlite3'),'--db'),
           workdir:Path=typer.Option(Path('cache'),'--workdir'),output:Path=typer.Option(Path('output'),'--output'),
           online:bool=typer.Option(False,'--online'),concurrency:int=typer.Option(2,'--concurrency',min=1,max=8),
           batch_size:int=typer.Option(10,'--batch-size',min=1,max=1000),
        config:Path=typer.Option(None,'--config'),max_pdf_mib:int=typer.Option(None,'--max-pdf-mib',min=1),
        methods_max_chars:int=typer.Option(None,'--methods-max-chars',min=1)):
    """Retry manifest entries with failed or absent results; keep successes."""
    run_command(manifest,'',None,'',db,workdir,output,online,concurrency,batch_size,True,config=config,max_pdf_mib=max_pdf_mib,methods_max_chars=methods_max_chars)


@app.command('search')
def search(query:str,max_results:int=typer.Option(10,'--max-results',min=1,max=100),
           category:str=typer.Option('cond-mat.mtrl-sci','--category'),online:bool=typer.Option(False,'--online')):
    """Search arXiv metadata; network is opt-in."""
    if not online:failure('Search requires --online. Local manifest processing remains offline.');raise typer.Exit(1)
    async def operation():
        fetcher=ArxivFetcher()
        try:
            q=PaperQuery(input_type=InputType.QUERY,query_value=query,category=category or None,max_results=max_results,date_from=None,date_to=None)
            return await fetcher.search(q)
        finally:await fetcher.aclose()
    try:
        rows=asyncio.run(operation())
        for row in rows:typer.echo(row.model_dump_json())
    except Exception:failure('Scholarly search failed; no request details displayed.');raise typer.Exit(1)


@app.command('status')
def status(db:Path=typer.Option(Path('state.sqlite3'),'--db')):
    """Show persisted stage counts."""
    try:
        if not db.is_file():raise ValueError('Database missing')
        with Database(db) as database:
            counts=[dict(r) for r in database.connection.execute('SELECT stage,stage_status,count(*) AS count FROM tasks GROUP BY stage,stage_status ORDER BY stage,stage_status')]
            typer.echo(json.dumps(counts))
    except Exception:failure('Cannot read database status.');raise typer.Exit(1)


@app.command('export')
def export(db:Path=typer.Option(Path('state.sqlite3'),'--db'),output:Path=typer.Option(Path('output'),'--output')):
    """Regenerate validated results and failure/review JSONL snapshots."""
    try:
        if not db.is_file():raise ValueError('Database missing')
        with Database(db) as database:
            result=export_results(database,output);typer.echo(f'Exported {result.records} records to {result.results_path}')
    except Exception:failure('Export failed; previous completed files remain individually valid.');raise typer.Exit(1)
