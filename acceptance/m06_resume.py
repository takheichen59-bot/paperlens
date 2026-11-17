import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import tempfile
from datetime import datetime,timezone,timedelta
from hashlib import sha256
from contracts import *
from storage import Database,PaperRepository
from checkpoints import ResumeStore,fingerprint

def setup(d):
    db=Database(Path(d)/'state.db')
    m=PaperMeta(paper_id='p',source_id='2401.00001',doi=None,title='Fixture',page_url='https://arxiv.org/abs/2401.00001',pdf_url='https://arxiv.org/pdf/2401.00001',version='v1',fetched_at=datetime.now(timezone.utc))
    PaperRepository(db).upsert(m,source=Source.ARXIV)
    return db,ResumeStore(db,Path(d)/'cache')
def artifact(d):
    p=Path(d)/'p.pdf';p.write_bytes(b'%PDF-fixture%%EOF')
    return DownloadArtifact(pdf_path=p,content_hash=sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,downloaded_at=datetime.now(timezone.utc))
def case_after_download():
    with tempfile.TemporaryDirectory() as d:
        db,s=setup(d);a=artifact(d);cfg=fingerprint('download','v1')
        s.start('p',Stage.DOWNLOAD,cfg);s.save('p',Stage.DOWNLOAD,cfg,a);s.finish('p',Stage.DOWNLOAD)
        db.close()
        with Database(Path(d)/'state.db') as reopened:
            assert ResumeStore(reopened,Path(d)/'cache').load('p',Stage.DOWNLOAD,cfg,DownloadArtifact)==a
def case_after_parse():
    with tempfile.TemporaryDirectory() as d:
        db,s=setup(d)
        with db:
            p=ParsedPaper(paper_id='p',pdf_hash='a'*64,pages=(),raw_blocks=(),cleaned_text='',sections=(),warnings=('empty_fixture',))
            cfg=fingerprint('parser-v1');s.start('p',Stage.PARSE,cfg);s.save('p',Stage.PARSE,cfg,p);s.finish('p',Stage.PARSE)
            assert s.load('p',Stage.PARSE,cfg,ParsedPaper)==p
            assert s.load('p',Stage.EXTRACT,cfg,ExtractionResult) is None
def case_completed():
    with tempfile.TemporaryDirectory() as d:
        db,s=setup(d)
        with db:
            a=artifact(d);cfg=fingerprint('v1');s.start('p',Stage.DOWNLOAD,cfg);s.save('p',Stage.DOWNLOAD,cfg,a);s.finish('p',Stage.DOWNLOAD)
            for _ in range(2):assert s.load('p',Stage.DOWNLOAD,cfg,DownloadArtifact)
            assert s.tasks.get_current('p',Stage.DOWNLOAD).attempts==1
def case_corrupt():
    with tempfile.TemporaryDirectory() as d:
        db,s=setup(d)
        with db:
            a=artifact(d);cfg=fingerprint('v1');s.start('p',Stage.DOWNLOAD,cfg);s.save('p',Stage.DOWNLOAD,cfg,a);s.finish('p',Stage.DOWNLOAD)
            a.pdf_path.write_bytes(b'bad');assert s.load('p',Stage.DOWNLOAD,cfg,DownloadArtifact) is None
            s.path('p',Stage.DOWNLOAD).write_text('{bad');assert s.load('p',Stage.DOWNLOAD,cfg,DownloadArtifact) is None
def case_version_and_recover():
    with tempfile.TemporaryDirectory() as d:
        db,s=setup(d)
        with db:
            cfg=fingerprint('v1');s.start('p',Stage.EXTRACT,cfg)
            assert s.recover(before=datetime.now(timezone.utc)+timedelta(seconds=1))==1
            assert s.tasks.get_current('p',Stage.EXTRACT).stage_status==StageStatus.PENDING
            s.start('p',Stage.DOWNLOAD,cfg);s.save('p',Stage.DOWNLOAD,cfg,artifact(d));s.finish('p',Stage.DOWNLOAD)
            assert s.load('p',Stage.DOWNLOAD,fingerprint('v2'),DownloadArtifact) is None
            assert s.load('p',Stage.DOWNLOAD,cfg,DownloadArtifact) is not None

if __name__ == "__main__":
    raise SystemExit(run_cases(['case_after_download', 'case_after_parse', 'case_completed', 'case_corrupt', 'case_version_and_recover'], globals()))
