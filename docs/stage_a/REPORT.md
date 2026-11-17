# P1：告警分级、M14字段降级、泄漏审计

实际统计：`{"submitted": 10, "success": 3, "partial": 6, "failed": 0, "skipped": 1, "failed_internal_classification": 0, "failed_content_or_processing": 0}`

读取版本 `20261115T153225819714Z-1d4245a5cb644f5d87f027fbda481c72`；发布时间 `2026-11-15T15:32:25.819706+00:00`。分类依据：`docs/diagnosis/WARNINGS_INVENTORY.md`。
告警消息：informational 84，blocking 15；原始证据 201 条。

failed_internal_classification属于程序内部告警分类遗漏/矛盾，标注为“待下一轮排查的分类遗漏”，排除于内容质量统计；其余failed为内容/处理失败。

## 逐篇状态与告警

| paper_id | 原→新状态 | informational | blocking | methods字符 | success含多栏提示 |
|---|---|---|---|---:|---|
| arxiv:2501.00534 | partial→partial | page_1_possible_multicolumn, page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_5_possible_multicolumn, conclusions_fallback | methods_fallback_truncated, missing_field:methods | 0 | N/A |
| arxiv:2501.00561 | failed→partial | page_1_possible_multicolumn, page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_5_possible_multicolumn, page_6_possible_multicolumn, page_7_possible_multicolumn, page_8_possible_multicolumn, page_9_possible_multicolumn | methods_fallback_truncated, missing_field:methods | 0 | N/A |
| arxiv:2501.00564 | partial→partial | page_1_possible_multicolumn, page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_5_possible_multicolumn, page_6_possible_multicolumn | methods_fallback_rejected, missing_field:chemicals, missing_field:methods | 0 | N/A |
| arxiv:2501.00589 | partial→success | page_1_possible_multicolumn, page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_5_possible_multicolumn, page_6_possible_multicolumn, page_7_possible_multicolumn, page_8_possible_multicolumn, page_9_possible_multicolumn, page_10_possible_multicolumn, page_12_possible_multicolumn | 无 | 925 | True |
| arxiv:2501.00591 | partial→partial | page_1_possible_multicolumn, page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_5_possible_multicolumn, page_6_possible_multicolumn, page_7_possible_multicolumn | methods_fallback_truncated, missing_field:conclusions, missing_field:methods | 0 | N/A |
| arxiv:2501.00600 | partial→partial | page_3_possible_multicolumn, page_11_possible_multicolumn, page_12_possible_multicolumn, page_18_possible_multicolumn, page_26_possible_multicolumn, conclusions_fallback | methods_fallback_rejected, missing_field:methods | 0 | N/A |
| arxiv:2501.00620 | partial→partial | page_2_possible_multicolumn, page_3_possible_multicolumn, page_4_possible_multicolumn, page_6_possible_multicolumn, page_7_possible_multicolumn, page_8_possible_multicolumn, page_9_possible_multicolumn, page_11_possible_multicolumn, page_12_possible_multicolumn, page_13_possible_multicolumn, page_14_possible_multicolumn, page_15_possible_multicolumn, page_16_possible_multicolumn, page_17_possible_multicolumn, page_18_possible_multicolumn, page_20_possible_multicolumn, page_23_possible_multicolumn, page_28_possible_multicolumn, page_30_possible_multicolumn, page_31_possible_multicolumn | methods_fallback_rejected, missing_field:chemicals, missing_field:methods | 0 | N/A |
| arxiv:2501.00679 | partial→success | page_3_possible_multicolumn, page_6_possible_multicolumn, page_7_possible_multicolumn, page_8_possible_multicolumn, page_9_possible_multicolumn, page_12_possible_multicolumn, page_13_possible_multicolumn, page_14_possible_multicolumn, page_23_possible_multicolumn, page_24_possible_multicolumn, page_25_possible_multicolumn, page_26_possible_multicolumn, page_27_possible_multicolumn, page_29_possible_multicolumn, page_31_possible_multicolumn, page_33_possible_multicolumn, page_34_possible_multicolumn, page_35_possible_multicolumn | 无 | 815 | True |
| arxiv:2501.00680 | partial→success | page_1_possible_multicolumn | 无 | 1330 | True |
| arxiv:2501.01468 | skipped | N/A | N/A | N/A | N/A |

## 状态变化与内容变化分开说明

- arxiv:2501.00534：状态原因：状态不变；字段缺失或已有阻断性告警仍保留。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals, conclusions。
- arxiv:2501.00561：状态原因：M14只清空超长methods，恢复chemicals/conclusions，failed→partial。字段与修复前相同：chemicals=False, conclusions=False, methods=True。保留字段：chemicals, conclusions。
- arxiv:2501.00564：状态原因：状态不变；字段缺失或已有阻断性告警仍保留。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：conclusions。
- arxiv:2501.00589：状态原因：三字段及证据原已存在；仅提示性告警不再阻断，内容未因状态变化而改善。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals, conclusions, methods。
- arxiv:2501.00591：状态原因：状态不变；字段缺失或已有阻断性告警仍保留。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals。
- arxiv:2501.00600：状态原因：状态不变；字段缺失或已有阻断性告警仍保留。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals, conclusions。
- arxiv:2501.00620：状态原因：状态不变；字段缺失或已有阻断性告警仍保留。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：conclusions。
- arxiv:2501.00679：状态原因：三字段及证据原已存在；仅提示性告警不再阻断，内容未因状态变化而改善。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals, conclusions, methods。
- arxiv:2501.00680：状态原因：三字段及证据原已存在；仅提示性告警不再阻断，内容未因状态变化而改善。字段与修复前相同：chemicals=True, conclusions=True, methods=True。保留字段：chemicals, conclusions, methods。

methods长度200–3000：3/10；这是长度统计，仍含图注和错序，不能解释为可用方法篇数。

00561的chemicals/conclusions恢复属于输出内容恢复，不证明实体识别或结论语义改善。三篇success只改变状态政策，字段内容与A前一致。

## 全字段泄漏审计

4篇全部片段可判定；5篇有unresolved；1篇不适用。已判定片段165，未判定片段36，已发现泄漏1条。完整片段见LEAKAGE.md。

| paper_id | 审计状态 | 已判定/未判定片段 | 泄漏条数 | unresolved原因 |
|---|---|---|---:|---|
| arxiv:2501.00534 | unresolved | 0/10 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00561 | unresolved | 20/9 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00564 | decided | 2/0 | 0 | 无 |
| arxiv:2501.00589 | unresolved | 20/8 | 1 | 区间无法判定：章节为unknown |
| arxiv:2501.00591 | unresolved | 0/5 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.00600 | decided | 10/0 | 0 | 无 |
| arxiv:2501.00620 | decided | 26/0 | 0 | 无 |
| arxiv:2501.00679 | decided | 71/0 | 0 | 无 |
| arxiv:2501.00680 | unresolved | 16/4 | 0 | 区间无法判定：章节为unknown |
| arxiv:2501.01468 | not_applicable | 0/0 | 0 | 无 |

独立自检：`PASS: known leak detected`，退出码0。范围只涵盖有效章节视图和已确证区间，不是全部真实章节的人工标注，不覆盖unresolved范围。

## 下载与已知限制

- {"paper_id": "arxiv:2501.01468", "status": "skipped", "informational": null, "blocking": null, "file_bytes": 129565883, "file_bytes_source": "content_length", "bytes_received": 0, "skipped_reason": "size_limit", "preserved_fields": []}

- M09多栏顺序、图注/方法串入结论、HK0/HK1误报保持原样；本轮不改抽取规则。
- 00589虽成为结构success，已确证的致谢续段泄漏仍存在，不能用状态提升解释内容改善。
- parser_summary调试字段暂缓；解析清洗统计未进入分级文件。
- exports使用CURRENT单点发布及共享读取快照；已改消费方与README。
- contracts、表结构、M09、M12、化学物规则的哈希比对见UNCHANGED.json。

验收：`python scripts/verify_all.py --results work/stage_a/real/results`。本阶段停在P1，尚未开始B–F及网站成品交付。
