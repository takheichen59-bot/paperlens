"""Bounded streaming PDF cache; atomic file publication and checksum checks."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import httpx
from contracts import *


class DownloadSizeLimit(ContractError):
    """Only this typed condition maps to skipped; no new contracts enum."""
    def __init__(self,limit_bytes,*,file_bytes=None,file_bytes_source='unknown',bytes_received=0):
        super().__init__(Stage.DOWNLOAD,ErrorKind.INVALID_DOWNLOAD,False)
        self.limit_bytes=limit_bytes;self.file_bytes=file_bytes
        self.file_bytes_source=file_bytes_source;self.bytes_received=bytes_received
    def audit(self):return {'status':'skipped','skipped_reason':'size_limit','limit_bytes':self.limit_bytes,
        'file_bytes':self.file_bytes,'file_bytes_source':self.file_bytes_source,'bytes_received':self.bytes_received}


def valid_pdf(path,limit):
    size=path.stat().st_size
    if not 5<size<=limit:return False
    with path.open('rb') as f:
        start=f.read(5);f.seek(max(0,size-1024));end=f.read()
    return start==b'%PDF-' and b'%%EOF' in end


def digest_file(path):
    h=sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
    return h.hexdigest()


async def download_pdf(fetcher,meta,destination):
    directory=Path(destination);directory.mkdir(parents=True,exist_ok=True)
    name=sha256((meta.paper_id+'|'+(meta.version or '')).encode()).hexdigest()
    path=directory/(name+'.pdf');checksum=directory/(name+'.sha256')
    temporary=directory/(name+'.'+uuid4().hex+'.part')
    sum_temp=temporary.with_suffix('.sum.part');response=None
    try:
        if path.exists() and checksum.exists() and valid_pdf(path,fetcher.max_pdf_bytes):
            digest=digest_file(path)
            if digest==checksum.read_text().strip():
                return DownloadArtifact(pdf_path=path,content_hash=digest,bytes=path.stat().st_size,downloaded_at=datetime.now(timezone.utc))
        response=await fetcher.policy.get(fetcher.client,meta.pdf_url,stage=Stage.DOWNLOAD,stream=True)
        length=response.headers.get('Content-Length')
        if length and int(length)>fetcher.max_pdf_bytes:raise DownloadSizeLimit(fetcher.max_pdf_bytes,file_bytes=int(length),file_bytes_source='content_length')
        size=0;h=sha256()
        with temporary.open('wb') as f:
            async for chunk in response.aiter_bytes():
                size+=len(chunk)
                if size>fetcher.max_pdf_bytes:raise DownloadSizeLimit(fetcher.max_pdf_bytes,file_bytes=int(length) if length else None,file_bytes_source='content_length' if length else 'unknown',bytes_received=size)
                h.update(chunk);f.write(chunk)
        if not valid_pdf(temporary,fetcher.max_pdf_bytes):raise ValueError('Not a PDF')
        digest=h.hexdigest();sum_temp.write_text(digest+'\n')
        temporary.replace(path);sum_temp.replace(checksum)
        return DownloadArtifact(pdf_path=path,content_hash=digest,bytes=size,downloaded_at=datetime.now(timezone.utc))
    except ContractError:raise
    except httpx.HTTPError as exc:
        raise ContractError(Stage.DOWNLOAD,ErrorKind.NETWORK_TIMEOUT,True,cause=exc) from exc
    except (OSError,ValueError) as exc:
        raise ContractError(Stage.DOWNLOAD,ErrorKind.INVALID_DOWNLOAD,False,cause=exc) from exc
    finally:
        if response is not None:await response.aclose()
        temporary.unlink(missing_ok=True);sum_temp.unlink(missing_ok=True)
