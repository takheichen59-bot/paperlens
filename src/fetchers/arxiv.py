"""Single-source arXiv metadata adapter; HTTP transport is injectable."""
from datetime import datetime,timezone
from pathlib import Path
import re
from urllib.parse import urlsplit
import feedparser
import httpx
from .http_policy import HttpPolicy
from contracts import *


def arxiv_ref(value):
    if value.startswith(('http://','https://')):
        url=urlsplit(value)
        if url.hostname not in {'arxiv.org','www.arxiv.org','export.arxiv.org'}:raise ValueError('Not an arXiv URL')
        value=url.path.removeprefix('/abs/').removeprefix('/pdf/').removesuffix('.pdf')
    match=re.fullmatch(r'((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7}))(v\d+)?',value)
    if not match:raise ValueError('Invalid arXiv identifier')
    return match[1],match[2]


class ArxivFetcher(BaseFetcher):
    endpoint='https://export.arxiv.org/api/query'
    def __init__(self,client=None,*,policy=None,max_pdf_bytes=100*1024*1024):
        self.client=client or httpx.AsyncClient(timeout=30,follow_redirects=True)
        self._owned=client is None
        self.policy=policy or HttpPolicy()
        self.max_pdf_bytes=max_pdf_bytes
    async def _get(self,url,**kwargs):
        return await self.policy.get(self.client,url,**kwargs)
    def _parse(self,content):
        parsed=feedparser.parse(content)
        if parsed.bozo or parsed.get('version')!='atom10':
            raise ContractError(Stage.METADATA,ErrorKind.VALIDATION_FAILED,False)
        result=[]
        try:
            for entry in parsed.entries:
                sid,version=arxiv_ref(entry.id)
                suffix=version or ''
                result.append(PaperMeta(paper_id='arxiv:'+sid,source_id=sid,
                    doi=entry.get('arxiv_doi') or None,title=' '.join(entry.title.split()),
                    page_url='https://arxiv.org/abs/'+sid+suffix,
                    pdf_url='https://arxiv.org/pdf/'+sid+suffix,
                    version=version,fetched_at=datetime.now(timezone.utc)))
        except (ValueError,AttributeError) as exc:
            raise ContractError(Stage.METADATA,ErrorKind.VALIDATION_FAILED,False,cause=exc) from exc
        return tuple(result)
    async def search(self,query:PaperQuery):
        params={'max_results':str(query.max_results),'start':'0'}
        if query.input_type in {InputType.ARXIV_ID,InputType.ARXIV_URL}:
            sid,v=arxiv_ref(query.query_value);params['id_list']=sid+(v or '')
        else:
            value=query.query_value.replace('"',' ')
            expression=('doi:"'+value+'"') if query.input_type==InputType.DOI else 'all:"'+value+'"'
            if query.category:
                if not re.fullmatch(r'[a-zA-Z0-9.-]+',query.category):raise ValueError('Invalid category')
                expression+=' AND cat:'+query.category
            if query.date_from or query.date_to:
                lo=query.date_from.strftime('%Y%m%d')+'0000' if query.date_from else '199101010000'
                hi=query.date_to.strftime('%Y%m%d')+'2359' if query.date_to else '999912312359'
                expression+=f' AND submittedDate:[{lo} TO {hi}]'
            params['search_query']=expression
        rows=self._parse((await self._get(self.endpoint,params=params)).content)
        return tuple(PaperRef(source=Source.ARXIV,source_id=m.source_id,version=m.version) for m in rows[:query.max_results])
    async def fetch(self,doi_or_id:str):
        if re.fullmatch(r'10\.\d{4,9}/\S+',doi_or_id,re.I):
            params={'search_query':'doi:"'+doi_or_id+'"','max_results':'2'}
            rows=tuple(m for m in self._parse((await self._get(self.endpoint,params=params)).content) if m.doi==doi_or_id.lower())
        else:
            sid,v=arxiv_ref(doi_or_id)
            params={'id_list':sid+(v or ''),'max_results':'2'}
            rows=tuple(m for m in self._parse((await self._get(self.endpoint,params=params)).content) if m.source_id==sid and (v is None or m.version==v))
        if not rows:raise ContractError(Stage.METADATA,ErrorKind.NOT_FOUND,False)
        if len(rows)>1:raise ContractError(Stage.METADATA,ErrorKind.AMBIGUOUS_INPUT,False)
        return rows[0]
    async def download(self,meta:PaperMeta,destination:Path):
        from .pdf_download import download_pdf
        return await download_pdf(self,meta,destination)
    async def aclose(self):
        if self._owned:await self.client.aclose()
