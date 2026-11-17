# Warnings 盘点与待确认分类依据

本文件为实施前盘点，不代表分类逻辑已经实现。范围：当前src/生产代码、acceptance/测试、scripts/消费方、examples/，并grep工作区Python源码中的历史生成器/复制树。未修改src、测试、规则、contracts或DDL。原始grep见 WARNINGS_GREP.txt。

## 统计口径

- 冻结批次：work/fixes/real-final；输入10篇，其中9条持久化ExtractionResult、1篇skipped无抽取结果。
- “结果次数/篇数”：最终ExtractionResult.warnings内的出现次数及涉及论文数；一次页面告警算一次，不把所有页合并成一次。
- “解析次数/篇数”：9篇ParsedPaper.warnings中的上游次数，独立列示，不能与结果列相加当不同告警。
- failed那篇最终只留下operation_failed；不能从其最终warnings推断拒绝前候选没有版面提示。
- skipped_reason=size_limit是FailureRecord状态原因，不是extractor warning，不计入两类warnings；报告对该篇写“未执行抽取/N/A”。

## 当前生产告警代码及建议分类

| 代码/代码族 | 生产出现文件 | 结果次数/篇数 | 上游解析次数/篇数 | 建议分类 | 依据/字段条件 |
|---|---|---:|---:|---|---|
| `page_<n>_possible_multicolumn` | `src/parsers/pdf.py:47` | 73/8 | 82/9 | informational | 仅标记可能的阅读顺序风险，当前不清空字段或撤销证据。 |
| `page_<n>_no_text` | `src/parsers/pdf.py:32` | 0/0 | 0/0 | informational | 页级覆盖提示；若最终字段缺失，由missing_field另行blocking，不能因一页无文本推定所有字段失效。 |
| `removed_block:<id>` | `src/parsers/cleaning.py:87` | 0/0 | 119/7 | informational | 清洗轨迹；Composite当前过滤该前缀，故不进入最终warnings。 |
| `sections_unknown` | `src/parsers/sections.py:111` | 0/0 | 0/0 | informational | 章节识别不足，不自动撤销已经通过raw切片与字段证据检查的字段；不是语义正确保证。 |
| `methods_fallback:<kind>` | `src/extractors/methods.py:46` | 0/0 | 0/0 | informational | 成功回退的来源提示；实际无方法时必须另有缺字段告警。 |
| `conclusions_fallback` | `src/extractors/conclusions.py:21` | 2/2 | 0/0 | informational | 成功选出回退片段的来源提示，不因来源自动判为证据失效。 |
| `methods_fallback_truncated` | `src/extractors/methods.py:47` | 2/2 | 0/0 | blocking | methods必须已清空且无methods证据；下一阶段M14降级复用此代码，分类语义相同。 |
| `methods_fallback_rejected` | `src/extractors/methods.py:48` | 3/3 | 0/0 | blocking | methods为空、无有效methods证据；三字段均有效却带此代码属于分类/生成矛盾。 |
| `missing_field:chemicals` | `src/extractors/composite.py:41` | 2/2 | 0/0 | blocking | chemicals缺失；不能把非空且有有效证据的chemicals仅凭此代码标失效。 |
| `missing_field:conclusions` | `src/extractors/composite.py:41` | 1/1 | 0/0 | blocking | conclusions缺失，其他字段不受该代码自动影响。 |
| `missing_field:methods` | `src/extractors/composite.py:41` | 5/5 | 0/0 | blocking | methods缺失，常与回退失败/超限共同描述同一字段，不重复计算失败论文数。 |
| `operation_failed` | `src/pipeline/single.py:77` | 1/1 | 0/0 | blocking | 当前生成路径已清空整条结果；若未来保留三字段却沿用此代码，则必须报分类错误。 |
| `ner_failed:<block>` | `src/extractors/ner.py:41` | 0/0 | 0/0 | informational | 可选NER失败，现实现保留规则基线；增强覆盖不足不等于基线证据失效。 |
| `ner_invalid_offset:<block>` | `src/extractors/ner.py:44` | 0/0 | 0/0 | informational | 无效NER候选已经丢弃，不能再撤销未受影响的有效基线字段。若无任何化学物，由missing_field阻断。 |
| `ner_overlap:<block>` | `src/extractors/ner.py:50` | 0/0 | 0/0 | informational | 冲突候选被跳过，保留原有证据；待审阅提示，不自动降级有效字段。 |
| `llm_input_limit` | `src/extractors/llm.py:27` | 0/0 | 0/0 | informational | 模拟增强未执行，保留基线。 |
| `llm_timeout` | `src/extractors/llm.py:42` | 0/0 | 0/0 | informational | 模拟增强超时，保留已验证基线。 |
| `llm_response_rejected` | `src/extractors/llm.py:43` | 0/0 | 0/0 | informational | 增强响应已拒绝，现输出为基线，不是让错误响应成为有效证据。 |
| `llm_evidence_rejected` | `src/extractors/llm.py:39,41` | 0/0 | 0/0 | informational | 增强候选的错误证据未进入结果；基线完整性检查仍执行，不能据此豁免错误的最终候选。 |

按此待确认建议，冻结结果共有89条warning：informational 75条、blocking 14条。blocking涉及字段失效，不是“看起来严重”的同义词。数量是消息数，不是问题数或论文数。

## 每篇冻结告警概览

| arXiv | 结果条数 | 拟informational | 拟blocking | 状态说明 |
|---|---:|---:|---:|---|
| 2501.00534 | 8 | 6 | 2 | partial |
| 2501.00561 | 1 | 0 | 1 | failed |
| 2501.00564 | 9 | 6 | 3 | partial |
| 2501.00589 | 11 | 11 | 0 | partial |
| 2501.00591 | 10 | 7 | 3 | partial |
| 2501.00600 | 8 | 6 | 2 | partial |
| 2501.00620 | 23 | 20 | 3 | partial |
| 2501.00679 | 18 | 18 | 0 | partial |
| 2501.00680 | 1 | 1 | 0 | partial |
| 2501.01468 | N/A | N/A | N/A | skipped，未执行抽取 |

## 动态代码的逐值次数

| 实际代码 | 结果次数/篇数 |
|---|---:|
| `conclusions_fallback` | 2/2 |
| `methods_fallback_rejected` | 3/3 |
| `methods_fallback_truncated` | 2/2 |
| `missing_field:chemicals` | 2/2 |
| `missing_field:conclusions` | 1/1 |
| `missing_field:methods` | 5/5 |
| `operation_failed` | 1/1 |
| `page_10_possible_multicolumn` | 1/1 |
| `page_11_possible_multicolumn` | 2/2 |
| `page_12_possible_multicolumn` | 4/4 |
| `page_13_possible_multicolumn` | 2/2 |
| `page_14_possible_multicolumn` | 2/2 |
| `page_15_possible_multicolumn` | 1/1 |
| `page_16_possible_multicolumn` | 1/1 |
| `page_17_possible_multicolumn` | 1/1 |
| `page_18_possible_multicolumn` | 2/2 |
| `page_1_possible_multicolumn` | 5/5 |
| `page_20_possible_multicolumn` | 1/1 |
| `page_23_possible_multicolumn` | 2/2 |
| `page_24_possible_multicolumn` | 1/1 |
| `page_25_possible_multicolumn` | 1/1 |
| `page_26_possible_multicolumn` | 2/2 |
| `page_27_possible_multicolumn` | 1/1 |
| `page_28_possible_multicolumn` | 1/1 |
| `page_29_possible_multicolumn` | 1/1 |
| `page_2_possible_multicolumn` | 5/5 |
| `page_30_possible_multicolumn` | 1/1 |
| `page_31_possible_multicolumn` | 2/2 |
| `page_33_possible_multicolumn` | 1/1 |
| `page_34_possible_multicolumn` | 1/1 |
| `page_35_possible_multicolumn` | 1/1 |
| `page_3_possible_multicolumn` | 7/7 |
| `page_4_possible_multicolumn` | 5/5 |
| `page_5_possible_multicolumn` | 4/4 |
| `page_6_possible_multicolumn` | 5/5 |
| `page_7_possible_multicolumn` | 4/4 |
| `page_8_possible_multicolumn` | 3/3 |
| `page_9_possible_multicolumn` | 3/3 |

## 测试、历史与非warning项

- `empty_fixture`（acceptance/m06_resume.py）、`updated`（acceptance/m02_storage.py）：测试哨兵，真实10篇次数0，不注册为生产告警；若出现在生产输入，按未登记分类错误处理。
- `methods_fallback:abstract`只在跳过的历史用例中出现；当前M12禁止摘要回退。当前结果次数0，不借兼容旧代码允许不符合当前规则的抽取。
- `invalid_source_location`、`unsupported_chemical_removed`存在于历史work生成器、变异克隆/旧安装副本中；当前src的M14直接拒绝完整性错误，不再以这两个warning返回结果。真实冻结结果次数0，不将历史复制树当现行生成器。
- `removed_margin_or_page_number:<block>`为CleanedView.logs内部日志，进入ParsedPaper时转成removed_block；不能把两者重复统计。
- 当前未发现font_info_missing、line_join_inferred等实际生产告警生成点。字体/行连接只是需求中的示例，本轮不凭空生成代码或假报次数；以后新增先登记。
- error_kind（如validation_failed、needs_ocr）及skipped_reason属于独立错误/状态数据，不自动当作warnings代码。

## Blocking语义与未登记策略（待确认）

blocking只描述至少一个字段实际缺失/降级或其证据失效。若三字段均有有效证据、没有任何字段降级，却携带blocking代码，选择明确报 WarningClassificationError，而不是人为把结果改成partial。
未登记代码也报分类错误，不自动当informational放行，也不凭空声称某字段已经失效。分类错误属于政策/配置问题，不应被包装成“论文三字段为空”；后续实现需在发布前显式失败并保持上一代导出不变。
最终候选的切片不等、非空无证据、字段—证据矛盾仍是数据完整性异常，直接拒绝；不以informational标签覆盖。可选增强的错误候选已被丢弃且回到合法基线时，其拒绝提示属于informational。

## 实现与统计边界

只有本清单确认后才实现分类。保持ExtractionResult.warnings原始字符串及M01九字段results.jsonl；分级进入独立warnings_by_severity.jsonl。不能通过给results追加paper_id或warnings字段绕过extra=forbid。
分级文件与主结果一行对应；skipped无主结果行，因此不放入分级文件，10篇报告单独列skipped及N/A告警。success只表示现有数据完整性检查及本轮状态政策通过，不证明00589错序/图注/致谢问题已修复。

## A项确认后登记的内部失败标记

`warning_classification_error`：生成于pipeline单篇边界，基线10篇次数0；blocking，仅用于字段及证据已全部清空的失败结果。FailureRecord固定reason同名、error_kind=validation_failed，由统一predicate识别；属于程序内部分类遗漏/矛盾，不属于论文内容问题。分类逻辑实现于src/extractors/warning_policy.py，原清单次数为修复前冻结基线，后续实际次数见docs/stage_a报告。

B项新增：`caption_block:<raw_block_id>`，由src/parsers/sections.py生成，informational。仅标记阅读视图中被判为caption并排除的raw区间；raw_blocks不改写，同一raw块可能只部分排除。不是证据失效告警；实际字段为空仍由missing_field阻断。

C项新增：`methods_primary_bounded`，src/extractors/methods.py生成，informational。表示从命名方法候选区取连续完整raw块作为有界片段，不是完整方法覆盖；字段及原文证据仍有效，不能据此当作blocking。未找到可容纳的完整块时methods为空、missing_field:methods阻断。
