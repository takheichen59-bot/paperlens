"""One-paper orchestration; no batch scheduling or JSONL file writing."""
from datetime import datetime,timezone
from pathlib import Path
import inspect
from contracts import *
from storage import PaperRepository,ResultRepository,ErrorRepository,TaskRepository
from checkpoints import ResumeStore,fingerprint
from fetchers.pdf_download import digest_file,DownloadSizeLimit
from parsers.sections import StructuredPDFParser
from extractors.composite import CompositeExtractor,status_for
from extractors.common import result
from extractors.warning_policy import WarningClassificationError


class PaperPipeline:
    def __init__(self,db,root,fetcher,parser=None,extractor=None):
        self.db=db;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.fetcher=fetcher;self.parser=parser or StructuredPDFParser();self.extractor=extractor or CompositeExtractor()
        self.checkpoints=ResumeStore(db,self.root/'checkpoints');self.parse_executor=None
    async def _stage(self,meta,stage,config,model,operation,*,pdf_hash=None):
        cached=(self.checkpoints.load_parse(meta.paper_id,config,pdf_hash=pdf_hash,parser_version=self.parser.version)
                if stage==Stage.PARSE else self.checkpoints.load(meta.paper_id,stage,config,model))
        if cached is not None:return cached
        self.checkpoints.start(meta.paper_id,stage,config)
        try:
            value=operation()
            if inspect.isawaitable(value):value=await value
            if stage==Stage.PARSE:self.checkpoints.save_parse(meta.paper_id,config,*value)
            else:self.checkpoints.save(meta.paper_id,stage,config,value)
            self.checkpoints.finish(meta.paper_id,stage)
            return value
        except WarningClassificationError:
            # Preserve identity; the single-paper boundary owns failure persistence.
            raise
        except Exception as exc:
            error=exc if isinstance(exc,ContractError) else ContractError.from_exception(exc,stage=stage,error_kind=ErrorKind.PARSE_FAILED if stage==Stage.PARSE else ErrorKind.EXTRACT_FAILED if stage==Stage.EXTRACT else ErrorKind.INVALID_DOWNLOAD,retryable=False)
            self.checkpoints.finish(meta.paper_id,stage,error=error,skipped=isinstance(error,DownloadSizeLimit))
            raise error
    def _record(self,meta,extraction,reference=''):
        value={'doi':meta.doi if meta else None,'title':meta.title if meta else reference,
               'source_url':meta.page_url if meta else '',
               **{k:extraction.model_dump(mode='json')[k] for k in ('chemicals','conclusions','methods','extraction_method','source_snippets')},
               'status':status_for(extraction).value}
        checked=validate_record(value)
        if not checked.valid:raise ContractError(Stage.VALIDATE,ErrorKind.VALIDATION_FAILED,False)
        return checked.record
    async def _parse(self,path,meta):
        if self.parse_executor is None:value=self.parser.parse_with_view(path)
        else:
            import asyncio
            value=await asyncio.get_running_loop().run_in_executor(self.parse_executor,self.parser.parse_with_view,path)
        paper,view=value
        return paper.model_copy(update={'paper_id':meta.paper_id}),view
    def _handle_warning_classification_error(self,task,exc:WarningClassificationError)->None:
        failed=result(method=self.extractor.version,warnings=('operation_failed','warning_classification_error'))
        with self.db.transaction():
            self.checkpoints.finish(task.paper_id,task.stage,error=exc)
            ErrorRepository(self.db).append(exc,paper_id=task.paper_id)
            ResultRepository(self.db).upsert(task.paper_id,failed,status=ResultStatus.FAILED)
    async def run(self,doi_or_id,*,meta=None,local_pdf=None):
        paper=None
        try:
            paper=meta if meta is not None else await self.fetcher.fetch(doi_or_id)
            paper,_=PaperRepository(self.db).upsert(paper,source=Source.ARXIV)
            local=Path(local_pdf) if local_pdf is not None else None
            limit=getattr(self.fetcher,'max_pdf_bytes',100*1024*1024)
            config=fingerprint('download-v2',paper.paper_id,paper.version,paper.pdf_url,limit,digest_file(local) if local else None)
            async def download():
                if local is None:return await self.fetcher.download(paper,self.root/'pdfs')
                if local.stat().st_size>limit:raise DownloadSizeLimit(limit,file_bytes=local.stat().st_size,file_bytes_source='filesystem')
                return DownloadArtifact(pdf_path=local.resolve(),content_hash=digest_file(local),bytes=local.stat().st_size,downloaded_at=datetime.now(timezone.utc))
            artifact=await self._stage(paper,Stage.DOWNLOAD,config,DownloadArtifact,download)
            parse_config=fingerprint(artifact.content_hash,self.parser.version)
            parsed,view=await self._stage(paper,Stage.PARSE,parse_config,ParsedPaper,lambda:self._parse(artifact.pdf_path,paper),pdf_hash=artifact.content_hash)
            extract_config=fingerprint(parsed.model_dump_json(),view.to_dict(),self.extractor.version)
            extraction=await self._stage(paper,Stage.EXTRACT,extract_config,ExtractionResult,lambda:self.extractor.with_view(view).extract(parsed))
            record=self._record(paper,extraction)
            ResultRepository(self.db).upsert(paper.paper_id,extraction,status=record.status)
            return record
        except DownloadSizeLimit as exc:
            from exports.jsonl import save_skip_info
            save_skip_info(self.db,paper.paper_id,exc.audit())
            raise
        except WarningClassificationError as exc:
            task=TaskRepository(self.db).get_current(paper.paper_id,Stage.EXTRACT)
            self._handle_warning_classification_error(task,exc)
            failed=result(method=self.extractor.version,warnings=('operation_failed','warning_classification_error'))
            return self._record(paper,failed,doi_or_id)
        except Exception as exc:
            error=exc if isinstance(exc,ContractError) else ContractError.from_exception(exc,stage=Stage.METADATA)
            ErrorRepository(self.db).append(error,paper_id=paper.paper_id if paper else None)
            failed=result(method=self.extractor.version,warnings=('operation_failed',))
            if paper:ResultRepository(self.db).upsert(paper.paper_id,failed,status=ResultStatus.FAILED)
            return self._record(paper,failed,doi_or_id)
