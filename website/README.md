# MatterLens 0.2.0 — 科研文献工作台交付说明

本版把四阶段功能串成可使用的半自动工具：批量获取论文 → 科研记录 → 证据检索与跨论文比较 → 可恢复批处理。网站：

https://matterlens-research-6af992.takheichen59.chatgpt.site

**半自动工具，需人工复核，不保证完整性。功能可运行不等于抽取达到生产质量。** 没有接入真实 NER / LLM，没有改变 contracts/、SQLite 表结构或旧 paperlens CLI 方法签名。新增功能放在 research 包、独立 CLI 和网页业务层。

## 直接使用网站

1. 默认打开“论文与科研记录”，已有20篇真实材料科学论文。
2. 勾选论文，点击“导出科研汇总 Excel”；表内包括材料、方法、主要发现、结论，以及算法、公式/数值候选、DOI、来源、复核状态。
3. 点击任意字段或“证据”，核对原文页码和段落。缺失字段明确留空。
4. “人工复核”可修订四字段。修订单独保存；原始抽取与证据保留。只有用户明确确认对照原文后才标“已人工复核”。复核记录绑定PDF哈希，原文更新后不自动沿用。
5. “20篇完整PDF+汇总”下载所有原始PDF、科研Excel/CSV/JSONL、原三字段JSONL、失败与复核队列、索引及SHA256SUMS。
6. 用“搜索/导入论文”在线检索、批量粘贴arXiv ID或选择本地PDF。“下载并提取”完成后保存当前资料包。
7. “跨论文对比”并列所选论文的材料、方法、结果和局限。“按证据检索”返回相关原文与引用。“提及关系”可以点击材料/算法查看关联证据。

原始PDF请按每篇许可使用；本站不绕过付费墙。固定20篇全部核验CC开放许可。原文摘录及复核结果保存于当前仅所有者可访问的工作区；本地PDF本身不上传。PDF暂存网页，刷新后需重新获取；科研记录保存到工作区。

## 实测范围与质量

| 指标 | 实测值 | 意义 |
|---|---:|---|
| 真实PDF | 20篇 / 352页 / 87,246,820字节 | 全部实际下载、SHA256去重、文本检查 |
| 结构化记录 / 处理失败 | 20 / 0 | 不是内容准确率 |
| 材料字段非空 | 18/20 | 词典与保守化学式规则 |
| 方法字段200–3000字符 | 10/20 | 有界方法原文，不代表人工确认可用 |
| 结论字段非空 | 15/20 | 原文定位，不补写 |
| 主要发现非空 | 17/20 | 结果/结论句候选 |
| 算法 / 公式 / 数值候选非空 | 13 / 19 / 19篇 | 无语义模型，公式不重建LaTeX |
| 原文证据 | 956条 | 字符切片与页码一致 |
| 人工复核 | 0/20 | 尚无独立人工准确率评价 |

全字段位置审计：2篇全部片段有已知章节标签，18篇含未识别章节，共414条片段归属 unresolved。已知抽取视图中没有片段进入被标为references/supplement的区间；**不能据此声称全字段零泄漏**。详细逐篇原因见 RESEARCH_LEAKAGE_AUDIT.json。旧泄漏审计自检在当前缓存环境下返回2（SKIP: cache unavailable），这是前置缓存不可用，不能当作审计逻辑通过。

## 四阶段交付边界

- Phase 1：真实20篇的搜索、识别、去重、许可、下载和索引已实测。
- Phase 2：20条结构化记录与可追溯证据已生成；公式和数值为候选，质量未达生产标准，缺失与未知章节需人工复核。
- Phase 3：提供并列比较、确定性词项哈希向量检索、正文提及图谱和带引用检索助手。不是语义模型检索或自由生成问答；关系不表示因果或材料确被使用。
- Phase 4：本地最多5,000条任务的有界调度、内容哈希检查点、失败隔离、人工复核、版本化导出与重复更新。5,000条合成任务通过真实SIGKILL恢复测试；真实语料评测仍为20篇，未验证5,000篇真实PDF的下载耗时、内存和准确率，未部署分布式集群。

网页每批最多50篇、单篇100MiB、暂存PDF合计300MiB；网页读取最多300页。大批任务用下面的Python命令。

## 安装

Python 3.11+，Linux / macOS。Windows建议WSL2（本地状态库使用标准库fcntl单写入锁）。

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install paper_extraction_contracts-0.2.0-py3-none-any.whl
# 或在完整源码目录执行：python -m pip install .
paperlens-research --help
```

运行依赖保持原集合：pydantic、httpx、feedparser、PyMuPDF、typer及标准库；未增加NER/LLM依赖或密钥。

## 批量处理与恢复

把完整20篇资料包解压到data/后：

```sh
python -m research run --manifest data/index.json \
  --workdir work/library --output results --workers 2
```

中断后重复同一命令。只有PDF哈希、解析器和抽取器版本均匹配的检查点才复用。单篇PDF出错单独记失败，其余继续。输出为版本目录，终端返回output.directory；results/CURRENT.json原子指向完整生成的版本。消费者先读这个指针再读该目录，避免跨版本混读。旧版目录保留供回溯。

自定义manifest.jsonl，每行一篇（pdf相对清单所在目录）：

```json
{"pdf":"PDF/2501.00680v1.pdf","meta":{"paper_id":"arxiv:2501.00680","id":"2501.00680v1","title":"Paper title","doi":null,"url":"https://arxiv.org/abs/2501.00680v1"}}
```

最多5,000条；按paper_id、DOI和PDF哈希去重。PyMuPDF解析在单个进程内串行进入，避免不安全的并发调用；队列和状态写入有界，不宣称CPU并行加速。

```sh
# 在线搜索材料科学综合、核验CC许可并获取20篇，复用下载缓存
python -m research sync --online --count 20 \
  --workdir work/library --output results

# 指定主题；可重复执行用于更新
python -m research sync --online --query 'solid state electrolyte' --count 20 \
  --workdir work/library --output results

# 离线检索和带引用的证据结果
python -m research search --workdir work/library 'DFT'
python -m research ask --workdir work/library 'graphene'
python -m research graph --workdir work/library > graph.json

# 人工复核；edits.json可含materials列表、methods/findings/conclusions文本
python -m research review --workdir work/library --paper-id arxiv:2501.00680 \
  --edits edits.json --decision reviewed --note '已对照原文'
python -m research export --workdir work/library --output results
```

在线来源请求间隔至少3秒，有超时和重试；需要明确--online。不保证任意关键词都能凑足目标数量：候选/许可不足会返回非零并保留已获得文件。体积超限记skipped，普通网络/解析错误记failed，不相互吞并。下载阶段单独日志位于work/library/acquired/download_failures.jsonl。

定期更新可用系统调度器执行同一条sync命令，示例（替换绝对路径）：

```cron
0 8 * * * /absolute/.venv/bin/python -m research sync --online --count 20 --workdir /absolute/work/library --output /absolute/results >> /absolute/update.log 2>&1
```

本交付不替用户创建后台计划任务。新PDF版本导致内容哈希变化时重新处理，并使旧人工复核失效。旧字段与人工修订不混写。

## 文件语义

- research.xlsx / research.csv：每篇一行；显示人工修订后的四字段（如有），保留复核状态。
- research.jsonl：完整科研记录、原始字段、原文块、证据偏移、候选与人工复核覆盖层。
- results.jsonl：旧M01九字段格式，仍只含chemicals/conclusions/methods，不加新字段。
- failures.jsonl：PDF处理异常。某篇三字段不足、但处理成功时留在科研记录与review队列中，不冒充处理异常。
- review.jsonl：待人工复核论文及缺失字段；初始20篇均待复核。
- index.json：固定20篇的元信息与PDF路径。
- SHA256SUMS：原始PDF及科研导出校验和；发布包的下载校验和另见DOWNLOAD_SHA256SUMS。

Excel单元格受32767字符限制，JSONL保留完整文本。数值未做单位/实验条件归一化，不能据此给论文排性能名次。

## 复验命令

```sh
python scripts/verify_all.py
python acceptance/research_science.py
python acceptance/research_intelligence.py
python acceptance/research_batch.py
python scripts/research_audit.py --records data/research.jsonl --output audit.json
python acceptance/phase1_acquisition.py --corpus data --feed samples/phase1/search.atom.xml
cd website
node verify-phase1.mjs
node verify-research.mjs
node build.mjs
```

既有22个验收脚本（20模块+2修复）160项通过；新增科学记录、检索比较、批处理各5场景通过；网页获取19项、科研工作台16项逻辑/API/导出检查通过。独立ZIP/OOXML检查通过。真实20篇进入新CLI并生成JSONL/failures/review；重复运行resumed=20、processed=0。大批测试是合成工程任务，不作为科研准确率证据。

当前环境没有Sites指定浏览器控制工具，因此**未声称浏览器点击、布局和辅助技术验收通过**；线上API、真实下载包及文件哈希另做HTTP实际复验。完整复验记录与已知缺口见RESEARCH_REPORT.md。
