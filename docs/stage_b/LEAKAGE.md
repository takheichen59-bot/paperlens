# 全字段泄漏审计

读取版本：20261115T155710810368Z-da8c3819714146ba82ed476bef02bdc8；发布时间：2026-11-15T15:57:10.810360+00:00

判定依据限于匹配PDF哈希/解析版本的章节视图及外部确证区间，不等于完整人工语义标注。

| paper_id | 状态 | 审计 | 已判定片段 | unresolved片段 | 泄漏条数 | unresolved原因 |
|---|---|---|---:|---:|---:|---|
| arxiv:2501.00534 | partial | unresolved | 0 | 9 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00561 | partial | unresolved | 17 | 8 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00564 | partial | decided | 1 | 0 | 0 |  |
| arxiv:2501.00589 | partial | unresolved | 3 | 7 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00591 | partial | unresolved | 0 | 4 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00600 | partial | decided | 9 | 0 | 0 |  |
| arxiv:2501.00620 | partial | decided | 26 | 0 | 0 |  |
| arxiv:2501.00679 | success | decided | 70 | 0 | 0 |  |
| arxiv:2501.00680 | success | unresolved | 14 | 4 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.01468 | skipped | not_applicable | 0 | 0 | 0 |  |

范围限定：4篇全部片段可判定，5篇存在unresolved，1篇无抽取片段、不适用。已判定范围共发现0条泄漏；不覆盖未判定区间。

