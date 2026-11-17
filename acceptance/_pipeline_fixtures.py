"""Single-source offline adapter using synthetic local PDF bytes."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from contracts import *


def metadata(index=1):
    sid=f'2401.{index:05d}'
    return PaperMeta(paper_id='arxiv:'+sid,source_id=sid,doi=None,title=f'Synthetic fixture {index}; not a real paper',
        page_url='https://arxiv.org/abs/'+sid,pdf_url='https://arxiv.org/pdf/'+sid,version='v1',fetched_at=datetime(2024,1,1,tzinfo=timezone.utc))


class LocalFetcher(BaseFetcher):
    def __init__(self,paths=None,*,fail=False):self.paths=paths or {};self.fail=fail;self.downloads=0
    async def search(self,query):return tuple(PaperRef(source=Source.ARXIV,source_id=metadata(i).source_id,version='v1') for i in self.paths)
    async def fetch(self,doi_or_id):
        return metadata(int(doi_or_id.rsplit('.',1)[-1]))
    async def download(self,meta,destination):
        self.downloads+=1
        if self.fail:raise ContractError(Stage.DOWNLOAD,ErrorKind.NETWORK_TIMEOUT,True)
        path=Path(self.paths[int(meta.source_id.rsplit('.',1)[-1])])
        return DownloadArtifact(pdf_path=path,content_hash=sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,downloaded_at=datetime.now(timezone.utc))
    async def aclose(self):pass
