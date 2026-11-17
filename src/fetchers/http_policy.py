"""Shared source pacing and bounded retry policy; injectable clock for tests."""
import asyncio
import time
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import httpx
from contracts import ContractError,Stage,ErrorKind


class HttpPolicy:
    def __init__(self,*,interval=3.0,retries=2,clock=time.monotonic,sleep=asyncio.sleep):
        if interval<0 or retries<0:raise ValueError('Invalid HTTP policy')
        self.interval=interval;self.retries=retries;self.clock=clock;self.sleep=sleep
        self._lock=asyncio.Lock();self._last=None
    async def pace(self):
        async with self._lock:
            if self._last is not None:
                delay=self.interval-(self.clock()-self._last)
                if delay>0:await self.sleep(delay)
            self._last=self.clock()
    def retry_after(self,response,attempt):
        raw=response.headers.get('Retry-After','')
        try:return max(0,float(raw))
        except ValueError:
            try:return max(0,(parsedate_to_datetime(raw)-datetime.now(timezone.utc)).total_seconds())
            except (ValueError,TypeError,OverflowError):return min(2**attempt,60)
    async def get(self,client,url,*,stage=Stage.METADATA,stream=False,**kwargs):
        for attempt in range(self.retries+1):
            await self.pace()
            try:
                if stream:
                    r=await client.send(client.build_request("GET",url,**kwargs),stream=True)
                else:
                    r=await client.get(url,**kwargs)
            except httpx.TimeoutException as exc:
                if attempt<self.retries:await self.sleep(min(2**attempt,60));continue
                raise ContractError(stage,ErrorKind.NETWORK_TIMEOUT,True,cause=exc) from exc
            except httpx.RequestError as exc:
                if attempt<self.retries:await self.sleep(min(2**attempt,60));continue
                raise ContractError(stage,ErrorKind.UNKNOWN,True,cause=exc) from exc
            if r.is_success:return r
            retry=r.status_code==429 or 500<=r.status_code<600
            if retry and attempt<self.retries:
                delay=self.retry_after(r,attempt);await r.aclose();await self.sleep(delay);continue
            kind=ErrorKind.NOT_FOUND if r.status_code==404 else ErrorKind.RATE_LIMITED if r.status_code==429 else ErrorKind.UNKNOWN
            await r.aclose()
            raise ContractError(stage,kind,retry)
