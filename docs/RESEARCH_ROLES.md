# 材料角色、数值归属与可读交付

此功能属于 `research-1` 规则记录，不是新版工作区的 `ScientificRecord`。没有配置或调用外部模型，不改变任何数据库、冻结契约或旧存储接口。

## 保留原始结果

`materials` 仍是全部化学物候选，可能包含背景材料；`experimental_data` 仍是原始数值句候选。方法、发现、结论不作静默改写。

新增 `attribution` 解释层，版本 `context-roles-v1`：

- `materials`：逐材料汇总角色，并保留每次提及的角色、规则理由、原句证据与必要的前文归属证据。角色为 `study_subject`、`background`、`comparator`、`reagent_or_environment`、`uncertain`。本文对照与背景文献中的比较分开。
- `numeric`：用 `candidate_index` 对应原始数值句，分为 `own_result`、`simulation_parameter`、`experimental_condition`、`cited_result`、`uncertain`。同一句混合参数、结果或跨研究比较时保留不确定，不拆造新结果。
- `review_status` 固定为 `unreviewed`。原字段的人工修订不等于归属层已经复核；自动结果、人工覆盖和来源均保留。

归属依据包括明确的本研究动作、标题中的材料、样品制备、对照措辞、前文的他人研究归属和章节候选。规则不等于语义理解，仍会漏报和误报。没有通过单位、关键词提及或原句存在性来认证科学主张。

提取器升级为 `scientific-evidence-v1.2`，旧指纹不会被当作新版本结果复用；旧记录进入现有历史目录。只导出而不重跑的历史记录不补写归属，文件明确标记 `NOT_EXECUTED_HISTORICAL_RECORD`。未迁移或混用新旧记录格式。

## 运行与实际文件

已有合法本地清单：

```bash
python -m research run --manifest /path/to/manifest.json \
  --workdir work/roles-library --output work/roles-export --workers 1
```

输出路径见 `CURRENT.json`。其中：

- `research.xlsx`：阅读汇总、原始字段与修订、材料角色、数值归属、证据、说明，共六个表。阅读汇总显示自动原文；人工修订另列，归属仍待复核。
- `research.jsonl`：包含原始块、原始候选、新归属、证据和可能的人工修订。
- `results.jsonl`：原有旧格式，不加入归属字段。
- `research.csv`：保留原列并追加角色列；`material_roles.csv`、`numeric_attribution.csv`、`evidence.csv` 提供明细。
- `processing-report.pdf`：从实际记录生成的处理报告，**不是原始论文**。
- `preview.html`：本地阅读预览，链接同目录的实际文件；没有独立助手导读或人工金标准。
- `manifest.json`：文件哈希；`review.jsonl` 与 `failures.jsonl` 保留复核队列和失败项。

所有证据的字符区间仍逐字等于 `raw_blocks` 切片。该校验不证明内容归属、科学解释或结果完整性正确。Excel 单元格达到格式长度上限时会明确标记截断，完整数据留在 JSONL。

## 五篇真实论文复现

已保存公开源元数据、CC BY 4.0 许可和固定 PDF 哈希，不提交真实 PDF 或用户库。联网重获：

```bash
python scripts/acquire_role_corpus.py --output work/real-role-corpus
python scripts/validate_real_roles.py \
  --manifest work/real-role-corpus/manifest.json \
  --workdir work/real-role-library --output work/real-role-export
```

获取脚本实际调用平台现有 `OfficialSourceAcquirer`，逐篇核对当前许可、限制大小、探测真实 PDF、验证固定哈希，并生成显式 research 清单。复用获取组件不导入任何数据库。此官方白名单网络策略与通用 IP 固定下载不同。

若有旧版本生成的合法基线 JSONL，可给验证器加 `--baseline-jsonl /path/to/old/research.jsonl`。它检查原字段和原证据文本/偏移/页码保持相等，允许提取器策略版本发生预期变化。已知 BiFeO3 示例断言来自用户交接说明，不是独立人工金标准。

新交付文件的真实浏览器检查：

```bash
python tests/browser/run_research_delivery.py --directory /absolute/export/version \
  --browser /usr/bin/chromium --output work/delivery-browser
```

本轮实测及明确缺口见 [QA 报告](qa/attribution-20261117/REPORT.md)。材料候选覆盖和章节识别仍需优先修复，再扩展20篇质量回归。
