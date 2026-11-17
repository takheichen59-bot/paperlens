"""Independent transactional database. Never migrates the frozen M02 database."""
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import json,sqlite3,time
from .models import Paper,ScientificRecord,ParsedDocument
from .errors import PlatformError

def now():return datetime.now(timezone.utc).isoformat()
def encode(v):return json.dumps(v,ensure_ascii=False,allow_nan=False)
class Store:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with self.connection() as c:
   # Strictly separate database: refuse a legacy M02 database before any migration.
   existing={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if existing and 'schema_versions' not in existing:raise PlatformError('REFUSE_UNRELATED_DATABASE')
   version=c.execute('PRAGMA user_version').fetchone()[0]
   if version>1:raise PlatformError('UNSUPPORTED_DATABASE_VERSION')
   if version==0:
    sql=(Path(__file__).parent/'migrations'/'0001_platform.sql').read_text()
    c.executescript('BEGIN IMMEDIATE;\n'+sql+'\nPRAGMA application_id=1397510217;\nPRAGMA user_version=1;\nCOMMIT;')
   required={'papers','documents','extractions','parses','reviews','jobs','events','search_results','source_rates','schema_versions'}
   actual={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   if not required<=actual:raise PlatformError('DATABASE_SCHEMA_INCOMPLETE')
 @contextmanager
 def connection(self):
  c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=10000');c.execute('PRAGMA journal_mode=WAL')
  try:yield c;c.commit()
  except BaseException:c.rollback();raise
  finally:c.close()
 def upsert_paper(self,paper):
  with self.connection() as c:
   existing=c.execute('SELECT paper_id,metadata_json FROM papers WHERE paper_id=? OR (doi IS NOT NULL AND doi=?)',(paper.paper_id,paper.doi)).fetchone()
   if existing:
    old=Paper.model_validate_json(existing['metadata_json']);paper=paper.model_copy(update={'paper_id':existing['paper_id'],'sources':tuple(dict.fromkeys(old.sources+paper.sources))})
   c.execute('INSERT INTO papers(paper_id,doi,title,metadata_json) VALUES(?,?,?,?) ON CONFLICT(paper_id) DO UPDATE SET doi=excluded.doi,title=excluded.title,metadata_json=excluded.metadata_json',(paper.paper_id,paper.doi,paper.title,paper.model_dump_json()))
  return paper
 def paper(self,pid):
  with self.connection() as c:
   row=c.execute('SELECT * FROM papers WHERE paper_id=?',(pid,)).fetchone();return dict(row) if row else None
 def papers(self,limit=50,offset=0):
  with self.connection() as c:return [dict(r) for r in c.execute('SELECT * FROM papers ORDER BY rowid DESC LIMIT ? OFFSET ?',(limit,offset))]
 def count(self):
  with self.connection() as c:return c.execute('SELECT COUNT(*) FROM papers').fetchone()[0]
 def event(self,jid,event,payload):
  with self.connection() as c:c.execute('INSERT INTO events(job_id,event,payload_json,created_at) VALUES(?,?,?,?)',(jid,event,encode(payload),now()))
 def job_events(self,jid):
  with self.connection() as c:return [dict(r) for r in c.execute('SELECT * FROM events WHERE job_id=? ORDER BY event_id DESC LIMIT 100',(jid,))]
 def current_snapshot(self,paper_ids=()):
  # One read transaction for exports, comparisons and graph inputs.
  for r in self.papers(limit=100000):
   if paper_ids and r['paper_id'] not in paper_ids:continue
   try:self.ensure_current(r['paper_id'])
   except PlatformError:pass
  with self.connection() as c:
   c.execute('BEGIN');rows=list(c.execute('SELECT * FROM papers ORDER BY paper_id'));out=[]
   for r in rows:
    if paper_ids and r['paper_id'] not in paper_ids:continue
    e=c.execute("SELECT * FROM extractions WHERE document_id=? AND status!='STALE' ORDER BY rowid DESC LIMIT 1",(r['current_document'],)).fetchone()
    out.append({'paper':json.loads(r['metadata_json']),'access_status':r['access_status'],'document_id':r['current_document'],'extraction_id':e['extraction_id'] if e else None,'extraction':json.loads(e['payload_json']) if e else None})
   return out
 def current_review(self,eid):
  with self.connection() as c:
   row=c.execute('SELECT * FROM reviews WHERE extraction_id=? ORDER BY revision DESC LIMIT 1',(eid,)).fetchone();return dict(row) if row else None
 def save_document(self,pid,sha,path,kind,*,source_url='',license=None,method='user_upload'):
  did='doc:'+uuid4().hex
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');p=c.execute('SELECT current_document FROM papers WHERE paper_id=?',(pid,)).fetchone()
   if not p:raise PlatformError('PAPER_NOT_FOUND')
   old=c.execute('SELECT document_id FROM documents WHERE paper_id=? AND sha256=?',(pid,sha)).fetchone()
   if old:
    did=old['document_id']
    c.execute("UPDATE documents SET license=COALESCE(?,license),source_url=CASE WHEN ?!='' THEN ? ELSE source_url END WHERE document_id=?",(license,source_url,source_url,did))
   else:c.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)',(did,pid,sha,str(Path(path).resolve()),kind,license,source_url,method,Path(path).stat().st_size,now(),'CURRENT'))
   if p['current_document'] and p['current_document']!=did:
    c.execute("UPDATE documents SET status='STALE' WHERE document_id=?",(p['current_document'],));c.execute("UPDATE extractions SET status='STALE' WHERE document_id=?",(p['current_document'],));c.execute("UPDATE reviews SET status='STALE' WHERE extraction_id IN (SELECT extraction_id FROM extractions WHERE document_id=?)",(p['current_document'],))
   c.execute("UPDATE documents SET status='CURRENT' WHERE document_id=?",(did,));c.execute("UPDATE papers SET current_document=?,access_status='FULLTEXT_AVAILABLE' WHERE paper_id=?",(did,pid))
  return did
 def document(self,did):
  with self.connection() as c:
   r=c.execute('SELECT * FROM documents WHERE document_id=?',(did,)).fetchone();return dict(r) if r else None
 def ensure_current(self,pid):
  """External file changes invalidate dependent artifacts before use."""
  from .parsing import digest
  row=self.paper(pid)
  if not row or not row['current_document']:return
  doc=self.document(row['current_document'])
  try:valid=Path(doc['path']).is_file() and digest(doc['path'])==doc['sha256']
  except OSError:valid=False
  if valid:return
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE')
   c.execute("UPDATE documents SET status='STALE' WHERE document_id=?",(doc['document_id'],))
   c.execute("UPDATE extractions SET status='STALE' WHERE document_id=?",(doc['document_id'],))
   c.execute("UPDATE reviews SET status='STALE' WHERE extraction_id IN (SELECT extraction_id FROM extractions WHERE document_id=?)",(doc['document_id'],))
   c.execute("UPDATE papers SET current_document=NULL,access_status='SOURCE_NOT_AVAILABLE' WHERE paper_id=? AND current_document=?",(pid,doc['document_id']))
  raise PlatformError('DOCUMENT_FILE_CHANGED')
 def mark_unavailable(self,pid):
  with self.connection() as c:c.execute("UPDATE papers SET access_status='FULLTEXT_UNAVAILABLE' WHERE paper_id=? AND current_document IS NULL",(pid,))
 def save_parse(self,did,document):
  with self.connection() as c:c.execute('INSERT INTO parses VALUES(?,?,?,?,?) ON CONFLICT(document_id,parser_version) DO UPDATE SET payload_json=excluded.payload_json,status=excluded.status',('parse:'+uuid4().hex,did,document.parser_version,document.model_dump_json(),'NEEDS_REVIEW' if document.warnings else 'PARSED'))
 def latest_parse(self,did):
  with self.connection() as c:
   r=c.execute('SELECT payload_json FROM parses WHERE document_id=? ORDER BY rowid DESC LIMIT 1',(did,)).fetchone();return ParsedDocument.model_validate_json(r[0]) if r else None
 def save_extraction(self,did,record):
  eid='ext:'+uuid4().hex
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');current=c.execute('SELECT status,sha256 FROM documents WHERE document_id=?',(did,)).fetchone()
   if not current or current['status']!='CURRENT' or current['sha256']!=record.document_sha256:raise PlatformError('STALE_DOCUMENT')
   c.execute('INSERT INTO extractions VALUES(?,?,?,?,?,?,?)',(eid,did,record.model,record.extraction_version,record.model_dump_json(),record.validation_status.value,now()))
  return eid
 def extraction(self,pid):
  with self.connection() as c:
   r=c.execute("SELECT e.* FROM extractions e JOIN papers p ON p.current_document=e.document_id WHERE p.paper_id=? AND e.status!='STALE' ORDER BY e.rowid DESC LIMIT 1",(pid,)).fetchone();return dict(r) if r else None
 def history(self,pid):
  with self.connection() as c:return [dict(r) for r in c.execute('SELECT e.* FROM extractions e JOIN documents d ON d.document_id=e.document_id WHERE d.paper_id=? ORDER BY e.rowid DESC',(pid,))]
 def enqueue(self,kind,payload,*,idempotency_key=None,total=0):
  jid='job:'+uuid4().hex
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE')
   if idempotency_key:
    existing=c.execute('SELECT job_id FROM jobs WHERE idempotency_key=?',(idempotency_key,)).fetchone()
    if existing:return existing[0]
   c.execute('INSERT INTO jobs(job_id,kind,payload_json,status,total,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(jid,kind,encode(payload),'QUEUED',total,idempotency_key,now(),now()))
  return jid
 def claim(self,owner,lease_seconds=120):
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');c.execute("UPDATE jobs SET status='FAILED',error_code='ATTEMPTS_EXHAUSTED' WHERE status='RUNNING' AND lease_until<? AND attempts>=max_attempts",(time.time(),))
   row=c.execute("SELECT * FROM jobs WHERE (status='QUEUED' OR (status='RUNNING' AND lease_until<?)) AND attempts<max_attempts ORDER BY created_at LIMIT 1",(time.time(),)).fetchone()
   if not row:return None
   c.execute("UPDATE jobs SET status='RUNNING',owner=?,lease_until=?,attempts=attempts+1,updated_at=? WHERE job_id=?",(owner,time.time()+lease_seconds,now(),row['job_id']));result=dict(row);result['owner']=owner;result['attempts']+=1;return result
 def update_job(self,jid,owner,*,status=None,progress=None,result=None,error=None,lease_seconds=120):
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT owner,status FROM jobs WHERE job_id=?',(jid,)).fetchone()
   if not row or row['owner']!=owner or row['status']!='RUNNING':raise PlatformError('JOB_LEASE_LOST')
   c.execute('UPDATE jobs SET status=COALESCE(?,status),progress=COALESCE(?,progress),result_json=COALESCE(?,result_json),error_code=?,lease_until=?,updated_at=? WHERE job_id=?',(status,progress,encode(result) if result is not None else None,error,time.time()+lease_seconds,now(),jid))
 def pause(self,jid):
  with self.connection() as c:c.execute("UPDATE jobs SET status='PAUSED',updated_at=? WHERE job_id=? AND status IN ('QUEUED','RUNNING')",(now(),jid))
 def resume(self,jid):
  with self.connection() as c:c.execute("UPDATE jobs SET status='QUEUED',owner=NULL,lease_until=NULL,attempts=0,updated_at=? WHERE job_id=? AND status IN ('PAUSED','FAILED')",(now(),jid))
 def job(self,jid):
  with self.connection() as c:
   r=c.execute('SELECT * FROM jobs WHERE job_id=?',(jid,)).fetchone();return dict(r) if r else None
 def jobs(self):
  with self.connection() as c:return [dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100')]
 def save_search_results(self,jid,papers):
  for p in papers:
   p=self.upsert_paper(p)
   with self.connection() as c:c.execute('INSERT OR IGNORE INTO search_results VALUES(?,?)',(jid,p.paper_id))
 def search_results(self,jid):
  with self.connection() as c:return [dict(r) for r in c.execute('SELECT p.* FROM papers p JOIN search_results s ON p.paper_id=s.paper_id WHERE s.job_id=?',(jid,))]
 def reserve_source(self,provider,interval):
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT next_allowed FROM source_rates WHERE provider=?',(provider,)).fetchone();when=max(time.time(),r[0] if r else 0)
   c.execute('INSERT INTO source_rates VALUES(?,?) ON CONFLICT(provider) DO UPDATE SET next_allowed=excluded.next_allowed',(provider,when+interval));return max(0,when-time.time())
 def review(self,eid,revision,payload):
  with self.connection() as c:
   c.execute('BEGIN IMMEDIATE');e=c.execute('SELECT status FROM extractions WHERE extraction_id=?',(eid,)).fetchone()
   if not e or e['status']=='STALE':raise PlatformError('STALE_DOCUMENT')
   old=c.execute('SELECT MAX(revision) FROM reviews WHERE extraction_id=?',(eid,)).fetchone()[0] or 0
   if old!=revision:raise PlatformError('REVIEW_CONFLICT')
   c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?)',('review:'+uuid4().hex,eid,old+1,encode(payload),'NEEDS_REVIEW' if not payload.get('confirmed') else 'HUMAN_REVIEWED',now()))
  return old+1
