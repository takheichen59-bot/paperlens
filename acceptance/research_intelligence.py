"""Five offline evidence-retrieval/comparison acceptance scenarios."""
from pathlib import Path
import copy, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from research.analysis import search, answer, graph, vector, compare

def record(id, material):
    s={"evidence_id":"e1","field":"chemicals","text":material+" was investigated.","page_start":2,"page_end":2,"block_id":"p2-b1","start_offset":0,"end_offset":len(material+" was investigated."),"section":"Results"}
    return {"paper_id":id,"id":id,"meta":{"title":material+" study"},"materials":[material],"methods":"","findings":"","conclusions":"","limitations":"","algorithms":[],"formulas":[],"experimental_data":[],"source_snippets":[s]}

def case_vectors():
    assert vector("graphene DFT")==vector("graphene DFT")
    assert len(vector(""))==0
    assert search("graphene",[record("1","graphene"),record("2","silicon")])[0]["id"]=="1"
def case_no_evidence():
    r=record("1","graphene");r["source_snippets"]=[]
    assert search("graphene",[r])==[]
def case_answer():
    r=record("1","graphene");a=answer("石墨烯",[r]);assert a["citations"][0]["evidence"]==r["source_snippets"][0]
    assert answer("unknownwordzz",[r])["citations"]==[]
def case_graph():
    r=record("1","graphene");g=graph([r]);assert len(g["edges"])==1
    assert g["edges"][0]["relation"]=="mentions" and g["edges"][0]["evidence_id"]=="e1"
def case_compare():
    r=record("1","graphene");original=copy.deepcopy(r);rows=compare([r]);assert r==original
    assert rows[0]["materials"]==["graphene"] and "不能直接" in rows[0]["caution"]

failed=0
for name in ["case_vectors","case_no_evidence","case_answer","case_graph","case_compare"]:
    try:globals()[name]();print("PASS",name)
    except Exception as exc:failed+=1;print("FAIL",name,type(exc).__name__)
print(f"INTELLIGENCE SUMMARY: {5-failed} passed, {failed} failed")
raise SystemExit(int(bool(failed)))
