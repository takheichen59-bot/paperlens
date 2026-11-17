import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from _support import run_cases
import tempfile
from unittest.mock import patch
from contracts import *
from storage import Database,PaperRepository,ResultRepository,ErrorRepository,TaskRepository
from exports import (export_results,parse_failure_line,FailureStatus,is_warning_classification_error,
    open_current_snapshot,read_current_results,read_current_warnings_by_severity,
    read_current_review,read_current_failures,prune_versions)
from exports import snapshots
from exports.jsonl import save_skip_info
from extractors.composite import CompositeExtractor,status_for
from _pipeline_fixtures import metadata
from _text_fixtures import paper,extract_with_view

FULL=['Methods','Titanium dioxide was prepared at 180 C.','Conclusions','The coating improved corrosion resistance.']

def seed(db,lines,index=1):
    meta=metadata(index);PaperRepository(db).upsert(meta,source=Source.ARXIV)
    r=extract_with_view(CompositeExtractor(),paper(lines))
    ResultRepository(db).upsert(meta.paper_id,r,status=status_for(r))
    return r

def case_alignment():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,FULL,1);seed(db,FULL[:2],2)
        skipped=metadata(3);PaperRepository(db).upsert(skipped,source=Source.ARXIV)
        TaskRepository(db).upsert_task(TaskRecord(task_id='skip',paper_id=skipped.paper_id,stage=Stage.DOWNLOAD,
            stage_status=StageStatus.SKIPPED,attempts=0,config_fingerprint='a'*64,error=ErrorKind.INVALID_DOWNLOAD))
        save_skip_info(db,skipped.paper_id,{'status':'skipped','skipped_reason':'size_limit','file_bytes':200000000,'file_bytes_source':'content_length'})
        export_results(db,out)
        with open_current_snapshot(out) as s:
            main=read_current_results(out,snapshot=s);warnings=read_current_warnings_by_severity(out,snapshot=s)
            main_ids={row[0] for row in s.results_index};warning_ids={row.paper_id for row in warnings}
            assert len(main)==len(warnings)==2
            assert main_ids==warning_ids=={metadata(1).paper_id,metadata(2).paper_id}
            assert skipped.paper_id not in main_ids and skipped.paper_id not in warning_ids
            for i,(r,w) in enumerate(zip(main,warnings)):
                assert w.result_index==i and r.status==w.status
                assert w.result_sha256==s.results_index[i][2] and w.paper_id==s.results_index[i][0]
            failures=read_current_failures(out,snapshot=s)
            assert len(failures)==1 and failures[0].status==FailureStatus.SKIPPED

def case_complete():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,FULL);s=export_results(db,out);records=read_current_results(out)
        assert s.records==1 and records[0].status==ResultStatus.SUCCESS
        assert validate_record(records[0].model_dump(mode='json')).valid
        assert not read_current_review(out)

def case_partial():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,FULL[:2]);s=export_results(db,out)
        assert read_current_results(out)[0].status==ResultStatus.PARTIAL and s.review==1
        assert 'missing_field:conclusions' in read_current_review(out)[0]['reasons']

def case_failure():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,['No technical content is available in this document.'])
        ErrorRepository(db).append(ContractError(Stage.PARSE,ErrorKind.PARSE_FAILED,False,cause=ValueError('SECRET')),paper_id=metadata().paper_id)
        s=export_results(db,out);assert read_current_results(out)[0].status==ResultStatus.FAILED
        failures=read_current_failures(out)
        assert s.failed==2 and len(failures)==2 and all('SECRET' not in str(r) for r in failures)
        assert all(r.attempts>=0 for r in failures)

def case_repeat_and_latest():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';r=seed(db,FULL);export_results(db,out)
        first=read_current_results(out)
        export_results(db,out);assert read_current_results(out)==first
        newer=r.model_copy(update={'extraction_method':'new-version'})
        ResultRepository(db).upsert(metadata().paper_id,newer,status=ResultStatus.SUCCESS)
        export_results(db,out);export_results(db,out)
        assert len(read_current_results(out))==1 and read_current_results(out)[0].extraction_method=='new-version'
        versions=sorted(p for p in (out/'versions').iterdir() if not p.name.startswith('.'))
        assert len(versions)==4
        with open_current_snapshot(out) as s:current=s.version_id
        removed=prune_versions(out,keep=3)
        remaining={p.name for p in (out/'versions').iterdir() if not p.name.startswith('.')}
        assert len(remaining)==3 and current in remaining and removed==(versions[0].name,)

def case_failure_line_parser():
    with tempfile.TemporaryDirectory():
        skipped=parse_failure_line({'status':'skipped','paper_id':'p','stage':'download','error_kind':'invalid_download','attempts':1,'skipped_reason':'size_limit','file_bytes':129565883,'file_bytes_source':'content_length'})
        base={'status':'failed','paper_id':'p','stage':'validate','error_kind':'validation_failed','attempts':1}
        target=parse_failure_line({**base,'reason':'warning_classification_error'})
        assert target.reason=='warning_classification_error' and target.error_kind==ErrorKind.VALIDATION_FAILED
        assert is_warning_classification_error(target)
        for extra in ({},{'reason':None},{'reason':'other'}):
            r=parse_failure_line({**base,**extra})
            assert r.reason==extra.get('reason') and not is_warning_classification_error(r)
        assert not is_warning_classification_error(parse_failure_line({**base,'reason':'warning_classification_error','error_kind':'extract_failed'}))
        assert skipped.status==FailureStatus.SKIPPED and skipped.file_bytes==129565883
        assert not is_warning_classification_error(skipped)
        assert parse_failure_line({'paper_id':None,'stage':'parse','error_kind':'parse_failed'}).status==FailureStatus.FAILED
        for bad in ({'status':'skipped','paper_id':'p','stage':'download'}, {**base,'reason':12}):
            try:parse_failure_line(bad)
            except ValueError:pass
            else:raise AssertionError('Invalid failure accepted')

def fault_scenario(phase):
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,FULL)
        replace=snapshots.os.replace;write=snapshots._write_jsonl
        def injected_replace(src,dst):
            if (phase=='version' and Path(src).name.startswith('.staging-')) or (phase=='pointer' and Path(dst).name=='CURRENT'):
                raise OSError('injected publish fault')
            return replace(src,dst)
        def injected_write(path,rows):
            if Path(path).name==phase:raise OSError('injected write fault')
            return write(path,rows)
        def attempt():
            with patch('exports.snapshots.os.replace',side_effect=injected_replace),patch('exports.snapshots._write_jsonl',side_effect=injected_write):
                try:export_results(db,out)
                except OSError:pass
                else:raise AssertionError('Fault not raised')
            assert not list(out.glob('*.tmp')) and not list((out/'versions').glob('.staging-*'))
        # First publish fails from an empty output root: no partial public generation.
        attempt();assert not (out/'CURRENT').exists() and not list((out/'versions').iterdir())
        export_results(db,out)
        with open_current_snapshot(out) as before:
            rows=read_current_results(out,snapshot=before);warnings=read_current_warnings_by_severity(out,snapshot=before)
            attempt()
            with open_current_snapshot(out) as after:
                assert before.version_id==after.version_id
                assert read_current_results(out,snapshot=after)==rows
                assert read_current_warnings_by_severity(out,snapshot=after)==warnings

def case_interruption():fault_scenario('version')
def case_main_write_failure():fault_scenario('results.jsonl')
def case_severity_write_failure():fault_scenario('warnings_by_severity.jsonl')
def case_pointer_failure():fault_scenario('pointer')

def case_11a_snapshot_consistency():
    with tempfile.TemporaryDirectory() as d,Database(Path(d)/'db') as db:
        out=Path(d)/'out';seed(db,FULL[:2]);export_results(db,out)
        with open_current_snapshot(out) as old:
            rows=read_current_results(out,snapshot=old)
            assert rows[0].status==ResultStatus.PARTIAL and old.published_at
            seed(db,FULL);export_results(db,out)
            warnings=read_current_warnings_by_severity(out,snapshot=old)
            assert warnings[0].status==rows[0].status==ResultStatus.PARTIAL
            assert warnings[0].result_sha256==old.results_index[0][2]
            assert read_current_results(out,snapshot=old)==rows
            with open_current_snapshot(out) as new:
                assert new.version_id!=old.version_id
                assert read_current_results(out,snapshot=new)[0].status==ResultStatus.SUCCESS

def case_11b_destination_rejection():
    with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b,Database(Path(a)/'db') as db:
        out_a=Path(a)/'out';out_b=Path(b)/'out';seed(db,FULL)
        export_results(db,out_a);export_results(db,out_b)
        with open_current_snapshot(out_a) as s:
            for reader in (read_current_results,read_current_warnings_by_severity):
                assert reader(out_a,snapshot=s)
                try:reader(out_b,snapshot=s)
                except ValueError as exc:assert str(out_a) in str(exc) and str(out_b) in str(exc)
                else:raise AssertionError('Cross-destination snapshot accepted')

def case_snapshot():
    failed=[]
    for name,case in [('11a',case_11a_snapshot_consistency),('11b',case_11b_destination_rejection)]:
        try:case()
        except Exception as exc:
            print(f'FAIL {name}: {type(exc).__name__}');failed.append(name)
        else:print(f'PASS {name}')
    assert not failed,','.join(failed)

if __name__ == '__main__':
    raise SystemExit(run_cases(['case_alignment','case_complete','case_partial','case_failure',
        'case_repeat_and_latest','case_failure_line_parser','case_interruption','case_main_write_failure',
        'case_severity_write_failure','case_pointer_failure','case_snapshot'],globals()))
