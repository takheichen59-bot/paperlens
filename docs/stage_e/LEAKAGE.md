# 全字段泄漏审计

读取版本：20261115T161604837297Z-105ed92998754549bc0924a40c9f9c7d；发布时间：2026-11-15T16:16:04.837289+00:00

判定依据限于匹配PDF哈希/解析版本的章节视图及外部确证区间，不等于完整人工语义标注。

| paper_id | 状态 | 审计 | 已判定片段 | unresolved片段 | 泄漏条数 | unresolved原因 |
|---|---|---|---:|---:|---:|---|
| arxiv:2501.00534 | partial | unresolved | 0 | 9 | 0 | 区间无法判定：无独立标题的前置/正文区 |
| arxiv:2501.00561 | success | unresolved | 24 | 2 | 0 | 区间无法判定：无独立标题的前置/正文区 |
| arxiv:2501.00564 | partial | decided | 6 | 0 | 0 |  |
| arxiv:2501.00589 | success | unresolved | 14 | 2 | 0 | 区间无法判定：无独立标题的前置/正文区 |
| arxiv:2501.00591 | partial | unresolved | 0 | 4 | 0 | 区间无法判定：无独立标题的前置/正文区 |
| arxiv:2501.00600 | partial | unresolved | 7 | 2 | 0 | 区间无法判定：未登记的章节标题 270 MPa |
| arxiv:2501.00620 | partial | decided | 59 | 0 | 0 |  |
| arxiv:2501.00679 | success | decided | 81 | 0 | 0 |  |
| arxiv:2501.00680 | success | unresolved | 8 | 3 | 0 | 区间无法判定：无独立标题的前置/正文区；区间无法判定：未登记的章节标题 3.1 Nanoparticle with opposite faces terminated either with；区间无法判定：未登记的章节标题 3.3 Nanoparticle with mixed termiations |
| arxiv:2501.01468 | skipped | not_applicable | 0 | 0 | 0 |  |

范围限定：3篇全部片段可判定，6篇存在unresolved，1篇无抽取片段、不适用。已判定范围共发现0条泄漏；不覆盖未判定区间。

