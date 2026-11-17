"""Opt-in real upstream/browser smoke test, separate from deterministic fixture CI.
Searches Crossref; independently downloads a known arXiv paper with a recorded CC
license. A search result is not presented as proof it supplied that known paper.
"""
import argparse,hashlib,json,os,socket,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))

def main():
 import httpx
 from playwright.sync_api import sync_playwright,expect
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('work/browser-live'));p.add_argument('--browser',default=os.getenv('CHROMIUM_EXECUTABLE'));a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);meta=json.loads((ROOT/'samples/browser/real_paper.json').read_text());result={'scope':'REAL_UPSTREAM_AND_REAL_PDF_BROWSER_SMOKE','checks':[],'real_llm':'NOT_EXECUTED','scientific_accuracy':'NOT_EVALUATED'}
 with tempfile.TemporaryDirectory(prefix='paperlens-live-') as tmp:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  env={k:v for k,v in os.environ.items() if not k.startswith(('LLM_','OPENAI_','EMBEDDING_','GROBID_','DOCLING_','PAPERLENS_'))};env['PYTHONPATH']=str(ROOT/'src');url=f'http://127.0.0.1:{port}';log=(out/'server.log').open('w');proc=subprocess.Popen([sys.executable,'-m','science_platform','serve','--data',tmp,'--port',str(port)],cwd=tmp,env=env,stdout=log,stderr=log)
  try:
   deadline=time.monotonic()+30
   while True:
    try:
     if httpx.get(url+'/api/v1/health').status_code==200:break
    except httpx.HTTPError:pass
    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Server unavailable')
    time.sleep(.1)
   with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox']}
    if a.browser:options['executable_path']=a.browser
    browser=pw.chromium.launch(**options);context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=context.new_page();page.set_default_timeout(15000)
    def wait_job(jid,timeout=180):
     end=time.monotonic()+timeout
     while time.monotonic()<end:
      j=context.request.get(url+'/api/v1/jobs/'+jid).json()
      if j['status'] in {'COMPLETED','FAILED'}:return j
      time.sleep(.4)
     raise AssertionError('Job timed out')
    def passed(name):result['checks'].append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
    page.goto(url+'/#discovery');expect(page.locator('main h1')).to_have_text('发现真实文献');page.locator('[name=query]').fill('materials science computational');page.locator('[name=provider][value=openalex]').uncheck()
    with page.expect_response(lambda r:r.url.endswith('/api/v1/discovery') and r.request.method=='POST') as event:page.locator('#search-form button[type=submit]').click()
    search=wait_job(event.value.json()['job_id']);result['search_job']=search;assert search['status']=='COMPLETED',search;papers=context.request.get(url+'/api/v1/jobs/'+search['job_id']+'/results').json()['items'];assert len(papers)==20,len(papers);result['search_records']=[{'paper_id':p['paper_id'],'doi':p['doi'],'title':p['title'],'sources':p['sources']} for p in papers];passed('real Crossref search target20 returns20 stored records')
    # Known benchmark: original metadata/CC license are externalized in the manifest.
    payload={'paper_id':'arxiv:'+meta['id'],'doi':meta['doi'],'title':meta['title'],'authors':[{'name':n} for n in meta['authors']],'year':int(meta['year']),'source_url':meta['url'],'is_open_access':True,'fulltext_links':[{'url':meta['pdf_url'],'kind':'pdf','access':'OPEN_ACCESS','license':meta['license_url']}]}
    posted=context.request.post(url+'/api/v1/papers',data=payload);assert posted.status==201,posted.text();pid=posted.json()['paper_id'];page.goto(url+'/#library');expect(page.locator('main h1')).to_have_text('我的文献库');page.locator('#library-filter input').fill(meta['title']);page.locator('#library-filter button').click();expect(page.locator('[data-select]')).to_have_count(1);page.locator('[data-select]').check()
    with page.expect_response(lambda r:r.url.endswith('/api/v1/batch') and r.request.method=='POST') as event:page.locator('[data-batch=acquire]').click()
    downloaded=wait_job(event.value.json()['job_id']);result['download_job']=downloaded;assert downloaded['result_json']['items'][pid]['status']=='FULLTEXT_AVAILABLE',downloaded;detail=context.request.get(url+'/api/v1/papers/'+pid+'/detail').json();result['download']=detail['document'];result['license_basis']={'url':meta['license_url'],'verified_at':meta['license_checked_at'],'same_sha_as_previously_verified_version':detail['document']['sha256']==meta['sha256']};assert detail['document']['file_size']>100000;passed('real arXiv PDF downloaded and resource-limited probe accepted')
    page.goto(url+'/#paper/'+pid.replace(':','%3A'));expect(page.locator('main h1')).to_have_text(meta['title'])
    with page.expect_response(lambda r:r.url.endswith('/api/v1/batch') and r.request.method=='POST') as event:page.locator('#extract-paper').click()
    extracted=wait_job(event.value.json()['job_id']);assert extracted['result_json']['items'][pid]['status']=='NOT_EXECUTED',extracted;detail=context.request.get(url+'/api/v1/papers/'+pid+'/detail').json();assert detail['parsed']['segments'];result['parsed']={'parser':detail['parsed']['parser'],'segments':len(detail['parsed']['segments']),'extraction_execution_status':detail['extraction']['payload_json']['execution_status']};passed('real PDF parsed; missing model remains NOT_EXECUTED')
    page.goto(url+'/#paper/'+pid.replace(':','%3A'));expect(page.locator('#review-form button')).to_be_enabled();page.locator('#review-form textarea').fill('Workflow smoke check only; scientific claims not reviewed.');page.locator('#review-form button').click();expect(page.locator('#toast')).to_contain_text('复核意见已保存');expect(page.locator('#pdf-viewer')).to_have_attribute('src',__import__('re').compile(r'^blob:'));page.wait_for_timeout(2000);page.screenshot(path=str(out/'real-paper.png'),full_page=True);passed('real paper workflow note saved without claiming scientific review')
    page.goto(url+'/#library');expect(page.locator('#json-export')).to_be_visible()
    for button,ext in [('json-export','jsonl'),('xlsx-export','xlsx'),('pdf-export','zip')]:
     with page.expect_download() as event:page.locator('#'+button).click()
     path=out/('real-selected.'+ext);event.value.save_as(path)
     if ext=='jsonl':
      rows=[json.loads(x) for x in path.read_text().splitlines()];assert len(rows)==1 and rows[0]['paper']['paper_id']==pid;assert rows[0]['review']['payload']['notes'].startswith('Workflow smoke')
     elif ext=='zip':
      with zipfile.ZipFile(path) as z:
       manifest=json.loads(z.read('manifest.json'));assert len(manifest)==1 and manifest[0]['included'];assert hashlib.sha256(z.read(manifest[0]['file'])).hexdigest()==detail['document']['sha256']
    page.screenshot(path=str(out/'real-library.png'),full_page=True);passed('selected real-paper JSONL Excel PDF downloads preserve identity SHA and notes');browser.close();result['status']='PASS'
  except Exception as exc:result['status']='FAIL';result['error']=type(exc).__name__+': '+str(exc)[:1500];raise
  finally:
   proc.terminate()
   try:proc.wait(timeout=8)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
   log.close();(out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('LIVE BROWSER SUMMARY: 5 passed, 0 failed; no scientific accuracy or model validation claim')
if __name__=='__main__':main()
