import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import asyncio,httpx
from fetchers.http_policy import HttpPolicy
from contracts import *
class Clock:
    def __init__(self):self.now=0.;self.delays=[]
    def time(self):return self.now
    async def sleep(self,n):self.delays.append(n);self.now+=n
async def request(responses):
    clock=Clock();calls=[]
    def handle(r):
        calls.append(clock.now);value=responses[min(len(calls)-1,len(responses)-1)]
        if isinstance(value,Exception):raise value
        return value
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        policy=HttpPolicy(interval=3,retries=2,clock=clock.time,sleep=clock.sleep)
        response=await policy.get(client,'https://example.org')
    return response,calls,clock

def case_pacing():
    async def run():
        c=Clock();times=[]
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:(times.append(c.now) or httpx.Response(200)))) as client:
            p=HttpPolicy(interval=3,clock=c.time,sleep=c.sleep)
            await asyncio.gather(*(p.get(client,'https://example.org') for _ in range(3)))
        assert times==[0,3,6]
    asyncio.run(run())
def case_rate_limit():
    r,calls,c=asyncio.run(request([httpx.Response(429,headers={'Retry-After':'7'}),httpx.Response(200)]))
    assert calls==[0,7] and 7 in c.delays
def case_service_retry():
    _,calls,_=asyncio.run(request([httpx.Response(503),httpx.Response(200)]));assert len(calls)==2
def case_timeout_budget():
    async def run():
        count=0
        def handle(r):
            nonlocal count;count+=1;raise httpx.ReadTimeout('private request')
        c=Clock()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            try:await HttpPolicy(interval=0,retries=2,clock=c.time,sleep=c.sleep).get(client,'https://example.org')
            except ContractError as e:assert e.error_kind==ErrorKind.NETWORK_TIMEOUT and count==3
            else:raise AssertionError('timeout passed')
    asyncio.run(run())
def case_permanent_and_cancel():
    async def run():
        count=0
        def handle(r):
            nonlocal count;count+=1;return httpx.Response(404)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            try:await HttpPolicy(interval=0).get(client,'https://example.org')
            except ContractError as e:assert e.error_kind==ErrorKind.NOT_FOUND and count==1
            else:raise AssertionError('404 passed')
        async def cancel(n):raise asyncio.CancelledError()
        p=HttpPolicy(interval=3,sleep=cancel);await p.pace()
        try:await p.pace()
        except asyncio.CancelledError:pass
        else:raise AssertionError('cancellation swallowed')
    asyncio.run(run())

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_pacing', 'case_rate_limit', 'case_service_retry', 'case_timeout_budget', 'case_permanent_and_cancel'], globals()))
