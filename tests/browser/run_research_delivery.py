"""Open actual research exports and verify browser downloads without mocks."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time


def main():
    from playwright.sync_api import sync_playwright, expect
    p = argparse.ArgumentParser()
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--browser', default=None)
    args = p.parse_args(); directory = args.directory.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    expected = [json.loads(line) for line in (directory / 'research.jsonl').read_text().splitlines()]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    server = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory', str(directory)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = {'scope': 'REAL_EXPORT_PREVIEW_AND_IDENTICAL_BROWSER_DOWNLOADS', 'checks': [], 'scientific_accuracy': 'NOT_EVALUATED'}
    try:
        with sync_playwright() as pw:
            options = {'headless': True, 'args': ['--no-sandbox']}
            if args.browser: options['executable_path'] = args.browser
            browser = pw.chromium.launch(**options); context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1000}); page = context.new_page()
            errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
            url = f'http://127.0.0.1:{port}/preview.html'
            for attempt in range(30):
                try: page.goto(url); break
                except Exception:
                    if attempt == 29: raise
                    time.sleep(.1)
            expect(page.locator('article')).to_have_count(len(expected))
            for record in expected:
                expect(page.locator('h2').filter(has_text=record['id'])).to_have_count(1)
            result['checks'].append({'name': 'preview actual paper identities', 'status': 'PASS'})
            for name in ['research.xlsx', 'research.jsonl', 'processing-report.pdf']:
                with page.expect_download() as event: page.locator(f'a[download][href="{name}"]').click()
                downloaded = args.output / name; event.value.save_as(downloaded)
                digest = hashlib.sha256(downloaded.read_bytes()).hexdigest()
                assert digest == hashlib.sha256((directory / name).read_bytes()).hexdigest()
                result['checks'].append({'name': 'identical browser download ' + name, 'status': 'PASS', 'sha256': digest})
            assert not errors, errors
            page.screenshot(path=str(args.output / 'preview.png'))
            result.update(status='PASS', chromium=browser.version, paper_count=len(expected)); browser.close()
    except Exception as exc:
        result.update(status='FAIL', error=type(exc).__name__ + ': ' + str(exc)); raise
    finally:
        server.terminate(); server.wait(timeout=10)
        (args.output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('DELIVERY BROWSER: 4 checks passed; actual exports, no scientific accuracy claim')


if __name__ == '__main__':
    main()
