import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,httpx
from fetchers import ArxivFetcher
from fetchers.http_policy import HttpPolicy
from contracts import *

def atom(entries):
    return '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">'+''.join('<entry><id>https://arxiv.org/abs/'+sid+'</id><title>'+title+'</title>'+('<arxiv:doi>'+doi+'</arxiv:doi>' if doi else '')+'</entry>' for sid,title,doi in entries)+'</feed>'
async def using(entries,op):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text=atom(entries)))) as client:
        return await op(ArxivFetcher(client,policy=HttpPolicy(interval=0,retries=0)))
def case_keyword():
    rows=asyncio.run(using([('2401.00001v1','One',None),('2401.00002v2','Two','10.1234/test')],lambda f:f.search(PaperQuery(input_type=InputType.QUERY,query_value='materials',category='cond-mat.mtrl-sci',max_results=2,date_from=None,date_to=None))))
    assert [r.source_id for r in rows]==['2401.00001','2401.00002']
def case_id():
    m=asyncio.run(using([('2401.00001v1','One',None)],lambda f:f.fetch('2401.00001v1')))
    assert m.doi is None and m.version=='v1' and m.paper_id=='arxiv:2401.00001'
def case_url():
    m=asyncio.run(using([('2401.00001v1','One',None)],lambda f:f.fetch('https://arxiv.org/abs/2401.00001v1')))
    assert m.pdf_url=='https://arxiv.org/pdf/2401.00001v1'
def case_doi_missing():
    try:asyncio.run(using([],lambda f:f.fetch('10.1234/absent')))
    except ContractError as e:assert e.error_kind==ErrorKind.NOT_FOUND
    else:raise AssertionError('missing accepted')
def case_invalid_and_ambiguous():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,text='broken'))) as client:
            try:await ArxivFetcher(client,policy=HttpPolicy(interval=0,retries=0)).fetch('2401.00001')
            except ContractError as e:assert e.error_kind==ErrorKind.VALIDATION_FAILED
            else:raise AssertionError('bad XML accepted')
        try:await using([('2401.00001v1','One',None),('2401.00001v2','Two',None)],lambda f:f.fetch('2401.00001'))
        except ContractError as e:assert e.error_kind==ErrorKind.AMBIGUOUS_INPUT
        else:raise AssertionError('ambiguous accepted')
    asyncio.run(run())

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_keyword', 'case_id', 'case_url', 'case_doi_missing', 'case_invalid_and_ambiguous'], globals()))
