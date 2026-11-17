"""Build a complete installable research workspace without changing legacy artifacts."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT.parent/'sites/matterlens';VERSION='0.2.0'
subprocess.run([sys.executable,'-m','pip','wheel',str(ROOT),'--no-deps','--no-build-isolation','-w',str(ROOT/'dist')],check=True)
wheel=ROOT/'dist'/f'paper_extraction_contracts-{VERSION}-py3-none-any.whl';shutil.copyfile(wheel,SITE/'downloads'/wheel.name)
source=ROOT/'dist'/f'matterlens-research-{VERSION}-source.zip'
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as archive:
 for directory in ('src','acceptance','samples','scripts','docs'):
  for path in sorted((ROOT/directory).rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts and not any(p.endswith('.egg-info') for p in path.parts) and path.suffix not in {'.pyc','.pyo'}:
    archive.write(path,str(path.relative_to(ROOT)))
 for name in ('pyproject.toml','README.md','requirements-tested.txt'):
  if (ROOT/name).exists():archive.write(ROOT/name,name)
 for name in ('build.mjs','package.json','README.md','verify-site.mjs','verify-phase1.mjs','verify-research.mjs'):
  archive.write(SITE/name,'website/'+name)
 for directory in ('web_assets','worker','fixtures'):
  for path in sorted((SITE/directory).rglob('*')):
   if path.is_file():archive.write(path,'website/'+str(path.relative_to(SITE)))
 archive.writestr('website/.openai/hosting.json',json.dumps({'d1':None,'r2':'BUCKET'})+'\n')
 for path in sorted((SITE/'downloads').iterdir()):
  if path.name.startswith('research20-') or path.name in {'RESEARCH_DELIVERY.md','RESEARCH_REPORT.md'}:
   archive.write(path,'website/downloads/'+path.name)
 archive.writestr('website/.gitignore','dist/\nwork/\nnode_modules/\n')
 assert archive.testzip() is None
shutil.copyfile(source,SITE/'downloads/matterlens-research-source.zip')
names=[wheel.name,'matterlens-research-source.zip',*[p.name for p in sorted((SITE/'downloads').glob('research20-*'))]]
lines=[hashlib.sha256((SITE/'downloads'/name).read_bytes()).hexdigest()+'  '+name for name in names]
(ROOT/'dist/RESEARCH_SHA256SUMS').write_text('\n'.join(lines)+'\n');shutil.copyfile(ROOT/'dist/RESEARCH_SHA256SUMS',SITE/'downloads/RESEARCH_SHA256SUMS')
print('RESEARCH RELEASE:',wheel.stat().st_size,'byte wheel;',source.stat().st_size,'byte source ZIP;',len(lines),'checksums')
