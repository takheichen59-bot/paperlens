"""Conservative pre-push audit. Only report paths and finding categories."""
from pathlib import Path
import json,re,sys,subprocess
root=Path(__file__).resolve().parents[1]
patterns={'github_token':re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{35,})'),'model_key':re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}'),'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),'aws_access_id':re.compile(rb'\bAKIA[A-Z0-9]{16}\b')}
findings=[]
paths=[p for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts and '__pycache__' not in p.parts and '.egg-info' not in str(p) and 'build' not in p.relative_to(root).parts]
for p in paths:
 rel=p.relative_to(root)
 if rel.name=='.env' or rel.suffix in {'.db','.sqlite','.sqlite3','.pem','.key'}:findings.append({'file':str(rel),'kind':'excluded_runtime_file'})
 data=p.read_bytes()
 for kind,pattern in patterns.items():
  if pattern.search(data):findings.append({'file':str(rel),'kind':kind})
 if rel.suffix=='.json':
  try:
   def walk(value):
    if isinstance(value,dict):
     for k,v in value.items():
      if k.casefold() in {'siwc_bypass_bearer_token','api_key','access_token','refresh_token','client_secret'} and isinstance(v,str) and v and v not in {'NOT_CONFIGURED','fixture','test'}:findings.append({'file':str(rel),'kind':'credential_field'})
      walk(v)
    elif isinstance(value,list):
     for x in value:walk(x)
   walk(json.loads(data))
  except (ValueError,UnicodeDecodeError):pass
print(json.dumps({'files_scanned':len(paths),'findings':findings},ensure_ascii=False,indent=2))
raise SystemExit(bool(findings))
