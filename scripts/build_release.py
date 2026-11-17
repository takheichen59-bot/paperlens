"""Build the pure-Python wheel/source zip and SHA256SUMS. No runtime dependencies added."""
from pathlib import Path
import argparse,subprocess,sys,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1];VERSION='0.1.2';DIST=ROOT/'dist'

def wheel():
    subprocess.run([sys.executable,'-m','pip','wheel',str(ROOT),'--no-deps','--no-build-isolation','-w',str(DIST)],check=True)

def source():
    path=DIST/f'paperlens-{VERSION}-source.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        files=[ROOT/p for p in ('README.md','pyproject.toml','requirements-tested.txt','PLAN.md') if (ROOT/p).exists()]
        for folder in ('src','acceptance','samples','examples','scripts','docs','website'):
            files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and not any(x in p.parts for x in ('__pycache__','.git','node_modules','.leases','downloads')) and not any(x.endswith('.egg-info') for x in p.parts))
        for p in sorted(set(files)):
            if p.suffix not in ('.pyc','.pyo') and p.name!='.publish.lock':archive.write(p,Path('paperlens-0.1.2')/p.relative_to(ROOT))
    with zipfile.ZipFile(path) as archive:assert archive.testzip() is None
    print('Source zip:',path.name,path.stat().st_size,'bytes')

def hashes():
    names=[f'paper_extraction_contracts-{VERSION}-py3-none-any.whl',f'paperlens-{VERSION}-source.zip']
    values=[hashlib.sha256((DIST/n).read_bytes()).hexdigest()+'  '+n for n in names if (DIST/n).exists()]
    (DIST/'SHA256SUMS').write_text('\n'.join(values)+'\n');print('\n'.join(values))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--wheel-only',action='store_true');parser.add_argument('--source-only',action='store_true');a=parser.parse_args()
    DIST.mkdir(exist_ok=True)
    if not a.source_only:wheel()
    if not a.wheel_only:source()
    hashes()
