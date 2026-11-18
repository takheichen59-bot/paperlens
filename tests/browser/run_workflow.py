"""Real Chromium + real local API/SQLite. Synthetic records are labelled fixtures.
No route interception, fake upstream search, mocked LLM or scientific accuracy claim.
"""
import argparse,csv,hashlib,io,json,os,shutil,socket,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
TOKEN='browser-login-fixture'

def fixture_corpus(root):
 import pymupdf as fitz
 from science_platform.store import Store
 from science_platform.models import Paper,ScientificRecord,Claim,Evidence,ValidationStatus
 from science_platform.parsing import PyMuPDFParser,digest
 from science_platform.extraction import TaskOutput,validate_task
 store=Store(root/'data/platform.sqlite3');items=[]
 for i in range(3):
  pid=f'ui:canonical-{i}';doi=f'10.9999/paperlens-ui-{i}'
  store.upsert_paper(Paper(paper_id=pid,doi=doi,title=f'SYNTHETIC UI fixture {i} — not scientific evidence',source_url='',year=2024+i,venue='Engineering tests'))
  pdf=root/f'fixture-{i}.pdf';d=fitz.open();page=d.new_page();page.insert_text((72,60),'Synthetic interface test, not a scientific paper.');page.insert_text((72,100),'Methods',fontsize=16);page.insert_text((72,135),'We used a synthetic solver for interface testing only.');page=d.new_page();page.insert_text((72,80),'Results',fontsize=16);page.insert_text((72,120),'The fixture reports 42 test units.');d.save(pdf);d.close();items.append({'pid':pid,'doi':doi,'path':pdf})
  if i==2:continue # A real missing-file failure in the batch, repaired by UI upload.
  sha=digest(pdf);did=store.save_document(pid,sha,pdf,'pdf',license='CC0',method='SYNTHETIC_ENGINEERING_FIXTURE')
  doc=PyMuPDFParser().parse(pdf,pid);store.save_parse(did,doc);segment=next(s for s in doc.segments if 'We used a synthetic solver' in s.text);quote='We used a synthetic solver for interface testing only.';start=segment.text.index(quote)
  ev=Evidence(evidence_id='manual-0',paper_id=pid,document_sha256=sha,segment_id=segment.segment_id,page=segment.page,section=segment.section,quote=quote,start=start,end=start+len(quote),extraction_model='MANUAL_ENGINEERING_FIXTURE',extraction_version='ui-1',validation_status=ValidationStatus.VERIFIED)
  claim=Claim(claim_id='claim-0',text=quote,evidence_ids=(ev.evidence_id,));validate_task(doc,TaskOutput(claims=(claim,),evidence=(ev,)),extractor_field='methodology')
  store.save_extraction(did,ScientificRecord(paper_id=pid,document_sha256=sha,extraction_version='ui-1',model='MANUAL_ENGINEERING_FIXTURE',execution_status='EXECUTED',methodology=(claim,),evidence=(ev,)))
 return items

def main():
 from playwright.sync_api import sync_playwright,expect
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('work/browser'));p.add_argument('--browser',default=os.getenv('CHROMIUM_EXECUTABLE'));args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 checks=[];events=[];started=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='paperlens-browser-') as tmp:
  root=Path(tmp);items=fixture_corpus(root)
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  url=f'http://127.0.0.1:{port}';env={k:v for k,v in os.environ.items() if not k.startswith(('LLM_','OPENAI_','EMBEDDING_','GROBID_','DOCLING_','PAPERLENS_'))};env.update(PYTHONPATH=str(ROOT/'src'),PAPERLENS_API_TOKEN=TOKEN)
  log=(out/'server.log').open('w');server=subprocess.Popen([sys.executable,'-m','science_platform','serve','--data',str(root/'data'),'--port',str(port)],cwd=root,env=env,stdout=log,stderr=log)
  try:
   import httpx
   deadline=time.monotonic()+30
   while True:
    try:
     if httpx.get(url+'/api/v1/health').status_code==200:break
    except httpx.HTTPError:pass
    if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Local API did not start')
    time.sleep(.1)
   with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox']}
    if args.browser:options['executable_path']=args.browser
    browser=pw.chromium.launch(**options);context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=context.new_page();page.set_default_timeout(15000)
    page.on('pageerror',lambda e:events.append({'kind':'javascript_error','text':str(e)}))
    page.on('console',lambda e:events.append({'kind':'csp_error','text':e.text}) if e.type=='error' and ('Content Security Policy' in e.text or 'violates' in e.text) else None)
    def check(name,fn):
     try:fn();checks.append({'name':name,'status':'PASS'});print('PASS',name,flush=True)
     except Exception as e:
      checks.append({'name':name,'status':'FAIL','error':type(e).__name__+': '+str(e)[:1000]});page.screenshot(path=str(out/'failure.png'),full_page=True);raise
    def go(route,title):page.goto(url+'/#'+route);expect(page.locator('main h1')).to_have_text(title)
    def job_wait(jid):
     end=time.monotonic()+90
     while time.monotonic()<end:
      job=context.request.get(url+'/api/v1/jobs/'+jid,headers={'Authorization':'Bearer '+TOKEN}).json()
      if job['status'] in {'COMPLETED','FAILED'}:return job
      time.sleep(.15)
     raise AssertionError('Batch did not finish')
    def upload_existing(i):
     go('library','我的文献库');page.locator('#upload-toggle').click();page.locator('#upload-form [name=title]').fill(f'SYNTHETIC UI fixture {i} — not scientific evidence');page.locator('#upload-form [name=doi]').fill('https://doi.org/'+items[i]['doi'].upper());page.locator('#upload-form [name=file]').set_input_files(items[i]['path']);page.locator('#upload-form button[type=submit]').click();expect(page).to_have_url(url+'/#paper/'+items[i]['pid'].replace(':','%3A'));expect(page.locator('main h1')).to_contain_text('SYNTHETIC UI fixture')
    def auth():
     page.goto(url);expect(page.locator('#auth-form')).to_be_visible();page.locator('#auth-form input').fill(TOKEN);page.locator('#auth-form button').click();expect(page.locator('main h1')).to_have_text('从论文到可追溯的研究记录')
    check('01 authentication recovery and dashboard',auth)
    def all_pages():
     for route,title in [('library','我的文献库'),('discovery','发现真实文献'),('algorithms','算法浏览器'),('comparison','跨论文比较'),('gaps','研究空白与局限'),('graph','来源于真实记录的关联图'),('assistant','向文献库提问'),('jobs','任务监控'),('settings','配置与能力状态')]:go(route,title)
     # Delay consumption of one genuine API response body across navigation.
     # This covers the headers/body race without replacing any HTTP records.
     page.evaluate("""() => {
      const original=window.fetch;
      window.fetch=async (...args) => {
       const response=await original(...args);
       if(String(args[0]).startsWith('/api/v1/algorithms?')) {
        const json=response.json.bind(response);
        response.json=async () => {
         const body=await json();window.__bodyHeld=true;
         await new Promise(resolve=>window.__releaseBody=resolve);
         return body;
        };
       }
       return response;
      };
      window.__restoreFetch=()=>window.fetch=original;
      location.hash='algorithms';
     }""")
     page.wait_for_function('() => window.__bodyHeld === true')
     go('comparison','跨论文比较')
     page.evaluate('async () => { window.__releaseBody(); window.__restoreFetch(); await new Promise(resolve=>setTimeout(resolve,0)); }')
     page.wait_for_function("() => document.querySelector('#connection').textContent.includes('本地 API 已连接')")
     expect(page.locator('main h1')).to_have_text('跨论文比较')
    check('02 all navigation pages, empty states and delayed response isolation',all_pages)
    def filter_case():
     go('library','我的文献库');page.locator('#library-filter input').fill('NO_MATCH_FOR_ENGINEERING_TEST');page.locator('#library-filter button').click();expect(page.locator('.empty')).to_contain_text('尚无符合条件');page.locator('#library-filter input').fill('');page.locator('#library-filter button').click();expect(page.locator('[data-select]')).to_have_count(3)
    check('03 actual library filter and empty-state recovery',filter_case)
    def evidence_review():
     go('paper/ui%3Acanonical-0','SYNTHETIC UI fixture 0 — not scientific evidence');page.locator('[data-evidence]').first.click();expect(page.locator('#inspector mark')).to_have_text('We used a synthetic solver for interface testing only.');page.locator('#review-form textarea').fill('UI review: exact source checked; synthetic fixture only.');page.locator('#review-form [name=confirmed]').check();page.locator('#review-form button').click();expect(page.locator('#toast')).to_contain_text('复核意见已保存');page.reload();expect(page.locator('#review-form [name=confirmed]')).to_be_checked();expect(page.locator('#review-form textarea')).to_contain_text('exact source checked');expect(page.locator('#pdf-viewer')).to_have_attribute('src',__import__('re').compile(r'^blob:.*#page=1$'));page.locator('#page-next').click();expect(page.locator('#pdf-viewer')).to_have_attribute('src',__import__('re').compile(r'#page=2$'));page.locator('[data-evidence]').first.click();expect(page.locator('#inspector mark')).to_be_visible();page.screenshot(path=str(out/'evidence-desktop.png'),full_page=True)
    check('04 evidence slicing, PDF page controls and review persistence',evidence_review)
    check('05 duplicate DOI upload resolves canonical paper ID',lambda:upload_existing(0))
    def batch_retry():
     go('library','我的文献库');page.locator('#select-visible').click();expect(page.locator('#selected-count')).to_have_text('已选 3 篇');
     with page.expect_response(lambda r:r.url.endswith('/api/v1/batch') and r.request.method=='POST') as created:page.locator('[data-batch=parse]').click()
     jid=created.value.json()['job_id'];job=job_wait(jid);assert job['result_json']['items']['ui:canonical-2']['status']=='FAILED';good=job['result_json']['items']['ui:canonical-0'];upload_existing(2);go('jobs','任务监控');button=page.locator(f'[data-job="{jid}"][data-command=resume]');expect(button).to_be_enabled();
     with page.expect_response(lambda r:r.url.endswith('/resume') and r.request.method=='POST') as resumed:button.click()
     assert resumed.value.json()['status']=='QUEUED';after=job_wait(jid);assert after['result_json']['counts']=={'PARSED':3};assert after['result_json']['items']['ui:canonical-0']==good
    check('06 batch failure isolation and retry only failed checkpoint',batch_retry)
    def exports_case():
     go('library','我的文献库');page.locator('#clear-selection').click()
     for i in [0,1]:page.locator(f'[data-select="ui:canonical-{i}"]').check()
     expect(page.locator('#export-scope')).to_have_text('导出范围：已选 2 篇')
     for button,ext in [('json-export','jsonl'),('csv-export','csv'),('xlsx-export','xlsx'),('pdf-export','zip')]:
      with page.expect_download() as event:page.locator('#'+button).click()
      file=out/('selected.'+ext);event.value.save_as(file)
      if ext=='jsonl':
       rows=[json.loads(x) for x in file.read_text().splitlines()];assert {x['paper']['paper_id'] for x in rows}=={'ui:canonical-0','ui:canonical-1'};assert any(x['review'] and 'exact source checked' in x['review']['payload']['notes'] for x in rows)
      elif ext=='csv':assert len(list(csv.DictReader(io.StringIO(file.read_text(encoding='utf-8-sig')))))==2
      elif ext=='xlsx':
       with zipfile.ZipFile(file) as z:assert b'ui:canonical-0' in z.read('xl/worksheets/sheet1.xml') and b'ui:canonical-2' not in z.read('xl/worksheets/sheet1.xml')
      else:
       with zipfile.ZipFile(file) as z:assert len(json.loads(z.read('manifest.json')))==2
     page.screenshot(path=str(out/'library-desktop.png'),full_page=True)
    check('07 selected JSONL CSV Excel PDF downloads preserve review and scope',exports_case)
    def comparison_case():
     go('comparison','跨论文比较');page.locator('#run-selection').click();expect(page.locator('.comparison')).to_contain_text('methodology');expect(page.locator('.comparison')).to_contain_text('Not Reported')
     with page.expect_download() as event:page.locator('#compare-csv').click()
     event.value.save_as(out/'comparison.csv');assert len(list(csv.DictReader(io.StringIO((out/'comparison.csv').read_text(encoding='utf-8-sig')))))==2
    check('08 comparison matrix and export missing-data behavior',comparison_case)
    def graph_assistant():
     go('graph','来源于真实记录的关联图');page.locator('[data-node]').first.click();expect(page.locator('#graph-node h3')).to_be_visible();go('assistant','向文献库提问');page.locator('#ask-form textarea').fill('unreported celestial unicorn proof');page.locator('#ask-form button').click();expect(page.locator('#answer')).to_contain_text('Insufficient evidence in the indexed literature.')
    check('09 derived graph interaction and insufficient-evidence refusal',graph_assistant)
    def no_model():
     go('paper/ui%3Acanonical-2','SYNTHETIC UI fixture 2 — not scientific evidence')
     with page.expect_response(lambda r:r.url.endswith('/api/v1/batch') and r.request.method=='POST') as event:page.locator('#extract-paper').click()
     job=job_wait(event.value.json()['job_id']);assert job['result_json']['items']['ui:canonical-2']['status']=='NOT_EXECUTED';go('paper/ui%3Acanonical-2','SYNTHETIC UI fixture 2 — not scientific evidence');expect(page.locator('.notice.warn')).to_contain_text('深度提取未执行')
    check('10 no-model extraction is visibly NOT_EXECUTED',no_model)
    def mobile():
     page.set_viewport_size({'width':390,'height':844});go('library','我的文献库');assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Page overflows mobile viewport';page.screenshot(path=str(out/'library-mobile.png'),full_page=True)
    check('11 mobile layout has no page-level overflow',mobile)
    def errors():assert not events,json.dumps(events,ensure_ascii=False)
    check('12 no uncaught JavaScript or CSP violations',errors)
    browser.close()
  finally:
   server.terminate()
   try:server.wait(timeout=8)
   except subprocess.TimeoutExpired:server.kill();server.wait()
   log.close();receipt={'status':'PASS' if len(checks)==12 and all(c['status']=='PASS' for c in checks) else 'FAIL','scope':'REAL_BROWSER_WITH_SYNTHETIC_ENGINEERING_FIXTURES','upstream_discovery':'NOT_EXECUTED_IN_OFFLINE_SUITE','real_llm':'NOT_EXECUTED','scientific_accuracy':'NOT_EVALUATED','checks':checks,'events':events,'seconds':round(time.monotonic()-started,2)};(out/'report.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 print(f'BROWSER SUMMARY: {len(checks)} passed, 0 failed (real Chromium; synthetic fixtures; no scientific-quality claim)')
if __name__=='__main__':main()
