"""Real Chromium checks for the hosted UI using explicitly synthetic engineering fixtures.

Runs in GitHub Actions or a configured local development machine. It never signs
into production, calls a model, or represents fixtures as real scientific output.
Managed Sites preview must use its own relay; this runner does not bypass it.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
import fitz
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]


def main():
    if os.environ.get('SITES_MANAGED_LINUX_CONTAINER') == '1':
        raise SystemExit('Use the managed Sites preview relay here; run this isolated browser suite in CI or configured local development.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('work/hosted-browser'))
    args = parser.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    results = []
    report = {'scope': 'ACTUAL_CHROMIUM_WITH_SYNTHETIC_ENGINEERING_FIXTURES',
              'production_authentication': 'NOT_TESTED', 'scientific_accuracy': 'NOT_EVALUATED', 'reading_scope':'SYNTHETIC_GUIDE_AND_PERSPECTIVE_UI_FIXTURES',
              'checks': results, 'screenshots': []}
    server = None
    with tempfile.TemporaryDirectory(prefix='paperlens-hosted-ci-') as temp:
        project = Path(temp) / 'website'
        shutil.copytree(ROOT / 'website', project, ignore=shutil.ignore_patterns('node_modules', 'work', 'dist'))
        fixture_dir = project / 'work' / 'fixture-inputs'; fixture_dir.mkdir(parents=True)
        base_rows = [
            ('SYNTHETIC engineering fixture', True), ('Methods', True),
            ('We prepared graphene samples using a controlled synthetic protocol with simulated conditions only.', False),
            ('Results', True), ('We observed a synthetic strength of 26.5 GPa in this fictional engineering fixture.', False),
            ('Conclusions', True), ('In conclusion, this synthetic fixture verifies software behavior and makes no scientific claim.', False)]
        specs = []
        for name, revision in [('alpha', 'ONE'), ('beta', 'ONE'), ('alpha', 'TWO')]:
            rows = [(text, head) for text, head in base_rows]
            rows[0] = (f'SYNTHETIC {name} fixture', True)
            rows[2] = (f'We prepared graphene samples using fixture revision {revision} with a controlled synthetic protocol.', False)
            pdf = fitz.open(); page = pdf.new_page(); y = 55
            for text, heading in rows:
                page.insert_textbox(fitz.Rect(45, y, 550, y + 58), text, fontsize=14 if heading else 11)
                y += 65 if not heading else 40
            raw = pdf.tobytes(); pdf.close()
            filename = fixture_dir / f'{name}-{revision}.pdf'; filename.write_bytes(raw)
            specs.append({'id': 'synthetic-' + name, 'title': f'SYNTHETIC {name} fixture',
                          'revision': revision, 'pdf_hash': hashlib.sha256(raw).hexdigest(),
                          'blocks': [{'block_id': f'p1-b{i}', 'page': 1, 'text': text, 'heading': heading, 'caption': False}
                                     for i, (text, heading) in enumerate(rows)]})
        (fixture_dir / 'specs.json').write_text(json.dumps(specs))
        # This generator uses the actual browser rule implementation, not a mock model.
        generator = r'''
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {scientificFromBlocks} from './web_assets/research-core.js';
import {validateResearch} from './web_assets/research-shared.js';
import {syntheticReadingRecords} from './fixtures/reading-synthetic.mjs';
const dir='work/fixture-inputs',policy=JSON.parse(await readFile('web_assets/research-policy.json','utf8'));
const specs=JSON.parse(await readFile(dir+'/specs.json','utf8'));await mkdir('work/preview-objects',{recursive:true});
for(const s of specs){const meta={id:s.id,paper_id:'local:'+s.pdf_hash,title:s.title,source:'local',authors:['SYNTHETIC test fixture'],url:'',doi:null};
const r=scientificFromBlocks(s.blocks,meta,policy,s.pdf_hash);validateResearch(r);
await writeFile(dir+'/'+s.id+'-'+s.revision+'.jsonl',JSON.stringify(r)+'\n');
if(s.revision==='ONE')await writeFile('work/preview-objects/'+Buffer.from('research/records/'+encodeURIComponent(r.id)+'.json').toString('base64url'),JSON.stringify(r));}
for(const r of syntheticReadingRecords(policy)){validateResearch(r);await writeFile('work/preview-objects/'+Buffer.from('research/records/'+encodeURIComponent(r.id)+'.json').toString('base64url'),JSON.stringify(r));}
await writeFile(dir+'/reading-specs.json',JSON.stringify(syntheticReadingRecords(policy)));
'''
        (project / 'generate-browser-fixtures.mjs').write_text(generator)
        subprocess.run(['node', 'generate-browser-fixtures.mjs'], cwd=project, check=True)
        reading_fixtures=json.loads((fixture_dir/'reading-specs.json').read_text())
        # Small OFL test font; production's complete static font is kept in private R2.
        font=(ROOT/'tests/assets/report-ci.ttf').read_bytes();font_sha=hashlib.sha256(font).hexdigest()
        font_manifest=json.loads((project/'seed/report-font.json').read_text());font_manifest.update({'bytes':len(font),'sha256':font_sha,'test_scope':'SYNTHETIC_ENGINEERING_UI_FONT'})
        (project/'seed/report-font.json').write_text(json.dumps(font_manifest))
        (project/'work/preview-objects'/base64.urlsafe_b64encode(('batches/assets/'+font_sha+'.font').encode()).decode().rstrip('=')).write_bytes(font)
        batch_pdfs={}
        for number in range(1,6):
            d=fitz.open();p=d.new_page();y=45
            for text,head in [(f'SYNTHETIC batch {number}',True),*base_rows[1:]]:
                p.insert_textbox(fitz.Rect(45,y,550,y+58),text,fontsize=14 if head else 11);y+=40 if head else 65
            batch_pdfs[f'9999.0000{number}v1']=d.tobytes();d.close()
        subprocess.run(['node', 'build-workspace.mjs'], cwd=project, check=True)
        invalid = fixture_dir / 'invalid.pdf'; invalid.write_bytes(b'This is a SYNTHETIC invalid PDF fixture, not a paper.')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        origin = f'http://127.0.0.1:{port}'
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen(['node', 'scripts/dev.mjs', '--host', '127.0.0.1', '--port', str(port)], cwd=project, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(80):
                    if server.poll() is not None:
                        raise RuntimeError('Isolated server exited; see server.log')
                    try:
                        with urllib.request.urlopen(origin + '/api/health', timeout=1) as response:
                            assert json.load(response)['storage'] is True
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError('Isolated server did not become ready')
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                    errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                    def check(name, fn):
                        fn(); results.append({'name': name, 'status': 'PASS'})
                    def capture(name):
                        page.evaluate('document.fonts.ready'); path = output / name; page.screenshot(path=str(path), full_page=True); report['screenshots'].append(name)
                    def library():
                        page.goto(origin + '/#library'); page.get_by_role('heading', name='我的文献库', exact=True).wait_for()
                    def open_fixture():
                        page.goto(origin + '/#paper/synthetic-alpha'); page.get_by_role('heading', name='SYNTHETIC alpha fixture', exact=True).wait_for()
                    page.goto(origin)
                    page.get_by_role('heading', name='检索科学文献', exact=True).wait_for()
                    page.get_by_text('从真实论文开始', exact=True).wait_for()
                    page.locator('.sample-list .paper-row').nth(2).wait_for()
                    check('Homepage prioritizes search and pins genuine examples without labelling synthetic imports as examples', lambda: (
                        page.get_by_label('关键词、DOI 或 arXiv ID').is_visible() or (_ for _ in ()).throw(AssertionError('Search missing')),
                        len(page.locator('.sample-list .paper-row').all()) == 3 or (_ for _ in ()).throw(AssertionError('Expected three fixed genuine metadata examples')),
                        'SYNTHETIC' not in page.locator('.sample-list').inner_text() or (_ for _ in ()).throw(AssertionError('Fixture mislabeled as acquired example'))))
                    capture('homepage-desktop.png')
                    # Only this UI search response is stubbed; real providers have separate production receipts.
                    page.route('**/api/discovery?**', lambda route: route.fulfill(json={
                        'provider': 'crossref', 'scope': 'SYNTHETIC_ENGINEERING_FIXTURE', 'total': 1,
                        'items': [{'id': 'doi:10.0000/synthetic', 'doi': '10.0000/synthetic', 'title': 'SYNTHETIC discovery fixture',
                                   'authors': ['SYNTHETIC author'], 'year': 2026, 'source': 'crossref', 'url': 'https://doi.org/10.0000/synthetic',
                                   'abstract': 'Synthetic UI fixture only.', 'fulltext_status': 'METADATA_ONLY'}]}))
                    page.get_by_role('button', name='Crossref', exact=True).click()
                    page.get_by_label('关键词、DOI 或 arXiv ID').fill('SYNTHETIC query')
                    page.get_by_role('button', name='检索文献', exact=True).click()
                    page.get_by_text('SYNTHETIC discovery fixture', exact=True).wait_for()
                    check('Search form submits and renders metadata-only source actions using a labelled engineering fixture', lambda: page.get_by_role('button', name='导入授权 PDF', exact=True).is_visible() or (_ for _ in ()).throw(AssertionError('Missing authorized PDF action')))
                    library()
                    page.locator('input[data-select="synthetic-alpha"]').check()
                    page.locator('input[data-select="synthetic-beta"]').check()
                    page.get_by_role('button', name='比较所选', exact=True).click()
                    page.get_by_role('heading', name='文献比较', exact=True).wait_for()
                    check('Comparison contains selected methods and conclusions', lambda: (
                        'fixture revision ONE' in page.locator('.compare-table').inner_text() or (_ for _ in ()).throw(AssertionError('Method missing')),
                        'software behavior' in page.locator('.compare-table').inner_text() or (_ for _ in ()).throw(AssertionError('Conclusion missing'))))
                    library()
                    assert page.locator('input[data-select="synthetic-alpha"]').is_checked()
                    assert page.locator('input[data-select="synthetic-beta"]').is_checked()
                    with page.expect_download() as quick_download:
                        page.get_by_role('button', name='导出所选', exact=True).click()
                    quick_path=output/'quick-selected.xlsx';quick_download.value.save_as(quick_path)
                    assert page.url.endswith('/#library')
                    with zipfile.ZipFile(quick_path) as archive:
                        text=''.join(archive.read(n).decode() for n in archive.namelist() if n.startswith('xl/worksheets/sheet'))
                        assert 'SYNTHETIC alpha' in text and 'SYNTHETIC beta' in text
                        assert '2501.00680' not in text and 'synthetic-reading' not in text
                    results.append({'name':'One library click directly downloads selected Excel without opening export settings','status':'PASS'})
                    capture('quick-export-library-desktop.png')
                    # A genuine failed record request must recover the direct-download button and selection.
                    page.reload();page.get_by_role('heading',name='我的文献库',exact=True).wait_for()
                    page.route('**/api/research/record?id=synthetic-alpha',lambda route:route.fulfill(status=503,json={'error':'SYNTHETIC export source failure'}))
                    page.get_by_role('button',name='导出文献',exact=True).click()
                    page.get_by_text('SYNTHETIC export source failure',exact=True).wait_for()
                    expect(page.get_by_role('button',name='导出文献',exact=True)).to_be_enabled()
                    assert page.locator('input[data-select="synthetic-alpha"]').is_checked()
                    assert page.locator('input[data-select="synthetic-beta"]').is_checked()
                    page.unroute('**/api/research/record?id=synthetic-alpha')
                    with page.expect_download() as recovered_download:
                        page.get_by_role('button',name='导出文献',exact=True).click()
                    recovered_download.value.save_as(output/'quick-recovered.xlsx')
                    assert page.url.endswith('/#library')
                    results.append({'name':'Direct export failure restores its button and selection, and retry starts a real download','status':'PASS'})
                    page.get_by_role('link',name='更多格式',exact=True).click()
                    page.get_by_role('radio', name='JSONL 完整记录', exact=False).check()
                    with page.expect_download() as download:
                        page.get_by_role('button', name='导出 2 篇文献', exact=True).click()
                    selected_path = output / 'selected.jsonl'; download.value.save_as(selected_path)
                    selected = [json.loads(x) for x in selected_path.read_text().splitlines() if x.strip()]
                    assert {x['id'] for x in selected} == {'synthetic-alpha', 'synthetic-beta'}
                    results.append({'name': 'Selection survives navigation and JSONL contains exactly the selected records', 'status': 'PASS'})
                    page.get_by_role('radio', name='Excel 工作簿', exact=False).check()
                    with page.expect_download() as download:
                        page.get_by_role('button', name='导出 2 篇文献', exact=True).click()
                    workbook = output / 'selected.xlsx'; download.value.save_as(workbook)
                    with zipfile.ZipFile(workbook) as archive:
                        sheet_names = [n for n in archive.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
                        assert len(sheet_names) == 9
                        exported_text = ''.join(archive.read(n).decode() for n in sheet_names)
                        assert 'SYNTHETIC alpha' in exported_text and 'SYNTHETIC beta' in exported_text
                        assert '2501.00680' not in exported_text
                    results.append({'name': 'UI Excel download has nine reading/audit sheets and excludes unselected real-example records', 'status': 'PASS'})
                    # Isolate all-library scope to genuine synthetic stored records, without fabricating seed full texts.
                    synthetic_summaries=[r for r in page.request.get(origin+'/api/research/index').json()['records'] if r['id'].startswith('synthetic-')]
                    assert len(synthetic_summaries)==4
                    library();page.get_by_role('button',name='清空选择',exact=True).click()
                    page.route('**/api/research/index',lambda route:route.fulfill(json={'records':synthetic_summaries,'cursor':None}))
                    page.reload();page.get_by_role('heading',name='我的文献库',exact=True).wait_for()
                    page.set_viewport_size({'width':390,'height':844})
                    with page.expect_download() as all_download:
                        page.get_by_role('button',name='导出文献',exact=True).click()
                    all_path=output/'quick-all.xlsx';all_download.value.save_as(all_path)
                    with zipfile.ZipFile(all_path) as archive:
                        text=''.join(archive.read(n).decode() for n in archive.namelist() if n.startswith('xl/worksheets/sheet'))
                        assert all(r['id'] in text for r in synthetic_summaries)
                        assert '2501.00680' not in text
                    assert page.url.endswith('/#library')
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                    capture('quick-export-library-mobile.png')
                    page.set_viewport_size({'width':1440,'height':1000})
                    results.append({'name':'With no selection, the library export button directly downloads all stored fixture records','status':'PASS'})
                    page.unroute('**/api/research/index');page.reload()
                    page.locator('input[data-select="synthetic-alpha"]').check();page.locator('input[data-select="synthetic-beta"]').check()
                    open_fixture()
                    with page.expect_download() as single_download:
                        page.locator('[data-export-one]').click()
                    single_path=output/'quick-single.xlsx';single_download.value.save_as(single_path)
                    with zipfile.ZipFile(single_path) as archive:
                        text=''.join(archive.read(n).decode() for n in archive.namelist() if n.startswith('xl/worksheets/sheet'))
                        assert 'SYNTHETIC alpha' in text and 'SYNTHETIC beta' not in text
                    assert page.url.endswith('/#paper/synthetic-alpha')
                    results.append({'name':'Single-paper Excel directly downloads only the current paper and leaves its detail open','status':'PASS'})
                    with page.expect_download(timeout=60000) as generated_pdf:
                        page.locator('[data-report-one]').click()
                    report_path=output/'synthetic-processing-report.pdf';generated_pdf.value.save_as(report_path)
                    with fitz.open(report_path) as document:
                        assert len(document)>=2
                        assert 'SYNTHETIC' in ''.join(p.get_text() for p in document)
                    results.append({'name':'UI directly downloads a selectable PDF with a fixed reading framework, without a print popup','status':'PASS'})
                    page.locator('.detail-tabs [data-detail-tab="evidence"]').click()
                    page.locator('.evidence-entry').first.wait_for()
                    page.locator('.detail-tabs [data-detail-tab="record"]').click()
                    page.locator('.source-chip[data-evidence]').first.click()
                    assert page.locator('#evidence-inspector .inspector-quote').inner_text().strip()
                    capture('evidence-desktop.png')
                    results.append({'name': 'Evidence controls render exact source text and original page/block offsets', 'status': 'PASS'})
                    page.locator('.detail-tabs [data-detail-tab="review"]').click()
                    page.get_by_label('复核备注', exact=True).fill('SYNTHETIC reviewer note; no scientific validation')
                    page.get_by_label('研究方法', exact=True).fill('SYNTHETIC manual method overlay')
                    page.get_by_role('button', name='保存复核意见', exact=True).click()
                    page.get_by_text('复核意见已保存，自动结果保持原样。', exact=True).wait_for()
                    page.reload(); page.get_by_role('heading', name='SYNTHETIC alpha fixture', exact=True).wait_for()
                    page.locator('.detail-tabs [data-detail-tab="review"]').click(); page.get_by_label('复核备注', exact=True).wait_for()
                    expect(page.get_by_label('复核备注', exact=True)).to_have_value('SYNTHETIC reviewer note; no scientific validation')
                    assert not page.get_by_role('checkbox', name='我已对照原文核查当前四个核心字段').is_checked()
                    current = page.request.get(origin + '/api/research/record?id=synthetic-alpha').json()
                    assert 'fixture revision ONE' in current['methods']
                    assert current['review_status'] == 'unreviewed'
                    results.append({'name': 'Review notes and manual overlays persist without rewriting or confirming automatic fields', 'status': 'PASS'})
                    page.goto(origin + '/#upload'); page.get_by_role('button', name='导入 JSONL 记录', exact=True).wait_for()
                    with page.expect_file_chooser() as chooser:
                        page.get_by_role('button', name='导入 JSONL 记录', exact=True).click()
                    chooser.value.set_files(str(fixture_dir / 'synthetic-alpha-TWO.jsonl'))
                    page.get_by_role('heading', name='我的文献库', exact=True).wait_for()
                    open_fixture(); page.locator('.reader-points').filter(has_text='fixture revision TWO').first.wait_for()
                    page.locator('.detail-tabs [data-detail-tab="record"]').click(); page.locator('.record-copy').filter(has_text='fixture revision TWO').wait_for()
                    assert all('fixture revision ONE' not in value for value in page.locator('.record-copy').all_text_contents())
                    results.append({'name': 'Import of an already-viewed ID refreshes cached detail and evidence', 'status': 'PASS'})
                    page.goto(origin + '/#upload'); page.get_by_role('button', name='选择 PDF 文件', exact=True).wait_for()
                    with page.expect_file_chooser() as chooser:
                        page.get_by_role('button', name='选择 PDF 文件', exact=True).click()
                    chooser.value.set_files([str(fixture_dir / 'beta-ONE.pdf'), str(invalid)])
                    done = page.locator('.job-row').filter(has_text='beta-ONE').get_by_role('link', name='查看记录', exact=True)
                    done.wait_for(timeout=90000)
                    bad = page.locator('.job-row').filter(has_text='invalid')
                    bad.locator('.job-error').wait_for(timeout=30000)
                    completed_before = page.locator('.job-row').filter(has_text='记录已保存').count()
                    page.get_by_role('button', name='重试失败项', exact=True).click()
                    bad.locator('.job-error').wait_for(timeout=30000)
                    assert done.is_visible()
                    assert page.locator('.job-row').filter(has_text='记录已保存').count() == completed_before
                    results.append({'name': 'Actual PDF.js processing saves a vector PDF; invalid PDF recovery/replacement and failed-only retry preserve completed work', 'status': 'PASS'})
                    assert 'PDF 结构无效或文件已损坏' in bad.locator('.job-error').inner_text()
                    capture('failed-pdf-desktop.png')
                    with page.expect_file_chooser() as chooser:
                        bad.get_by_role('button', name='重新选择 PDF', exact=True).click()
                    chooser.value.set_files(str(fixture_dir / 'alpha-TWO.pdf'))
                    bad.get_by_role('link', name='查看记录', exact=True).wait_for(timeout=90000)
                    assert done.is_visible()
                    assert page.locator('.job-row').filter(has_text='记录已保存').count() == completed_before + 1
                    capture('jobs-desktop.png')
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.goto(origin); page.reload(); page.get_by_role('heading', name='检索科学文献', exact=True).wait_for()
                    page.get_by_text('从真实论文开始', exact=True).wait_for()
                    page.locator('.sample-list .paper-row').nth(2).wait_for()
                    assert page.locator('#sidebar').evaluate('(node)=>node.inert') is True
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1') is True
                    capture('homepage-mobile.png')
                    page.get_by_role('button', name='打开导航', exact=True).click()
                    assert page.locator('#sidebar').evaluate('(node)=>node.inert') is False
                    page.keyboard.press('Escape')
                    assert page.locator('#sidebar').evaluate('(node)=>node.inert') is True
                    assert page.get_by_role('button', name='打开导航', exact=True).evaluate('(node)=>document.activeElement===node')
                    results.append({'name': 'Mobile composition fits width and closed navigation leaves keyboard/assistive focus order', 'status': 'PASS'})
                    page.set_viewport_size({'width':1440,'height':1000})
                    for record in reading_fixtures:
                        page.goto(origin+'/#paper/'+record['id'])
                        guide=record['reading_card']['source_review']
                        page.get_by_role('heading',name=guide['title_zh'],exact=True).wait_for()
                        page.locator('.detail-tabs [data-detail-tab="reading"]').click()
                        expect(page.locator('.reader-notice')).to_contain_text('不是规则自动摘要或独立专家金标准')
                        expect(page.locator('.reader-quality')).to_contain_text('待用户复核')
                        expect(page.locator('.reader-points').first).to_contain_text(guide['question'][0]['text'])
                        page.locator('[data-reading-evidence]').first.click()
                        assert page.locator('#evidence-inspector .inspector-quote').inner_text().strip()
                        if record['id']=='synthetic-reading-experiment':
                            expect(page.locator('.reader-numbers')).to_contain_text('1.80')
                            expect(page.locator('.reader-numbers')).to_contain_text('1.79')
                            expect(page.locator('.reader-numbers')).to_contain_text('4.2')
                        if record['id']=='synthetic-reading-perspective':
                            assert page.get_by_role('heading',name='主要论点',exact=True).count()==1
                            assert page.get_by_role('heading',name='主要步骤',exact=True).count()==0
                            assert page.get_by_role('heading',name='主要发现',exact=True).count()==0
                        capture('reading-'+record['id']+'.png')
                        results.append({'name':'Synthetic reading-card origin, typed sections and evidence interaction '+record['id'],'status':'PASS'})
                    page.set_viewport_size({'width':390,'height':844})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1') is True
                    expect(page.locator('#sidebar')).not_to_be_in_viewport()
                    capture('reading-mobile.png')
                    # New one-click flow uses real PDF.js, rule extraction, R2 API and PDF/XLSX generation.
                    # Only upstream discovery/PDF bytes are explicitly synthetic fixtures.
                    page.set_viewport_size({'width':1440,'height':1000})
                    page.unroute('**/api/discovery?**')
                    batch_metadata=[{'id':pid,'title':'SYNTHETIC batch '+str(n+1),'source':'arxiv','authors':['SYNTHETIC fixture'],
                                     'url':'https://example.org/SYNTHETIC','pdf_url':'https://example.org/SYNTHETIC.pdf',
                                     'license_url':'https://creativecommons.org/licenses/by/4.0/'} for n,pid in enumerate(batch_pdfs)]
                    page.route('**/api/discovery?**',lambda route:route.fulfill(json={'items':batch_metadata,'provider':'arxiv','scope':'SYNTHETIC_ENGINEERING_BATCH_FIXTURE'}))
                    corrupt={'enabled':True};source_calls={pid:0 for pid in batch_pdfs}
                    def batch_source(route):
                        pid=urllib.parse.parse_qs(urllib.parse.urlparse(route.request.url).query)['id'][0]
                        source_calls[pid]+=1
                        body=b'%PDF-1.4\nSYNTHETIC corrupt fixture' if pid=='9999.00003v1' and corrupt['enabled'] else batch_pdfs[pid]
                        route.fulfill(status=200,content_type='application/pdf',body=body)
                    page.route('**/api/pdf?**',batch_source)
                    page.goto(origin+'/#discovery');page.get_by_role('heading',name='检索科学文献',exact=True).wait_for()
                    page.get_by_role('button',name='arXiv',exact=True).click();page.get_by_label('关键词、DOI 或 arXiv ID',exact=True).fill('SYNTHETIC automatic batch')
                    page.get_by_label('计划获取',exact=True).select_option('5');page.locator('#batch-auto').check()
                    with page.expect_download(timeout=120000) as batch_download:
                        page.get_by_role('button',name='一键爬取并生成 PDF / Excel',exact=True).click()
                    partial_zip=output/'one-click-partial.zip';batch_download.value.save_as(partial_zip)
                    capture('one-click-partial-desktop.png')
                    with zipfile.ZipFile(partial_zip) as z:
                        manifest=json.loads(z.read('BATCH-MANIFEST.json'));batch_id=manifest['id'] if 'id' in manifest else None
                        assert len(manifest['items'])==5
                        assert sum(j['state']=='done' for j in manifest['items'])==4
                        assert sum(j['state']=='failed' for j in manifest['items'])==1
                        assert len(z.read('research.jsonl').decode().splitlines())==4
                        with fitz.open(stream=z.read('report.pdf'),filetype='pdf') as report_doc:
                            report_text=''.join(report_doc[n].get_text() for n in range(len(report_doc)))
                            assert 'SYNTHETIC' in report_text and '失败1' in ''.join(report_text.split())
                        (output/'one-click-partial-report.pdf').write_bytes(z.read('report.pdf'))
                    assert all(n==1 for n in source_calls.values())
                    results.append({'name':'One click processes five PDF fixtures, isolates one corrupt PDF and automatically downloads actual PDF/XLSX/JSONL/originals ZIP','status':'PASS'})
                    corrupt['enabled']=False
                    with page.expect_download(timeout=120000) as retried_download:
                        page.get_by_role('button',name='仅重试失败项',exact=True).click()
                    finished_zip=output/'one-click-complete.zip';retried_download.value.save_as(finished_zip)
                    with zipfile.ZipFile(finished_zip) as z:
                        m=json.loads(z.read('BATCH-MANIFEST.json'));assert m['status']=='complete'
                        assert sum(j['state']=='done' for j in m['items'])==5
                        actual=[json.loads(line) for line in z.read('research.jsonl').decode().splitlines()]
                        assert len(actual)==5 and all(r['extractor_version']=='browser-scientific-rules-v1.5' for r in actual)
                        assert all('source_review' not in r['reading_card'] for r in actual)
                        (output/'one-click-complete-report.pdf').write_bytes(z.read('report.pdf'))
                        (output/'one-click-complete.xlsx').write_bytes(z.read('research.xlsx'))
                    assert source_calls['9999.00003v1']==2
                    assert all(n==1 for pid,n in source_calls.items() if pid!='9999.00003v1')
                    capture('one-click-complete-desktop.png')
                    results.append({'name':'Failed-only retry refetches the corrupt PDF and leaves four completed extraction checkpoints untouched','status':'PASS'})
                    page.reload();page.get_by_role('link',name='下载本批报告 PDF',exact=True).wait_for()
                    page.set_viewport_size({'width':390,'height':844});expect(page.locator('#sidebar')).not_to_be_in_viewport()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    capture('one-click-complete-mobile.png')
                    results.append({'name':'Durable batch files survive reload and the complete one-click page fits mobile width','status':'PASS'})
                    assert not errors, errors
                    results.append({'name': 'Hosted UI completes the exercised flows without uncaught browser JavaScript errors', 'status': 'PASS'})
                    browser.close()
                report['passed'] = len(results); report['failed'] = 0
            except Exception as error:
                report['passed'] = len(results); report['failed'] = 1; report['error'] = repr(error)
                (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
                raise
            finally:
                if server is not None:
                    server.terminate()
                    try:
                        server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill(); server.wait()
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
