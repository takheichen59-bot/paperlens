"""Readable, source-linked exports of the research format (not ScientificRecord)."""
from html import escape
from pathlib import Path
from tempfile import TemporaryFile
from xml.sax.saxutils import escape as xml_escape
import csv
import json
import re
import zipfile

from .attribution import MATERIAL_LABELS, NUMERIC_LABELS

ROLE_HEADERS = ["study_materials", "background_materials", "comparator_materials", "reagents_or_environment",
    "uncertain_materials", "own_result_candidates", "simulation_parameters", "experimental_conditions",
    "cited_result_candidates", "uncertain_numeric_candidates", "attribution_version"]
ROLE_TITLES = ["本文研究对象（规则候选）", "背景材料", "本文对照材料（规则候选）", "试剂 / 环境", "材料归属不确定",
    "本文数值结果（规则候选）", "模拟参数", "实验条件", "引用 / 背景数值", "数值归属不确定", "归属规则版本"]


def role_cells(record):
    layer = record.get("attribution")
    if not layer:
        return [""] * 10 + ["NOT_EXECUTED_HISTORICAL_RECORD"]
    cells = ["; ".join(m["name"] for m in layer["materials"] if m["role"] == role)
        for role in ("study_subject", "background", "comparator", "reagent_or_environment", "uncertain")]
    for role in ("own_result", "simulation_parameter", "experimental_condition", "cited_result", "uncertain"):
        cells.append("\n\n".join(record["experimental_data"][n["candidate_index"]]["text"] for n in layer["numeric"] if n["role"] == role))
    return cells + [layer["version"]]


def evidence_location(record, ids):
    by_id = {s["evidence_id"]: s for s in record["source_snippets"]}
    return "; ".join(f'{eid}: p{by_id[eid]["page_start"]}, {by_id[eid]["block_id"]}, '
        f'{by_id[eid]["start_offset"]}:{by_id[eid]["end_offset"]}' for eid in ids)


def material_rows(record):
    by_id = {s["evidence_id"]: s for s in record["source_snippets"]}
    for material in record.get("attribution", {}).get("materials", []):
        for mention in material["mentions"]:
            ids = mention["evidence_ids"]
            yield [record["paper_id"], material["name"], MATERIAL_LABELS[material["role"]],
                MATERIAL_LABELS[mention["role"]], mention["reason"],
                "\n\n".join(by_id[eid]["text"] for eid in ids), evidence_location(record, ids),
                "\n\n".join(by_id[eid]["text"] for eid in mention["context_evidence_ids"]),
                evidence_location(record, mention["context_evidence_ids"])]


def numeric_rows(record):
    by_id = {s["evidence_id"]: s for s in record["source_snippets"]}
    for item in record.get("attribution", {}).get("numeric", []):
        candidate = record["experimental_data"][item["candidate_index"]]
        yield [record["paper_id"], item["candidate_index"], NUMERIC_LABELS[item["role"]], item["reason"],
            json.dumps(candidate["values"], ensure_ascii=False), candidate["text"],
            evidence_location(record, item["evidence_ids"]),
            "\n\n".join(by_id[eid]["text"] for eid in item["context_evidence_ids"]),
            evidence_location(record, item["context_evidence_ids"])]


def evidence_rows(record):
    for s in record["source_snippets"]:
        yield [record["paper_id"], s["evidence_id"], s["field"], s["page_start"], s["block_id"],
            s["start_offset"], s["end_offset"], s["section_kind"], s["text"], record["pdf_hash"]]


MATERIAL_HEADERS = ["论文ID", "材料", "材料总体角色", "本次提及角色", "规则理由", "原句", "原句定位", "归属上下文原文", "上下文定位"]
NUMERIC_HEADERS = ["论文ID", "候选序号", "数值归属", "规则理由", "原始值与单位（未归一化）", "原句", "原句定位", "归属上下文原文", "上下文定位"]
EVIDENCE_HEADERS = ["论文ID", "证据ID", "字段", "原论文页码", "块ID", "起始偏移", "结束偏移", "章节候选", "原文", "原PDF SHA256"]
NOTES = [
    ["用途", "规则预筛与人工复核；没有调用真实模型，没有独立科研准确率金标准。"],
    ["研究对象", "仅对原始材料候选作角色判断；空白不代表论文没有材料。对照表示本文对照，背景比较单列。"],
    ["数值", "本文结果、模拟参数、实验条件、引用结果、不确定分别列出；同句混合归属可能仍需人工拆分。"],
    ["证据", "页码来自原始PDF；字符区间左闭右开，原句可用JSONL raw_blocks逐字切片回查。原句存在不等于科学正确。"],
    ["原始结果", "原始材料、方法、发现、结论、数值候选均保留。规则归属是新增解释层，不是人工修订。"],
    ["复核", "归属层保持unreviewed。阅读汇总显示自动原文；人工修改、备注另见原始字段与修订表及JSONL review。"],
    ["版本", "历史research-1记录没有attribution时明确标记NOT_EXECUTED_HISTORICAL_RECORD；不自动补写。"],
    ["格式边界", "本文件使用research-1；不等同新版工作区ScientificRecord，也不迁移或混用数据库。"],
    ["报告", "processing-report.pdf是处理报告，不是原始论文；原文链接与许可保留，作者见JSONL meta。"],
]


def write_detail_csvs(directory, records_factory):
    for filename, headers, rows in [("material_roles.csv", MATERIAL_HEADERS, material_rows),
            ("numeric_attribution.csv", NUMERIC_HEADERS, numeric_rows), ("evidence.csv", EVIDENCE_HEADERS, evidence_rows)]:
        with (Path(directory) / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle); writer.writerow(headers)
            for record in records_factory():
                for row in rows(record):
                    writer.writerow(["'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v for v in row])


def _column(index):
    result = ""
    while index:
        index, digit = divmod(index - 1, 26); result = chr(65 + digit) + result
    return result


def write_workbook(path, records, original_headers, original_row):
    # Disk replay keeps multi-sheet exports bounded without loading PDFs or all
    # raw blocks into memory at once. All sheets share the caller's locked snapshot.
    with TemporaryFile(mode="w+t", encoding="utf-8") as spool:
        for record in records:
            spool.write(json.dumps(record, ensure_ascii=False) + "\n")
        def replay():
            spool.seek(0)
            for line in spool:
                yield json.loads(line)
        def summary(r):
            roles = role_cells(r)
            return [[r["paper_id"], r["meta"].get("title", ""), roles[0], r["methods"], r["findings"], r["conclusions"],
                *roles[1:], "; ".join(r["materials"]), r["status"], r.get("review", {}).get("decision", "unreviewed"), r["meta"].get("url", "")]]
        sheets = [("阅读汇总", ["论文ID", "论文标题", ROLE_TITLES[0], "自动方法原文", "自动发现原文", "自动结论原文",
            *ROLE_TITLES[1:], "全部材料候选（含背景）", "结构状态", "原字段复核（不含归属）", "原文链接"], summary),
            ("原始字段与修订", original_headers, lambda r: [original_row(r)]),
            ("材料角色", MATERIAL_HEADERS, material_rows), ("数值归属", NUMERIC_HEADERS, numeric_rows),
            ("证据", EVIDENCE_HEADERS, evidence_rows), ("说明", ["项目", "说明"], None)]
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets) + 1)) + '</Types>')
            z.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _, _) in enumerate(sheets, 1)) + '</sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1)) + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
            z.writestr("xl/styles.xml", '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF173E4A"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="49" fontId="1" fillId="2" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
            for i, (_, headers, rows) in enumerate(sheets, 1):
                def values():
                    if rows is None:
                        yield from NOTES
                    else:
                        for record in replay():
                            yield from rows(record)
                _write_sheet(z, i, headers, values())


def _write_sheet(z, index, headers, rows):
    def cell(value, style):
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))
        if len(text) > 32760:
            text = text[:32710] + " [截断；完整原文见JSONL]"
        return f'<c t="inlineStr" s="{style}"><is><t xml:space="preserve">{xml_escape(text)}</t></is></c>'
    with z.open(f"xl/worksheets/sheet{index}.xml", "w") as sheet:
        sheet.write(('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>' + ''.join(f'<col min="{i}" max="{i}" width="{24 if i < 3 else 55}" customWidth="1"/>' for i in range(1, len(headers) + 1)) + '</cols><sheetData>').encode())
        sheet.write(('<row r="1" ht="36" customHeight="1">' + ''.join(cell(v, 1) for v in headers) + '</row>').encode())
        count = 1
        for row in rows:
            count += 1
            sheet.write((f'<row r="{count}">' + ''.join(cell(v, 0) for v in row) + '</row>').encode())
        sheet.write((f'</sheetData><autoFilter ref="A1:{_column(len(headers))}{count}"/></worksheet>').encode())


def write_processing_report(path, records_factory):
    """Generate from stored automatic records only; no assistant-written claims."""
    import pymupdf as fitz
    def p(text):
        return '<p>' + escape(str(text)).replace('\n', '<br/>') + '</p>'
    html = ['<h1>PaperLens 科学文献处理报告</h1>', p('这是处理报告，不是原始论文。内容来自实际规则输出，未使用外部模型；没有独立科研金标准。success 仅表示结构状态，所有新归属仍待人工复核。')]
    total = 0
    for r in records_factory():
        total += 1; roles = role_cells(r)
        html.extend(['<h2>' + escape(r['id']) + '</h2>', p(r['meta'].get('title', '')),
            p('作者：' + '; '.join(a if isinstance(a, str) else a.get('name', '') for a in r['meta'].get('authors', []))),
            p('原文：' + r['meta'].get('url', '')), p('许可：' + r['meta'].get('license_url', '未记录')),
            p('原PDF SHA256：' + r['pdf_hash']), p(f"规则版本：{r['extractor_version']}；结构状态：{r['status']}；自动复核状态：{r['review_status']}；归属版本：{roles[-1]}"),
            p('全部材料候选（保留）：' + '; '.join(r['materials']))])
        for title, value in zip(ROLE_TITLES[:5], roles[:5]):
            html.append(p(title + '：' + (value or '未识别；不能据此断言没有')))
        for field, title in [('methods', '自动方法原文'), ('findings', '自动发现原文'), ('conclusions', '自动结论原文')]:
            html.append('<h3>' + title + '</h3>'); html.append(p(r[field] or '未提取到。规则覆盖或章节识别可能不足。'))
            target = field
            evidence = [s['evidence_id'] for s in r['source_snippets'] if s['field'] == target]
            html.append(p('原论文定位：' + (evidence_location(r, evidence) or '无')))
        html.append('<h3>数值候选与归属</h3>')
        for row in numeric_rows(r):
            html.extend([p(row[2] + ' / ' + row[3]), p(row[5]), p('定位：' + row[6])])
            if row[7]: html.extend([p('归属上下文：' + row[7]), p('上下文定位：' + row[8])])
        if not r['experimental_data']: html.append(p('未提取到数值候选。'))
        html.append('<h3>完整性与复核</h3>')
        html.append(p(f"证据共 {len(r['source_snippets'])} 条；JSONL含原始块与字符区间，可逐字回查。材料角色只覆盖已识别的化学物候选。方法、发现、结论不保证完整；数值不应跨条件直接排名。"))
        if r.get('review'):
            html.append(p('已有人工修订（自动结果保留）：' + json.dumps(r['review'], ensure_ascii=False)))
    html.insert(2, p(f'本次导出包含 {total} 篇记录。科研正确性未独立评估。'))
    css = 'body {font-family:sans-serif;font-size:10pt;line-height:1.45;color:#183642} h1 {font-size:24pt;color:#126b73} h2 {font-size:17pt;margin-top:24pt;border-bottom:1px solid #126b73} h3 {font-size:12pt;color:#126b73} p {margin:6pt 0;overflow-wrap:anywhere}'
    story = fitz.Story(html=''.join(html), user_css=css)
    page = fitz.paper_rect('a4'); area = page + (38, 40, -38, -40)
    def rectfn(rect_num, filled):
        return page, area, None
    writer = fitz.DocumentWriter(str(path))
    try:
        story.write(writer, rectfn)
    finally:
        writer.close()
    with fitz.open(path) as pdf:
        if not len(pdf) or not any('PaperLens' in pg.get_text() for pg in pdf):
            raise ValueError('Processing report rendering failed')


def write_preview(path, records_factory):
    """Portable reading preview; download files stay beside this HTML."""
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PaperLens 规则提取阅读预览</title>',
        '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#183642;background:#f5f8f8}article,header{padding:24px;background:white;border:1px solid #d5e4e4;border-radius:12px;margin:20px 0}h1,h2,h3{color:#126b73}a{color:#086b82}pre{white-space:pre-wrap;font:14px/1.6 system-ui,sans-serif;overflow-wrap:anywhere}dl{display:grid;grid-template-columns:minmax(120px,210px) 1fr;gap:8px}dd{margin:0;overflow-wrap:anywhere}.downloads{display:flex;gap:20px;flex-wrap:wrap}small{overflow-wrap:anywhere}</style>',
        '<header><h1>PaperLens · 科学文献规则提取</h1><p>自动原文与规则归属分列，所有归属仍待复核。success 只表示结构状态；没有调用真实模型，没有独立科研准确率金标准。</p><nav class="downloads"><a download href="research.xlsx">下载 Excel</a><a download href="research.jsonl">下载 JSONL</a><a download href="processing-report.pdf">下载处理报告 PDF</a><a download href="evidence.csv">下载证据 CSV</a></nav></header>']
    for r in records_factory():
        parts.extend(['<article><h2>' + escape(r['id'] + ' · ' + r['meta'].get('title', '')) + '</h2><dl>'])
        for title, value in zip(ROLE_TITLES, role_cells(r)):
            parts.append('<dt>' + escape(title) + '</dt><dd>' + escape(value or '未识别 / 待确认').replace('\n', '<br>') + '</dd>')
        parts.append('</dl>')
        for field, title in [('materials', '原始材料候选（含背景）'), ('methods', '自动方法原文'), ('findings', '自动发现原文'), ('conclusions', '自动结论原文')]:
            value = '; '.join(r[field]) if field == 'materials' else r[field]
            parts.append('<h3>' + title + '</h3><pre>' + escape(value or '未提取到；不能据此断言论文未报告。') + '</pre>')
        parts.append('<p><small>原PDF SHA256：' + escape(r['pdf_hash']) + '<br>原文：<a href="' + escape(r['meta'].get('url', ''), quote=True) + '">' + escape(r['meta'].get('url', '')) + '</a></small></p><p>处理报告并非原始论文。页码、块ID、字符区间与引用上下文见证据表和完整 JSONL。</p></article>')
    parts.append('</html>')
    Path(path).write_text(''.join(parts), encoding='utf-8')
