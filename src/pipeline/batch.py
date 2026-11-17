"""Bounded asynchronous batches; SQLite writes stay in the owning event loop."""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime,timezone
from contracts import *
from storage import ErrorRepository
from fetchers.pdf_download import DownloadSizeLimit
from .single import PaperPipeline
from parsers.sections import StructuredPDFParser


@dataclass(frozen=True)
class BatchItem:
    reference:str
    meta:PaperMeta|None=None
    local_pdf:object=None


@dataclass(frozen=True)
class BatchReport:
    records:tuple[JSONLRecord,...]
    submitted:int
    duplicates:int
    skipped_items:tuple=()
    @property
    def skipped(self):return len(self.skipped_items)
    @property
    def succeeded(self):return sum(r.status==ResultStatus.SUCCESS for r in self.records)
    @property
    def partial(self):return sum(r.status==ResultStatus.PARTIAL for r in self.records)
    @property
    def failed(self):return sum(r.status==ResultStatus.FAILED for r in self.records)


class BatchRunner:
    def __init__(self,pipeline,*,concurrency=2,batch_size=10):
        if type(concurrency) is not int or concurrency<1 or type(batch_size) is not int or batch_size<1:raise ValueError('Positive batch limits required')
        self.pipeline=pipeline;self.concurrency=concurrency;self.batch_size=batch_size
    async def run(self,items):
        queue=asyncio.Queue(maxsize=self.concurrency*self.batch_size)
        submitted=0;duplicates=0;seen=set();results=[];skipped=[];executor=None
        if isinstance(self.pipeline,PaperPipeline):
            self.pipeline.checkpoints.recover(before=datetime.now(timezone.utc))
            if isinstance(self.pipeline.parser,StructuredPDFParser) and self.pipeline.parse_executor is None:
                executor=ProcessPoolExecutor(max_workers=1);self.pipeline.parse_executor=executor
        async def producer():
            nonlocal submitted
            if hasattr(items,'__aiter__'):
                async for item in items:
                    await queue.put((submitted,item));submitted+=1
            else:
                for item in items:
                    await queue.put((submitted,item));submitted+=1
            for _ in range(self.concurrency):await queue.put((None,None))
        async def worker():
            nonlocal duplicates
            while True:
                index,item=await queue.get()
                try:
                    if item is None:return
                    meta=item.meta if item.meta is not None else await self.pipeline.fetcher.fetch(item.reference)
                    key=meta.paper_id
                    if key in seen:duplicates+=1;continue
                    seen.add(key)
                    record=await self.pipeline.run(item.reference,meta=meta,local_pdf=item.local_pdf)
                    results.append((index,record))
                except DownloadSizeLimit as exc:
                    skipped.append((meta.paper_id,exc.audit()))
                except Exception as exc:
                    error=exc if isinstance(exc,ContractError) else ContractError.from_exception(exc,stage=Stage.METADATA)
                    if hasattr(self.pipeline,'db'):ErrorRepository(self.pipeline.db).append(error)
                    method=getattr(getattr(self.pipeline,'extractor',None),'version','batch-v1')
                    checked=validate_record({'doi':None,'title':item.reference,'source_url':'','chemicals':[],
                        'conclusions':'','methods':'','extraction_method':method,'source_snippets':[],'status':'failed'})
                    results.append((index,checked.record))
                finally:queue.task_done()
        workers=[asyncio.create_task(worker()) for _ in range(self.concurrency)]
        feed=asyncio.create_task(producer())
        try:
            await asyncio.gather(feed,*workers)
            return BatchReport(tuple(record for _,record in sorted(results)),submitted,duplicates,tuple(skipped))
        finally:
            feed.cancel()
            for worker in workers:worker.cancel()
            await asyncio.gather(feed,*workers,return_exceptions=True)
            if executor:
                executor.shutdown(wait=True,cancel_futures=True);self.pipeline.parse_executor=None
