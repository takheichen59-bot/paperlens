"""Five independent batch/review/export scenarios, including real SIGKILL recovery."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json, multiprocessing, sys, time, zipfile
from xml.etree import ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from research.library import Library, current_output
from contracts.jsonl_schema import validate_record
from exports import parse_failure_line
from _research_fixture import synthetic_record


def items(directory, count):
    root=Path(directory); result=[]
    for i in range(count):
        path=root/f"input-{i}.fixture"; path.write_text(f"synthetic queue input {i}")
        result.append({"pdf":path,"meta":{"paper_id":f"test:{i}","id":f"test-{i}","title":f"Synthetic task {i}","url":""}})
    return result


def first_and_isolation():
    with TemporaryDirectory() as tmp:
        batch=items(tmp,3);lib=Library(Path(tmp)/"library")
        def adapter(path,meta):
            if meta["id"]=="test-1":raise RuntimeError("injected")
            return synthetic_record(path,meta)
        result=lib.run(batch,extractor=adapter)
        assert result["processed"]==2 and result["failed"]==1
        assert len(list(lib.records()))==2
        output=lib.export(Path(tmp)/"export"); lines=(Path(output["directory"])/"failures.jsonl").read_text().splitlines()
        assert len(lines)==1; parse_failure_line(json.loads(lines[0]))
        lib.run(batch,extractor=synthetic_record)
        assert not list((lib.directory/"failures").glob("*.json"))


def resume():
    with TemporaryDirectory() as tmp:
        batch=items(tmp,3);lib=Library(Path(tmp)/"library")
        assert lib.run(batch,extractor=synthetic_record,stop_after=1)["processed"]==1
        r=lib.run(batch,extractor=synthetic_record);assert r["resumed"]==1 and r["processed"]==2
        def forbidden(*args):raise AssertionError("completed task reprocessed")
        assert lib.run(batch,extractor=forbidden)["resumed"]==3


def invalidate_and_deduplicate():
    with TemporaryDirectory() as tmp:
        batch=items(tmp,2);lib=Library(Path(tmp)/"library");lib.run(batch,extractor=synthetic_record)
        Path(batch[0]["pdf"]).write_text("changed source content")
        r=lib.run(batch+[batch[1]],extractor=synthetic_record)
        assert r["processed"]==1 and r["resumed"]==1 and r["duplicates"]==1


def reviews_and_exports():
    with TemporaryDirectory() as tmp:
        lib=Library(Path(tmp)/"library");lib.run(items(tmp,2),extractor=synthetic_record)
        lib.review("test:0",edits={"findings":"Human revision"},decision="reviewed")
        first=next(r for r in lib.records() if r["paper_id"]=="test:0")
        assert first["findings"]!="Human revision" and first["review"]["edits"]["findings"]=="Human revision"
        out=Path(tmp)/"export";published=lib.export(out);assert current_output(out)==published
        folder=Path(published["directory"])
        assert len((folder/"research.jsonl").read_text().splitlines())==2
        assert len((folder/"review.jsonl").read_text().splitlines())==1
        for line in (folder/"results.jsonl").read_text().splitlines():assert validate_record(json.loads(line)).valid
        with zipfile.ZipFile(folder/"research.xlsx") as z:
            assert z.testzip() is None
            sheet=ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            assert len(sheet.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'))==3


def killed_child(directory,batch):
    Library(directory).run(batch,workers=2,extractor=synthetic_record)


def scale_and_kill_resume():
    with TemporaryDirectory() as tmp:
        batch=items(tmp,5000);directory=Path(tmp)/"library";lib=Library(directory)
        child=multiprocessing.Process(target=killed_child,args=(directory,batch));child.start()
        deadline=time.monotonic()+20
        while len(list((directory/"records").glob('*.json')))<20 and child.is_alive() and time.monotonic()<deadline:
            time.sleep(.01)
        assert child.is_alive(),"child finished before interruption probe"
        child.kill();child.join(10);assert child.exitcode==-9
        completed=len(list((directory/"records").glob('*.json')));assert completed>=1
        result=lib.run(batch,workers=2,extractor=synthetic_record)
        assert result["failed"]==0 and result["resumed"]>=completed
        assert result["processed"]+result["resumed"]==5000
        assert len(list(lib.records()))==5000
        print(f"SCALE DETAIL: 5000 synthetic tasks; killed=-9; resumed={result['resumed']}; processed={result['processed']}; failed=0")


failed=0
for name in ["first_and_isolation","resume","invalidate_and_deduplicate","reviews_and_exports","scale_and_kill_resume"]:
    try:globals()[name]();print("PASS",name,flush=True)
    except Exception as exc:failed+=1;print("FAIL",name,type(exc).__name__,str(exc),flush=True)
print(f"BATCH SUMMARY: {5-failed} passed, {failed} failed")
raise SystemExit(int(bool(failed)))
