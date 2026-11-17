# 全字段泄漏审计

读取版本：20261115T153225819714Z-1d4245a5cb644f5d87f027fbda481c72；发布时间：2026-11-15T15:32:25.819706+00:00

判定依据限于匹配PDF哈希/解析版本的章节视图及外部确证区间，不等于完整人工语义标注。

| paper_id | 状态 | 审计 | 已判定片段 | unresolved片段 | 泄漏条数 | unresolved原因 |
|---|---|---|---:|---:|---:|---|
| arxiv:2501.00534 | partial | unresolved | 0 | 10 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00561 | partial | unresolved | 20 | 9 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00564 | partial | decided | 2 | 0 | 0 |  |
| arxiv:2501.00589 | success | unresolved | 20 | 8 | 1 | 区间无法判定：章节为unknown |
| arxiv:2501.00591 | partial | unresolved | 0 | 5 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00600 | partial | decided | 10 | 0 | 0 |  |
| arxiv:2501.00620 | partial | decided | 26 | 0 | 0 |  |
| arxiv:2501.00679 | success | decided | 71 | 0 | 0 |  |
| arxiv:2501.00680 | success | unresolved | 16 | 4 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.01468 | skipped | not_applicable | 0 | 0 | 0 |  |

范围限定：4篇全部片段可判定，5篇存在unresolved，1篇无抽取片段、不适用。已判定范围共发现1条泄漏；不覆盖未判定区间。

## arxiv:2501.00589 / conclusions / p8-b1 [0:920]

当前归属：CONCLUSIONS；实际归属：Acknowledgements；依据：external_ground_truth

```text
ment no. 857470 and from the European Regional Devel-
opment Fund via the Foundation for Polish Science Inter-
national Research Agenda PLUS program grant No. MAB
PLUS/2018/8.
JSW work was supported by the Na-
tional Science Centre, Poland, under research project no
UMO-2019/35/D/ST5/03526.
SB thanks the National Sci-
ence Center in Poland for SONATA BIS number DEC-
2023/50/E/ST3/00569 and FIRST TEAM FENG.02.02-IP.05-
0177/23 project, funded by the Foundation for Polish Sci-
ence. A.W. and S.B. acknowledge the support from COST
ACTION CA22154 (DAEMON) by COST (European Coop-
eration in Science and Technology). The authors acknowledge
the computational resources provided by the Aalto University
School of Science “Science-IT” project. M.A. thanks CSC
(Finland) for support via the project 2010169. J.B. acknowl-
edge funding from the Research council of Finland through
the OCRAMLIP project, grant number 354234.
```

