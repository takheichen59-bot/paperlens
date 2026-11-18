"""Portable reading assets over the separate, source-mapped reading layer.

These renderers never rewrite research-1 fields or mark a paper reviewed.  The
Chinese source review is an explicitly labelled assistant overlay; rule-only
records retain their missing/not-applicable reasons instead of invented prose.
"""
from __future__ import annotations

from collections import defaultdict
from html import escape
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape as xml_escape
import json
import re
import zipfile

from .reading import normalize_text, scientific_title, validate_reading


NOTICE = "中文卡片为助手对照本篇原PDF整理的来源复核层，不是规则自动摘要，也不是独立专家金标准；原自动结果及用户复核状态保留。"
RULE_NOTICE = "本篇没有助手来源复核层；以下仅展示规则候选及缺失原因，尚未核实科学内容或方法顺序。"
STATUS = "用户复核：unreviewed · 科研准确性：未独立评估"
CLAIM_FIELDS = (
    ("question", "研究问题"), ("objects", "研究对象"), ("methods", "方法路线"),
    ("steps", "来源支持的研究步骤"), ("arguments", "论证路径"),
    ("findings", "主要发现"), ("conclusion", "作者结论"),
    ("author_limitations", "作者明确局限"), ("boundaries", "助手阅读边界"),
    ("suggestions", "助手建议的借鉴方向"), ("numbers", "关键数值"),
)
TYPE_LABELS = {
    "perspective_or_review": "观点 / 综述（规则候选）",
    "computational": "计算研究（规则候选）",
    "mixed_computational_experimental": "计算与实验（规则候选）",
    "experimental_or_unresolved": "实验或待判定（规则候选）",
}


def _text(value):
    return normalize_text(str(value)) if value is not None else ""


def _snapshot(records):
    records = list(records)
    for record in records:
        if record.get("reading_card"):
            validate_reading(record)
    return records


def _card(record):
    layer = record.get("reading_card") or {}
    review = layer.get("source_review")
    # validate_reading above rejects invalid provenance and unsupported claims.
    assisted = bool(review)
    review = review or {}
    evidence = {s["id"]: s for s in layer.get("evidence", [])}
    values = {name: list(review.get(name, [])) for name, _ in CLAIM_FIELDS}
    missing = {}
    if not assisted:
        for field, target in (("question", "question"), ("methods", "methods"),
                              ("findings", "findings"), ("conclusions", "conclusion"),
                              ("limitations", "author_limitations")):
            value = layer.get("fields", {}).get(field, {})
            values[target] = [{"text": evidence[eid]["text"], "evidence_ids": [eid],
                               "kind": "规则候选"}
                              for eid in value.get("evidence_ids", []) if eid in evidence]
            if not values[target]:
                missing[target] = value.get("reason") or "阅读层未执行，无法判断该字段是否缺失。"
        values["objects"] = [{"text": item["name"] + "（" + item.get("role", "角色未核实") + "）",
                              "evidence_ids": item.get("evidence_ids", [])}
                             for item in layer.get("objects", [])]
        if not values["objects"]:
            missing["objects"] = "规则未定位到有来源的研究对象；需要原文复核，未使用背景材料补齐。"
        missing["steps"] = "规则仅识别方法线索，尚未核实可复述的步骤顺序。"
        missing["boundaries"] = "助手来源复核未执行；规则候选不能代替对原文的科学判断。"
        missing["suggestions"] = "助手来源复核未执行，未生成研究借鉴建议。"
    elif not values["author_limitations"]:
        missing["author_limitations"] = "来源复核层未列出作者明确限制；不等于论文没有局限。"
    perspective = bool(values["arguments"]) or layer.get("article_type", {}).get("label") == "perspective_or_review"
    if perspective:
        missing["methods"] = "观点 / 综述型讨论，实验操作流程不适用；请读论证路径。"
        missing["findings"] = "未按原创实验结果模板填充；本卡呈现来源支持的论点。"
    elif not values["steps"]:
        missing.setdefault("steps", "未提供已核对的步骤顺序，未按方法关键词推断操作流程。")
    for name, _ in CLAIM_FIELDS:
        if not values[name] and name not in missing:
            missing[name] = "来源复核层未提供此项，未自动补写。" if assisted else "阅读层未执行或未提供此项。"
    return {
        "record": record, "layer": layer, "review": review, "evidence": evidence,
        "id": str(record.get("id") or record.get("paper_id", "未提供论文ID")),
        "title": scientific_title(layer.get("title") or record.get("meta", {}).get("title", "未提供标题")),
        "title_zh": review.get("title_zh", ""), "type": review.get("type_zh") or
            TYPE_LABELS.get(layer.get("article_type", {}).get("label"), "类型待核实"),
        "assisted": assisted, "perspective": perspective, "values": values, "missing": missing,
        "notice": review.get("notice", NOTICE) if assisted else RULE_NOTICE,
    }


def _pages(card, ids):
    return sorted({p for eid in ids for p in card["evidence"].get(eid, {}).get("pages", [])})


def _page_label(pages):
    return ",".join(str(p) for p in pages)


def _citation(card, claim, html=False):
    pages = _pages(card, claim.get("evidence_ids", []))
    if not pages:
        return ""
    label = "［p." + _page_label(pages) + "］"
    if not html:
        return label
    target = "e-" + card["id"] + "-" + claim["evidence_ids"][0]
    return '<a class="citation" href="#' + escape(target, quote=True) + '">' + escape(label) + "</a>"


def _joined(card, name):
    return "\n".join(_text(c["text"]) + " " + _citation(card, c) for c in card["values"][name]) or card["missing"][name]


def _claims_html(card, name, *, portable=False, limit=None, heading=None):
    claims = card["values"][name]
    if limit is not None:
        claims = claims[:limit]
    title = heading or dict(CLAIM_FIELDS)[name]
    out = ['<section class="field"><h3>' + escape(title) + "</h3>"]
    if not claims:
        out.append('<p class="muted">' + escape(card["missing"][name]) + "</p>")
    else:
        tag = "ol" if name in {"steps", "arguments"} else "ul" if len(claims) > 1 else "div"
        out.append("<" + tag + ">")
        for claim in claims:
            kind = (str(claim.get("kind", "")) + "：") if claim.get("kind") else ""
            body = escape(kind + _text(claim["text"])) + " " + _citation(card, claim, portable)
            elem = "li" if tag in {"ol", "ul"} else "p"
            out.append("<" + elem + ">" + body + "</" + elem + ">")
        out.append("</" + tag + ">")
    out.append("</section>")
    return "".join(out)


def _number_table(card, *, portable=False):
    numbers = card["values"]["numbers"]
    out = ['<section class="numbers"><h3>关键数值与适用条件</h3>']
    if not numbers:
        reason = ("本篇按观点 / 综述阅读；未列为本文实验或模拟数值结果。" if card["perspective"] else
                  "未提供对象、物理量、条件和归属均明确的来源复核数值；未将未绑定候选填入关键表。")
        return "".join(out) + '<p class="muted">' + reason + "</p></section>"
    if portable:
        out.append('<div class="table-scroll">')
    out.append('<table class="number-table"><thead><tr><th class="object">对象 / 物理量</th><th class="value">值与单位</th><th class="conditions">条件 / 归属 / 来源</th></tr></thead><tbody>')
    for n in numbers:
        conditions = _text(n.get("conditions"))
        if n.get("comparison_baseline"):
            conditions += "；比较基准：" + _text(n["comparison_baseline"])
        out.append('<tr><td class="object">' + escape(_text(n.get("object"))) + "<br/>" + escape(_text(n.get("quantity"))) +
                   '</td><td class="value">' + escape(_text(n.get("value")) + " " + _text(n.get("unit"))) +
                   '</td><td class="conditions">' + escape(conditions) + "<br/>" + escape(_text(n.get("ownership"))) + " " +
                   _citation(card, n, portable) + "</td></tr>")
    return "".join(out) + "</tbody></table>" + ("</div>" if portable else "") + "</section>"


def _card_html(card, *, portable=False, part=None):
    origin = "助手来源复核导读" if card["assisted"] else "规则候选 · 未执行助手来源复核"
    out = ['<article class="card" id="paper-' + escape(card["id"], quote=True) + '">',
           '<p class="eyebrow">PAPERLENS · 研究阅读卡片</p>',
           "<h1>" + escape(card["title"]) + "</h1>"]
    if card["title_zh"]:
        out.append('<h2 class="subtitle">' + escape(card["title_zh"]) + "</h2>")
    out.append('<p class="identity">' + escape(card["id"] + " · " + card["type"]) + "</p>")
    if part == 2:
        out.append('<p class="notice">续页 · 结论、数值与阅读边界。' + escape(origin) + "；" + STATUS + "</p>")
    else:
        out.append('<p class="notice">' + escape(origin + "。" + card["notice"]) + "<br/>" + STATUS + "</p>")
    if part != 2:
        for name in ("question", "objects", "methods"):
            out.append(_claims_html(card, name, portable=portable))
        route = "arguments" if card["perspective"] else "steps"
        out.append(_claims_html(card, route, portable=portable))
        if card["perspective"]:
            out.append(_claims_html(card, "findings", portable=portable, heading="结果栏目适用性"))
        else:
            out.append(_claims_html(card, "findings", portable=portable, limit=3))
    if part == 1:
        return "".join(out) + '<p class="muted continuation">下一页：作者结论、关键数值、局限与助手阅读边界。</p></article>'
    out.append(_claims_html(card, "conclusion", portable=portable))
    out.append(_number_table(card, portable=portable))
    for name in ("author_limitations", "boundaries", "suggestions"):
        out.append(_claims_html(card, name, portable=portable))
    meta = card["record"].get("meta", {})
    url = meta.get("pdf_url") or meta.get("url") or ""
    if url:
        out.append('<p class="source-link">原文：<a href="' + escape(url, quote=True) + '">' + escape(url) + "</a> · 许可：" +
                   escape(meta.get("license_url") or "未提供，需另行核实") + "</p>")
    if card["review"].get("unresolved_claims"):
        out.append('<p class="notice">仍有来源未解决的复核项；未将其加入上方来源支持的正文。详见审计表。</p>')
    out.append("</article>")
    return "".join(out)


def _overview_html(cards, *, portable=False):
    out = ['<article class="overview" id="overview"><p class="eyebrow">PAPERLENS · 批量阅读入口</p>',
           '<h1>从研究问题走向原文证据</h1>',
           '<p class="lead">不同类型论文并列阅读，按研究对象、路线和内容判断用途；不做数值排名。</p>',
           '<p class="notice">本报告是处理与阅读卡片，不是原始论文。中文内容为助手来源复核层，规则候选与历史原字段分别保留。用户复核均为 unreviewed；没有独立科研准确率金标准。</p>',
           '<div class="table-scroll">' if portable else "",
           '<table class="overview-table"><thead><tr><th class="paper">论文与类型</th><th class="route">对象与路线</th><th class="core">核心内容与待核情况</th></tr></thead><tbody>']
    for card in cards:
        name = card["title_zh"] or card["title"]
        link = '<a href="#paper-' + escape(card["id"], quote=True) + '">' + escape(card["id"]) + "</a>" if portable else escape(card["id"])
        route = "arguments" if card["perspective"] else "methods"
        result = "arguments" if card["perspective"] else "findings"
        core = card["values"][result][:1]
        text = _text(core[0]["text"]) if core else card["missing"][result]
        route_text = _joined(card, route)
        if card["perspective"]:
            route_text = "观点 / 综述：论证路径见卡片；实验流程不适用。"
        out.append('<tr><td class="paper"><strong>' + escape(name) + "</strong><br/>" + link + "<br/>" + escape(card["type"]) +
                   '</td><td class="route">' + escape(_joined(card, "objects")) + "<br/>" + escape(route_text) +
                   '</td><td class="core">' + escape(text) + "<br/><span class=\"muted\">" +
                   ("助手来源复核；待用户核验。" if card["assisted"] else "仅规则候选，尚未执行助手来源复核。") + "</span></td></tr>")
    out.append('</tbody></table>' + ("</div>" if portable else "") + '<p class="muted">阅读顺序：研究问题 → 对象 → 路线 → 发现或论点 → 数值条件 → 局限与边界。方括号页码指原论文页码。完整英文证据和页码、块、字符偏移见 HTML 可展开区域及 Excel；原始研究记录保存在 research.jsonl。</p></article>')
    return "".join(out)


PDF_CSS = """
* {box-sizing:border-box;} body {font-family:sans-serif;font-size:11pt;line-height:1.4;color:#172b3b;}
h1 {font-size:18pt;line-height:1.2;margin:0 0 6pt;font-weight:bold;color:#163d4c;}
h2.subtitle {font-size:13pt;line-height:1.3;margin:0 0 6pt;color:#315c61;}
h3 {font-size:12pt;line-height:1.3;margin:10pt 0 3pt;color:#175861;page-break-after:avoid;}
p {margin:3pt 0 5pt;} .eyebrow {font-size:8pt;letter-spacing:.7pt;color:#557b7b;margin:0 0 7pt;}
.identity {font-size:8.3pt;color:#536977;margin:3pt 0 7pt;}
.notice {font-size:8pt;line-height:1.4;background:#edf5f3;padding:7pt;margin:5pt 0 9pt;}
.muted {color:#61727c;} .field {page-break-inside:avoid;} .field li {margin:2pt 0 4pt;}
ul,ol {margin:3pt 0 5pt;padding-left:17pt;} a {color:#207073;text-decoration:none;}
table {border-collapse:collapse;width:100%;font-size:10pt;line-height:1.4;}
th {background:#e7f0ee;color:#244f56;font-weight:bold;text-align:left;}
th,td {border-bottom:.5pt solid #cbdcda;padding:6pt;vertical-align:top;}
tr {page-break-inside:avoid;}
.number-table {table-layout:fixed;} .number-table .object {width:150pt;} .number-table .value {width:70pt;} .number-table .conditions {width:263pt;}
.overview-table .paper {width:29%;} .overview-table .route {width:34%;} .overview-table .core {width:37%;}
.overview-table {font-size:8.3pt;} .source-link {font-size:7.3pt;color:#61727c;margin-top:10pt;}
.lead {font-size:10pt;margin:8pt 0;} .citation {font-size:8pt;color:#286b6c;white-space:nowrap;} .continuation {font-size:8pt;margin-top:16pt;}
"""


def write_reading_report(path, records):
    """Write source-linked A4 cards; return factual renderer page counts."""
    import fitz
    records = _snapshot(records)
    cards = [_card(r) for r in records]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    page_counts = []
    starts = []
    def draw_section(writer, html):
        story = fitz.Story(html=html, user_css=PDF_CSS)
        count = 0
        while True:
            device = writer.begin_page(fitz.paper_rect("a4"))
            more, _ = story.place(fitz.Rect(38, 35, 557, 789))
            story.draw(device)
            writer.end_page()
            count += 1
            if not more:
                return count
            if count >= 20:
                raise ValueError("Reading content cannot fit bounded card layout")
    # Probe natural flow once, then intentionally split longer cards at the
    # transition to conclusions.  This prevents a lonely continuation line or
    # a source URL from becoming its own near-empty page.
    sections = [[_overview_html(cards)]]
    probe = fitz.DocumentWriter(BytesIO())
    try:
        for card in cards:
            html = _card_html(card)
            count = draw_section(probe, html)
            sections.append([html] if count == 1 else [_card_html(card, part=1), _card_html(card, part=2)])
    finally:
        probe.close()
    with TemporaryDirectory(prefix="paperlens-reading-") as temporary:
        raw_path = Path(temporary) / "layout.pdf"
        writer = fitz.DocumentWriter(str(raw_path))
        page_number = 0
        try:
            for group in sections:
                start = page_number
                for html in group:
                    page_number += draw_section(writer, html)
                starts.append(start)
                page_counts.append(page_number - start)
        finally:
            writer.close()
        # Retain readability instead of silently squeezing arbitrary long cards.
        if page_counts[0] != 1:
            raise ValueError("Overview exceeds one page; split the input batch for this reading report")
        if any(n > 2 for n in page_counts[1:]):
            raise ValueError("A reading card exceeds two pages; shorten source-review claims explicitly")
        doc = fitz.open(str(raw_path))
        toc = [[1, "批量概览", 1]]
        for card, start in zip(cards, starts[1:]):
            toc.append([1, card["title_zh"] or card["title"], start + 1])
        doc.set_toc(toc)
        doc.set_metadata({"title": "PaperLens · 来源支持的研究阅读卡片", "author": "PaperLens",
                          "subject": "assistant_source_review; user unreviewed; scientific accuracy not independently evaluated"})
        for i, page in enumerate(doc):
            page.draw_line((38, 801), (557, 801), color=(.77, .84, .83), width=.5)
            page.insert_text((38, 817), "PaperLens · 研究阅读卡片", fontname="china-s", fontsize=8, color=(.34, .43, .46))
            page.insert_text((275, 817), "返回概览", fontname="china-s", fontsize=8, color=(.16, .43, .44))
            page.insert_text((519, 817), f"{i+1} / {len(doc)}", fontsize=8, color=(.34, .43, .46))
            page.insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(270, 805, 320, 824), "page": 0})
        for card, start, count in zip(cards, starts[1:], page_counts[1:]):
            # The overview displays each stable arXiv identifier once.
            for rect in doc[0].search_for(card["id"]):
                doc[0].insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": start})
            meta = card["record"].get("meta", {})
            pdf_url = meta.get("pdf_url") or meta.get("url")
            if pdf_url:
                labels = {}
                for values in card["values"].values():
                    for claim in values:
                        pages = _pages(card, claim.get("evidence_ids", []))
                        if pages:
                            labels[_citation(card, claim)] = pages[0]
                for page in (doc[n] for n in range(start, start + count)):
                    for label, original_page in labels.items():
                        for rect in page.search_for(label):
                            page.insert_link({"kind": fitz.LINK_URI, "from": rect,
                                              "uri": pdf_url + "#page=" + str(original_page)})
                    for rect in page.search_for(pdf_url):
                        page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": pdf_url})
        doc.subset_fonts()
        doc.save(str(path), garbage=4, deflate=True)
        doc.close()
    return {"pages": sum(page_counts), "overview_pages": page_counts[0],
            "cards": [{"id": c["id"], "start_page": start+1, "pages": count}
                      for c, start, count in zip(cards, starts[1:], page_counts[1:])]}


WEB_CSS = """
:root{color-scheme:light;--ink:#193340;--muted:#647680;--accent:#236b6b;--line:#d4e0dc;--paper:#fff;--wash:#f0f5f1}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;color:var(--ink);background:var(--wash);font-family:system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.7}
main{max-width:1120px;margin:auto;padding:40px 24px 80px}article{background:var(--paper);padding:40px;border:1px solid var(--line);border-radius:16px;margin:0 0 30px}h1{font-family:Georgia,"Noto Serif CJK SC",serif;font-size:clamp(24px,3vw,34px);line-height:1.22;margin:0 0 14px;overflow-wrap:break-word;color:#163d4c}h2.subtitle{font-size:22px;font-weight:500;color:#315c61;margin:0 0 14px}h3{font-size:17px;line-height:1.4;margin:26px 0 8px;color:#175861}p{margin:8px 0 12px}.eyebrow{font-size:12px;letter-spacing:1.4px;color:#557b7b;margin-top:0}.identity{font-size:13px;color:var(--muted)}.notice{padding:15px 18px;background:#edf5f3;border-left:3px solid #7caaa0;font-size:13px;line-height:1.7}.muted{color:var(--muted)}a{color:var(--accent);text-underline-offset:3px}.citation{font-size:12px;white-space:nowrap}li{margin:6px 0}ul,ol{padding-left:25px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.65}th,td{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:14px 10px}th{background:#edf4ef;color:#315858}.overview-table td:first-child{width:29%}.overview-table td:nth-child(2){width:34%}.number-table td:first-child{width:30%}.number-table td:nth-child(2){width:14%}.source-link{overflow-wrap:anywhere;font-size:12px;color:var(--muted);margin-top:26px}details{border:1px solid var(--line);border-radius:9px;padding:12px 16px;margin:10px 0}summary{cursor:pointer;font-size:14px;font-weight:600;color:#315c61}blockquote{margin:12px 0;border-left:3px solid #acc7bf;padding:6px 14px;font-family:Georgia,serif;font-size:15px;line-height:1.65;white-space:normal;overflow-wrap:break-word}.locations{font-size:12px;overflow-wrap:anywhere;color:var(--muted)}.audit{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.back{font-size:13px}.table-scroll{overflow-x:auto}.field{break-inside:avoid}.evidence-item:target{outline:3px solid #d1a94d;outline-offset:3px}code{font-size:12px}
@media(max-width:650px){main{padding:16px 10px 40px}article{padding:22px 18px;border-radius:10px}h1{font-size:25px}table{min-width:650px}.notice{padding:12px}th,td{padding:10px}h2.subtitle{font-size:19px}}
@media print{body{background:white}main{padding:0}article{border:0;border-radius:0;padding:0;break-before:page}details{break-inside:avoid}.overview{break-before:auto}a{color:inherit}}
"""


def _evidence_html(card):
    fields = defaultdict(list)
    for name, label in CLAIM_FIELDS:
        for claim in card["values"][name]:
            for eid in claim.get("evidence_ids", []):
                if label not in fields[eid]:
                    fields[eid].append(label)
    selected = [e for e in card["layer"].get("evidence", []) if e["id"] in fields]
    others = [e for e in card["layer"].get("evidence", []) if e["id"] not in fields]
    out = ['<section class="evidence"><h3>英文证据与精确来源</h3><p class="muted">以下保留完整规范化原句。页码来自原论文；块内偏移是左闭右开区间，可在 research.jsonl 的 raw_blocks 中逐字回查。有原句不等于科学主张正确。</p>']
    def item(e):
        eid = e["id"]
        label = "、".join(fields[eid]) or "其余阅读证据（未用于上方复核主张）"
        locs = "; ".join(f'p.{p["page"]} · block {p["block_id"]} · [{p["start"]}, {p["end"]})' for p in e["parts"])
        return ('<details class="evidence-item" id="e-' + escape(card["id"] + "-" + eid, quote=True) + '"><summary>' +
                escape(label + " · 原文 p." + _page_label(e["pages"])) + "</summary><blockquote lang=\"en\">" +
                escape(e["text"]) + '</blockquote><p class="locations">' + escape(locs) +
                '</p><p class="audit">证据ID：' + escape(eid) + "</p></details>")
    out.extend(item(e) for e in selected)
    if others:
        out.append('<details><summary>其余完整阅读证据（' + str(len(others)) + ' 句）</summary>')
        out.extend(item(e) for e in others)
        out.append("</details>")
    out.append('<details class="audit"><summary>版本、来源与复核边界</summary><p>' + escape(card["notice"]) +
               "</p><p>来源层：" + escape(card["review"].get("origin", "未执行助手来源复核")) +
               "；状态：" + escape(card["review"].get("status", "仅规则候选")) +
               "；独立金标准：否；用户复核：unreviewed。</p><p>阅读版本：" + escape(card["layer"].get("version", "未执行")) +
               "；助手来源复核版本：" + escape(card["review"].get("version", "未执行")) + "</p><p>PDF SHA256：" +
               escape(card["record"].get("pdf_hash", "未提供")) + "</p></details></section>")
    return "".join(out)


def write_reading_preview(path, records):
    """Write standalone HTML with expandable English evidence and exact locators."""
    cards = [_card(r) for r in _snapshot(records)]
    content = [_overview_html(cards, portable=True)]
    for card in cards:
        html = _card_html(card, portable=True)
        html = html.removesuffix("</article>") + _evidence_html(card) + '<p class="back"><a href="#overview">↑ 返回批量概览</a></p></article>'
        content.append(html)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PaperLens · 来源支持的研究阅读卡片</title><style>' +
                    WEB_CSS + '</style></head><body><main>' + "".join(content) + '</main><script>function showEvidence(){let el=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(!el)return;for(let p=el;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;}addEventListener("hashchange",showEvidence);showEvidence();</script></body></html>', encoding="utf-8")
    return {"papers": len(cards), "evidence_sentences": sum(len(c["evidence"]) for c in cards)}


def _column(n):
    text = ""
    while n:
        n, digit = divmod(n-1, 26)
        text = chr(65+digit) + text
    return text


def _xlsx(path, sheets):
    # All values are inline strings, including formula-like source content.
    # No external workbook library or model/service is needed by the renderer.
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1)) + '</Types>')
        z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{xml_escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_,_,_) in enumerate(sheets,1)) + '</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1)) + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        z.writestr("xl/styles.xml", '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF245C60"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        for i, (_, headers, rows, widths) in enumerate(sheets, 1):
            body = [f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:{_column(len(headers))}{len(rows)+1}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="60"/><cols>']
            for c in range(len(headers)):
                width = widths[c] if c < len(widths) else 28
                body.append(f'<col min="{c+1}" max="{c+1}" width="{width}" customWidth="1"/>')
            body.append("</cols><sheetData>")
            for row_index, row in enumerate([headers, *rows], 1):
                body.append(f'<row r="{row_index}"' + (' ht="32" customHeight="1"' if row_index==1 else '') + '>')
                for c, value in enumerate(row, 1):
                    value = "" if value is None else str(value)
                    if len(value) > 32767:
                        raise ValueError("Excel cell exceeds 32767 characters; preserve in JSONL and split an explicit audit row")
                    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
                    body.append(f'<c r="{_column(c)}{row_index}" t="inlineStr" s="{1 if row_index==1 else 0}"><is><t xml:space="preserve">{xml_escape(value)}</t></is></c>')
                body.append("</row>")
            body.append(f'</sheetData><autoFilter ref="A1:{_column(len(headers))}{len(rows)+1}"/><pageMargins left="0.25" right="0.25" top="0.4" bottom="0.4" header="0.2" footer="0.2"/></worksheet>')
            z.writestr(f"xl/worksheets/sheet{i}.xml", "".join(body))


def write_reading_workbook(path, records):
    """Write readable cards, complete mapped evidence, and separate raw/audit tabs."""
    records = _snapshot(records)
    cards = [_card(r) for r in records]
    overview, claims, numbers, candidates, evidence, originals, audit = [], [], [], [], [], [], []
    for c in cards:
        r, layer, review = c["record"], c["layer"], c["review"]
        origin = "assistant_source_review" if c["assisted"] else "deterministic_source_reconstruction / 未执行助手来源复核"
        overview.append([c["id"], c["title"], c["title_zh"], c["type"], _joined(c,"question"), _joined(c,"objects"),
                         _joined(c,"methods"), _joined(c,"arguments" if c["perspective"] else "steps"),
                         _joined(c,"arguments" if c["perspective"] else "findings"), _joined(c,"conclusion"),
                         _joined(c,"author_limitations"), _joined(c,"boundaries"), origin, "unreviewed",
                         "not_independently_evaluated", r.get("meta",{}).get("pdf_url") or r.get("meta",{}).get("url","")])
        used = defaultdict(list)
        for name, label in CLAIM_FIELDS:
            if not c["values"][name]:
                claims.append([c["id"],label,"",c["missing"][name],"", "", origin,"unreviewed"])
            for claim in c["values"][name]:
                ids = claim.get("evidence_ids",[])
                claims.append([c["id"],label,claim.get("kind",""),claim["text"],_page_label(_pages(c,ids)),"; ".join(ids),origin,"unreviewed"])
                for eid in ids:
                    if label not in used[eid]: used[eid].append(label)
        for n in c["values"]["numbers"]:
            numbers.append([c["id"],n.get("object"),n.get("quantity"),n.get("value"),n.get("unit"),n.get("conditions"),
                            n.get("comparison_baseline"),n.get("ownership"),n["text"],_page_label(_pages(c,n["evidence_ids"])),
                            "; ".join(n["evidence_ids"]),origin,"unreviewed"])
        for n in layer.get("numeric_candidates",[]):
            candidates.append([c["id"],n.get("object"),n.get("quantity"),n.get("value"),n.get("unit"),n.get("conditions"),
                               n.get("ownership"),"; ".join(n.get("missing_bindings",[])),n.get("statement"),
                               _page_label(_pages(c,n.get("evidence_ids",[]))),"; ".join(n.get("evidence_ids",[])),
                               "规则候选；未绑定对象/物理量/条件/归属时不进入关键表"])
        raw = {b["block_id"]:b for b in r.get("raw_blocks",[])}
        for e in layer.get("evidence",[]):
            for part_index, p in enumerate(e["parts"],1):
                evidence.append([c["id"],"、".join(used[e["id"]]),e["id"],e["text"],p["page"],p["block_id"],p["start"],p["end"],
                                 raw[p["block_id"]]["text"][p["start"]:p["end"]],part_index,len(e["parts"]),e.get("section_kind"),
                                 e["paragraph_id"],e["start"],e["end"],r.get("pdf_hash")])
        for key in ("materials","methods","findings","conclusions","experimental_data","review"):
            value = r.get(key)
            text = value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
            chunks = [text[i:i+30000] for i in range(0,len(text),30000)] or [""]
            for index, chunk in enumerate(chunks,1):
                originals.append([c["id"],key,index,len(chunks),chunk,"历史 research-1 原值；没有被阅读层改写"])
        items = {"阅读来源":layer.get("origin","未执行"),"阅读版本":layer.get("version","未执行"),
                 "阅读schema":layer.get("schema_version","未执行"),"助手来源复核":origin,
                 "助手来源复核版本":review.get("version","未执行"),"来源复核状态":review.get("status","未执行"),
                 "用户复核":"unreviewed","独立金标准":False,"科研准确率":"not_independently_evaluated",
                 "PDF SHA256":r.get("pdf_hash"),"解析器版本":r.get("parser_version"),"提取器版本":r.get("extractor_version"),
                 "原记录结构状态":r.get("status"),"阅读质量":layer.get("quality",{}),"说明":c["notice"],
                 "未解决来源":review.get("unresolved_claims",[]),"排除片段":layer.get("excluded_fragments",[]),
                 "原文与许可":r.get("meta",{})}
        for key,value in items.items():
            text = value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
            for index in range(0,max(1,len(text)),30000):
                audit.append([c["id"],key,index//30000+1,text[index:index+30000]])
    notes = [["用途","阅读入口与来源复核辅助；不证明论文结论正确，不宣称科研级生产质量。"],
             ["中文复核层",NOTICE], ["阅读规则层",RULE_NOTICE],
             ["用户复核","source_review.human_review_status 与 reading_card.review_status 均保留 unreviewed；原 review 另见原始字段。"],
             ["数值","关键数值只使用来源复核层的完整绑定；未绑定规则候选单独存放，没有自动提升为本文新结果。"],
             ["证据","来源证据表逐个原始来源部分列出页码、块ID、左闭右开偏移以及原始切片；完整英文规范化句子不等于作者科学主张已正确。"],
             ["历史字段","原始字段保留历史原值与原 review，不用中文阅读卡片覆盖 methods/findings/conclusions。"],
             ["状态","success 等状态描述结构与流程；科研准确性没有独立金标准，不做数值排名。"],
             ["跨文献比较","观点/综述用论证路径，实验/模拟用方法及步骤；不强填不适用栏目。"],
             ["原始记录","完整 raw_blocks、reading_card、证据映射与所有版本在 research.jsonl；新旧数据库没有迁移或混用。"]]
    sheets = [
        ("阅读概览",["论文ID","科学标题","中文来源复核题目","研究类型","研究问题","研究对象","方法路线","步骤或论证路径","主要发现或论点","作者结论","作者明确局限","助手阅读边界","内容来源","用户复核","科研准确性","原文"],overview,[20,50,32,35,50,45,55,65,65,55,45,50,28,16,28,45]),
        ("研究卡片",["论文ID","栏目","主张类型","内容或具体缺失原因","原论文页码","证据ID","内容来源","用户复核"],claims,[20,24,20,95,16,48,28,18]),
        ("关键数值",["论文ID","对象","物理量","值","单位","条件","比较基准","归属","中文说明","原论文页码","证据ID","内容来源","用户复核"],numbers,[20,40,40,14,14,65,35,35,65,18,50,28,18]),
        ("规则数字候选",["论文ID","候选对象","物理量（未绑定可空）","值","单位","条件候选","归属","缺少绑定","完整英文原句","原论文页码","证据ID","状态说明"],candidates,[20,30,28,14,14,65,22,32,100,18,48,50]),
        ("来源证据",["论文ID","用于栏目","证据ID","完整规范化英文句子","原论文页码","原始块ID","块内起始偏移","块内结束偏移","原始切片","部分序号","总部分数","章节候选","规范段落ID","规范句起始","规范句结束","原PDF SHA256"],evidence,[20,30,42,110,16,30,16,16,100,12,12,20,35,16,16,72]),
        ("原始字段",["论文ID","历史字段","分片序号","分片总数","未改写原值","边界"],originals,[20,25,14,14,110,55]),
        ("审计与边界",["论文ID","审计项目","分片序号","原值或说明"],audit,[20,32,14,110]),
        ("说明",["项目","说明"],notes,[25,120]),
    ]
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    _xlsx(path,sheets)
    return {"papers":len(cards),"sheets":{name:len(rows) for name,_,rows,_ in sheets}}
