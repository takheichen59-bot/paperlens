"""Fetch the small public CC-BY benchmark through the actual platform acquirer.

Only arXiv source URLs are accepted. This creates an explicit research manifest;
it does not import or mix either database or ScientificRecord payloads.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import httpx
from science_platform.acquisition import OfficialSourceAcquirer
from science_platform.models import FullTextLink


async def run(args):
    seeds = json.loads(args.source.read_text()); args.output.mkdir(parents=True, exist_ok=True)
    results = []; failures = []; receipts = []
    acquirer = OfficialSourceAcquirer(args.output / 'pdf', max_bytes=64 * 1024 * 1024)
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            for item in seeds:
                meta = dict(item['meta'])
                try:
                    if not re.fullmatch(r'https://arxiv\.org/abs/\d{4}\.\d{4,5}v\d+', meta['url']) or meta['pdf_url'] != meta['url'].replace('/abs/', '/pdf/'):
                        raise ValueError('Not a versioned official arXiv source')
                    page = await client.get(meta['url']); page.raise_for_status()
                    match = re.search(r'<div class="abs-license">\s*<a href="([^"]+)"', page.text)
                    license_url = match[1].replace('http:', 'https:') if match else ''
                    if license_url != meta['license_url'] or license_url != 'https://creativecommons.org/licenses/by/4.0/':
                        raise ValueError('Current CC-BY license did not match benchmark')
                    meta['license_checked_at'] = datetime.now(timezone.utc).isoformat()
                    receipt = await acquirer.acquire(FullTextLink(url=meta['pdf_url'], kind='pdf', access='OPEN_ACCESS', license=license_url))
                    receipts.append({'id': meta['id'], **receipt})
                    if receipt['sha256'] != meta['sha256']:
                        raise ValueError('Downloaded version differs from benchmark checksum')
                    meta['acquisition_method'] = receipt['acquisition_method']
                    meta['acquired_at'] = receipt['downloaded_at']
                    results.append({'meta': meta, 'pdf': str(Path(receipt['path']).relative_to(args.output))})
                    print('DOWNLOADED', meta['id'], receipt['bytes'], receipt['sha256'], flush=True)
                except Exception as exc:
                    failures.append({'id': meta.get('id'), 'reason': getattr(exc, 'code', type(exc).__name__)})
                    print('FAILED', meta.get('id'), failures[-1]['reason'], flush=True)
    finally:
        await acquirer.aclose()
    (args.output / 'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    (args.output / 'acquisition.json').write_text(json.dumps({'scope': 'OFFICIAL_ARXIV_CC_BY_PDFS_NOT_SEARCH_RESULTS',
        'downloaded': len(results), 'requested': len(seeds), 'receipts': receipts, 'failures': failures}, ensure_ascii=False, indent=2) + '\n')
    return int(bool(failures) or len(results) != len(seeds))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, default=Path('samples/research/real_role_corpus.json'))
    p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    args.output = args.output.resolve()
    return asyncio.run(run(args))


if __name__ == '__main__':
    raise SystemExit(main())
