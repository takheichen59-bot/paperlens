"""Synthetic queue fixtures; never presented as real scientific-quality evidence."""
from hashlib import sha256


def synthetic_record(path, meta):
    values = {"chemicals": "graphene", "methods": "Graphene was measured.",
              "conclusions": "In conclusion, graphene is stable.", "findings": "The results show improved strength."}
    blocks = []; snippets = []; eligible = []
    for index, (field, text) in enumerate(values.items(), 1):
        bid = "b" + str(index); blocks.append({"block_id": bid, "page": 1, "text": text})
        eligible.append({"block_id": bid, "start": 0, "end": len(text), "section_kind": "results"})
        snippets.append({"evidence_id": "e"+str(index), "field": field, "text": text,
            "block_id": bid, "start_offset": 0, "end_offset": len(text), "page_start": 1, "page_end": 1,
            "section": "Results", "section_kind": "results", "strategy": "synthetic-engineering-fixture"})
    legacy_snippets = [{k:v for k,v in s.items() if k not in {"evidence_id", "section_kind"}} for s in snippets if s["field"] != "findings"]
    return {"schema_version":"research-1", "paper_id":meta["paper_id"], "id":meta["id"], "meta":meta,
        "pdf_hash":sha256(path.read_bytes()).hexdigest(), "parser_version":"synthetic-fixture", "extractor_version":"synthetic-fixture",
        "created_at":"2026-11-16T00:00:00+00:00", "materials":["graphene"], "methods":values["methods"],
        "findings":values["findings"], "conclusions":values["conclusions"], "algorithms":[], "formulas":[],
        "experimental_data":[], "limitations":"", "source_snippets":snippets, "raw_blocks":blocks,
        "eligible_ranges":eligible, "status":"success", "review_status":"unreviewed", "warnings":[],
        "legacy_record":{"doi":None,"title":meta["title"],"source_url":meta.get("url",""),"chemicals":["graphene"],
            "methods":values["methods"],"conclusions":values["conclusions"],"source_snippets":legacy_snippets,
            "status":"success","extraction_method":"synthetic-engineering-fixture"}}
