> 修复前冻结审查报告。最新实现与同批重跑结果见 ../fixes/REPORT.md；本文件中的“未修改实现”描述仅对应当时审查阶段。

# 真实语料前置抽查（2026-11-15）

结论：104 项仅证明已定义的契约与合成场景。当前抽取结果不足以作为科研信息验收通过的依据。本轮只增加审查脚本和文档，没有修改任何 src/ 实现、M01 契约、M02 表结构，也没有接入模型。

## 一、验收强度

- 逐脚本 AST assert、显式 AssertionError 及文本匹配计数见 assertion_density.json。计数不是覆盖率；M01 使用显式分支判断，不能因没有 assert 就说没有校验。
- M02 原验收有 24 个 assert，实际覆盖 FK 错误包装、重复 run_id 的 PK 错误、嵌套回滚、版本重开、0002 部分 DDL 回滚。原脚本没有独立覆盖 CHECK 包装。新增 audit_contract_checks.py 实测 PK/FK/CHECK 均保留 IntegrityError cause，并包装为 STORAGE / VALIDATION_FAILED / retryable=False，全部通过。
- M14 原验收样本 4 只将 block_id 改为 absent。临时克隆实现中移除字符切片相等检查，原 M14 五项仍通过；移除整段定位检查时才失败。原验收确实存在同 block 错偏移的盲区。补充错偏移、错页码实测均被现有实现拒绝。
- 变异测试只修改 work/audit/mutations 的独立克隆，没有修改实际 src。详见 mutation_checks.json。
- M07 多栏样本只要求同时读到左右列并给出告警；M20 多栏样本只检查 partial、化学物和复核告警，没有检查 methods/conclusions 的正确内容。这两项无法证明阅读顺序或字段可用性。
- tasks 当前实际为方案 B：UNIQUE(paper_id, stage)。Stage.STORAGE 和 Stage.EXPORT 存在，错误包装实测为 storage。旧 PROGRESS 已记方案 B，但没有单独记 Stage 补丁，现已补充；不能仅由文档缺项推断实现使用旧设计。

## 二、合成输出核查

3 篇示例、9 条证据逐条回溯到缓存 ParsedPaper 的原始 block：字符切片、页码、章节全部一致；方法/结论按原始 block 顺序拼接；无 success 搭配空方法/结论；失败与复核队列为空。未出现 °C、Fig. 2、XRD、SEM、TEM 噪声。

这只是干净样本核查。JSONL 有多行 JSON，不能整体交给 python -m json.tool；应逐行解码。

## 三、真实来源与语料

实际调用官方 arXiv Atom API：cat:cond-mat.mtrl-sci AND submittedDate:[202301010000 TO 202412312359]，按 submittedDate 降序取前 10 篇，属于便利样本，不是随机代表集。原始响应、类别、标题、日期均保存。ID 为 2501 是公告编号，保存的投稿日期仍是 2024-12-31。

3 篇冒烟使用实际元信息查询和 PDF 下载：0 success / 2 partial / 1 failed。
10 篇批次使用刚从官方 feed 获取的冻结元信息及真实 PDF 下载：0 success / 8 partial / 2 failed，CLI 退出码 3，耗时 29.83 秒。未用本地替代 PDF 绕过失败。

| arXiv ID | status | chemicals 数 | methods 字符 | conclusions 字符 |
|---|---|---:|---:|---:|
| 2501.00680v1 | partial | 5 | 2491 | 789 |
| 2501.00679v1 | partial | 2 | 5306 | 166 |
| 2501.01468v1 | failed | 0 | 0 | 0 |
| 2501.00620v1 | partial | 0 | 2018 | 0 |
| 2501.00600v2 | failed | 0 | 0 | 0 |
| 2501.00591v1 | partial | 14 | 16238 | 0 |
| 2501.00589v2 | partial | 4 | 42376 | 467 |
| 2501.00564v1 | partial | 1 | 6570 | 1980 |
| 2501.00561v1 | partial | 10 | 14513 | 2762 |
| 2501.00534v2 | partial | 1 | 6152 | 3684 |

两次下载失败均为真实 application/pdf、HTTP 200，文件大小分别为 129565883 和 40474244 字节，超过默认 20 MiB。不是 arXiv ID 不存在，也不是 OCR/解析失败。10 篇中下载成功 8/10；对已下载 PDF 的解析成功 8/8。仅 8 篇进入抽取，不能声称已完成 10 篇的字段质量评估。

## 四、真实字段质量

8 篇解析结果中：方法字段非空 8/8，结论字段非空 6/8，但识别到 methods 章节为 0/8、conclusions 章节为 2/8、references 章节为 3/8。字段非空不能作为正确率。

确认的问题：

1. M09 不识别 `VI.\nMETHOD`、`V.\nMETHODS`、`VI.\nCONCLUSIONS` 等罗马数字标题，也没有覆盖 `2 Calculation details`。这些原文标题已在 raw_blocks 中，不需要 OCR 才能读到。
2. 2501.00679 的正文直到文献都被挂在 Abstract 下，结论仅拼出两段半句；2501.00680 的 conclusions 带入 Acknowledgments、基金号和作者信息，methods 还带入标题。
3. 2501.00589 的 methods 达 42376 字符；2501.00561 的 conclusions 从讨论段落开头抽起。这是关键词段落堆积，不能当作可用的方法或结论。
4. 2501.00589、2501.00591 的参考文献没有被正确分段，至少 8 个文献独有材料名进入 chemicals。
5. `HK0`、`HK1` 晶面标记和 `SC0012704`、`SC0020221`、`SC0016434` 基金编号被当作化学式。其中 2501.00564 的唯一 chemicals 是基金编号。
6. M07 多栏告警存在确定误报：视觉检查为单栏的 2501.00680 第 2 页，仅居中页码“2”就同时满足左右列阈值，导致 multi-column 告警。0 success 因此也受错误质量标记影响，不能直接当成 0% 内容正确率。
7. 267 条真实证据的原始切片、页码、章节和字段内 block 顺序检查全部通过。引用可回溯并不能保证它是完整句子、正确实体或相关字段。

## 五、37 个实体逐条上下文审阅

标注文件：chemical_annotations.csv / .json。审阅者为本助手，尚未经过独立领域专家裁定，不能称为人工金标准。按“每篇去重后实体”计数，未做实体标准化，也未标注全文漏检，所以没有 recall 数值。

口径：正文、摘要、标题中的化学物/元素/材料组成允许，包括背景材料；参考文献、基金编号、晶面标记排除。缺陷位点、配位多面体、表面终止层组成标为边界项。

- 19 项：确认满足目标字段口径。
- 13 项：确认不满足，其中 8 项参考文献泄漏、3 项基金编号、2 项晶面标记。
- 5 项：口径待裁定，CrGa、GaO4、GaO6、BiO、FeO2。

目标字段 precision 的保守值为 19/37 = 51.4%；5 项边界全接受时为 24/37 = 64.9%；排除边界项后的可判定样本 precision 为 19/32 = 59.4%。这些是小便利样本的助手审阅统计，区间跨过 60% 决策阈值，不能据此直接断言模型上线门槛已触发。

若只问“字符串是不是化学/材料概念”，不管是否来自被禁止的参考文献，则为 27/37 = 73.0%，上限 32/37 = 86.5%。这个数字不能代替目标字段 precision。

## 六、建议返工顺序

1. 先裁定 5 个口径边界项，把助手标注交由领域人员复核，冻结评测样本。当前没有 recall 金标准，不能判断“precision 尚可但 recall 低”。
2. 修复 M07 多栏误报和 M09 标题/正文/参考文献/致谢边界，再复跑同一批样本；给 M07/M09/M14/M20 补能检出这些真实失败的断言。已有 8 项误报明确来自参考文献泄漏，单独换 NER 不会解决该来源问题。
3. 给 M10 加基金编号、晶面标记等负例与上下文约束，再决定词典或真实 NER。完成前两步后若经专家复核的 precision 仍低于 60%，优先评估化学 NER；只有完成漏检标注后才能用 recall 决定是否扩词典。
4. 单独处理下载体积配置和主动错误分类。当前 failures.jsonl 对下载失败还附加 extract_failed 汇总项，统计时必须以 task/error_event 的真实失败阶段为准。
5. OCR 不在这批样本的首要路径：已下载的 8 篇都有可读文本。大规模来源覆盖和新模型接入均未在本轮实施。

## 复验

```bash
python scripts/audit_contract_checks.py
python scripts/audit_saved_evidence.py
python scripts/audit_demo_trace.py

paperlens run --manifest docs/audit/smoke_manifest.json --online --db work/audit-replay/smoke.sqlite3 --workdir work/audit-replay/smoke-cache --output work/audit-replay/smoke-results
paperlens run --manifest docs/audit/real_manifest.json --online --db work/audit-replay/ten.sqlite3 --workdir work/audit-replay/ten-cache --output work/audit-replay/ten-results
```

在线复验受远端服务影响，输出可能变化。冻结的实际 CLI 输出见 ten_cli_run.json；全文预测见 real_results.jsonl；保存的原始 block 及 PDF 哈希见 source_blocks.json。
