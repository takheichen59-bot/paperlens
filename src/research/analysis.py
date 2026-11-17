"""Deterministic sparse-vector retrieval and cited comparisons; no language model."""
from __future__ import annotations
from collections import Counter
import hashlib, math, re

DIMENSIONS = 2048
STOP = frozenset("the a an and of to in for by with is are was were this that from on as at we our it be or these which have has using used study paper show results method methods".split())
ALIASES = {"石墨烯": "graphene", "密度泛函": "density functional DFT", "分子动力学": "molecular dynamics",
           "钙钛矿": "perovskite", "神经网络": "neural network", "有限元": "finite element",
           "锂": "lithium", "电导率": "conductivity", "带隙": "band gap", "强度": "strength"}


def tokens(text):
    for chinese, english in ALIASES.items():
        text = text.replace(chinese, " " + english + " ")
    return [x for x in re.findall(r"[a-z][a-z0-9-]{1,}", text.lower()) if x not in STOP]


def vector(text):
    terms = tokens(text)
    features = Counter(terms + [a + "_" + b for a, b in zip(terms, terms[1:])])
    result = {}
    for feature, count in features.items():
        h = hashlib.sha256(feature.encode()).digest()
        index = int.from_bytes(h[:4], "little") % DIMENSIONS
        sign = 1 if h[4] & 1 else -1
        result[index] = result.get(index, 0) + sign * (1 + math.log(count))
    norm = math.sqrt(sum(x*x for x in result.values()))
    return {k: v/norm for k, v in result.items()} if norm else {}


def search(query, records, limit=10):
    if not query.strip() or not 1 <= limit <= 100:
        return []
    q = vector(query); terms = set(tokens(query)); found = []
    for record in records:
        title = record.get("meta", {}).get("title", "")
        text = " ".join([title]*3 + [" ".join(record["materials"])]*3 +
            [record["methods"], record["findings"], record["conclusions"], record["limitations"]] +
            [a["name"] for a in record["algorithms"]])
        document = vector(text)
        cosine = sum(weight * document.get(index, 0) for index, weight in q.items())
        # Lexical overlap is required: hash collisions alone cannot fabricate a hit.
        overlap = terms.intersection(tokens(text))
        if not overlap:
            continue
        snippets = [s for s in record["source_snippets"] if terms.intersection(tokens(s["text"]))]
        if not snippets:
            continue
        found.append({"paper_id": record["paper_id"], "id": record["id"], "title": title,
            "score": round(cosine + len(overlap)/max(1,len(terms)), 6),
            "matched_terms": sorted(overlap), "evidence": snippets[:3]})
    return sorted(found, key=lambda x: (-x["score"], x["paper_id"]))[:limit]


def answer(query, records):
    hits = search(query, records, limit=5)
    return {"mode": "cited-retrieval-no-llm", "query": query,
        "message": "以下为论文原文证据；未生成跨条件的因果结论。" if hits else "未检索到可引用证据，请换用英文术语或更宽的主题。",
        "citations": [{"paper_id": h["paper_id"], "id": h["id"], "title": h["title"],
                       "evidence": h["evidence"][0]} for h in hits]}


def compare(records):
    return [{"paper_id": r["paper_id"], "id": r["id"], "title": r["meta"].get("title", ""),
        "materials": r["materials"], "methods": r["methods"], "algorithms": [a["name"] for a in r["algorithms"]],
        "findings": r["findings"], "conclusions": r["conclusions"], "limitations": r["limitations"],
        "experimental_data": r["experimental_data"], "formulas": r["formulas"],
        "evidence_count": len(r["source_snippets"]),
        "caution": "实验条件与单位未归一化，数值不能直接用于优劣排名。"} for r in records]


def graph(records):
    nodes, edges = {}, []
    for record in records:
        pid = record["paper_id"]
        nodes[pid] = {"id": pid, "kind": "paper", "label": record["meta"].get("title",record["id"])}
        candidates = [("material", v) for v in record["materials"]] + [("algorithm", a["name"]) for a in record["algorithms"]]
        for kind, value in candidates:
            if kind == "material":
                evidence = next((s for s in record["source_snippets"] if s["field"] == "chemicals" and value.casefold() in s["text"].casefold()), None)
            else:
                algorithm = next(a for a in record["algorithms"] if a["name"] == value)
                evidence = next((s for s in record["source_snippets"] if s["evidence_id"] in algorithm["evidence_ids"]), None)
            if evidence is None:
                continue
            key = kind + ":" + value.casefold()
            nodes[key] = {"id": key, "kind": kind, "label": value}
            edges.append({"source": pid, "target": key, "relation": "mentions", "evidence_id": evidence["evidence_id"]})
    return {"semantics": "正文提及关系，不代表使用、性能提升或因果关系", "nodes": list(nodes.values()), "edges": edges}
