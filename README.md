# PaperLens — 科学文献检索与研究方法挖掘平台

**版本：0.3.0 · 半自动研究工具 · 需人工复核，不保证完整性。**

帮助研究者批量检索与合法获取论文，保留原文，整理材料、方法、发现与结论，并逐步扩展到算法、数学模型、实验设计及跨论文比较。

**当前定位是可运行的开发版，不是科研级生产系统。** 已验证工程流程，不代表已经验证科研抽取准确率。没有配置真实模型时，深度提取明确返回 `NOT_EXECUTED`，不会用规则摘要或虚构内容填充。

- [完整功能说明](docs/PROJECT_OVERVIEW.md)
- [目前问题与优先级](docs/KNOWN_ISSUES.md)
- [安装与运行](docs/INSTALL.md)
- [架构、API 与数据字典](docs/ARCHITECTURE.md)
- [本次测试与外部验证状态](docs/VALIDATION.md)
- [历史 0.2 使用说明](docs/LEGACY_README_0_2.md)

## 当前可以做什么

| 能力 | 实际实现 | 验证边界 |
|---|---|---|
| 多来源检索 | Crossref、OpenAlex、Semantic Scholar、arXiv；Springer、Elsevier 授权适配器 | Crossref/OpenAlex 各取得20条真实记录；S2 遇到429；出版商授权未测 |
| 去重和筛选 | DOI 规范化、来源标准化、标题/作者/年份辅助去重、年份/引用/OA筛选 | 小规模与离线测试；不是全文相关性质量评测 |
| 全文获取 | OA链接、授权上传、哈希、大小与格式检查、逐跳重定向检查 | 一篇本轮真实在线下载；已有20篇真实PDF导入解析 |
| 规则信息汇总 | 材料、方法、结论、发现；原文片段、人工修订、CSV/Excel/JSONL | 旧版20篇非空率已记录；没有独立人工准确率评测 |
| 文档解析 | PyMuPDF；Tesseract OCR；JATS XML；GROBID/Docling 适配器 | 真实PDF解析与合成扫描件OCR执行；真实双解析器未执行 |
| 专项 AI 提取 | 研究问题、贡献、算法、数学、方法、实验、结果、局限、结论等专用任务 | 有严格Schema和证据校验；真实LLM未配置、未执行 |
| 研究情报 | 算法浏览、2–10篇比较、来源关系图、BM25检索、带阈值的问答入口 | 结构性测试通过；真实嵌入、生成式问答和研究假设未验证/未实现 |
| 数据可靠性 | 持久队列、逐篇隔离、暂停/恢复、历史记录、来源变更失效、复核冲突检查 | 真实进程终止/恢复已测；没有真实5000篇性能承诺 |
| 网站 | 新版本地科研工作区；保留旧版Worker网站源码 | Chromium12项流程+5项真实来源冒烟已执行；跨浏览器/生产验收未完成 |

## 托管网站：一键批量获取与报告

打开 [PaperLens 研究工作台](https://paperlens-research-workspace.halvedbolt3.chatgpt.site/)（保持所有者私有访问）。首页输入英文关键词或arXiv ID，选择5/10/20篇，点击 **一键爬取并生成 PDF / Excel**。执行时保持标签页开启；完成后可自动下载含原论文、处理报告、Excel和JSONL的ZIP。失败可单独重试，已完成记录保留。

托管流程使用PDF.js和通用规则，报告按固定章节生成，缺失项保留；并非模型深度解读。当前真实关键词批次5篇已处理并下载校验，另外5篇固定真实PDF重新解析。浏览器12项原流程与17项托管流程检查通过（合成工程语料，不是科研准确率）；尚未做20篇真实全文批量回归。见 [操作与限制](docs/BATCH_WORKFLOW.md)、[报告框架](docs/REPORT_FRAMEWORK.md)及[本轮实际验收](docs/qa/one-click-20261118/REPORT.md)。

## 快速启动新版网站

Python 3.11+。在仓库根目录：

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[platform,test]'
python -m science_platform serve --data ./data/science-platform
```

打开 **http://127.0.0.1:8765**。

Windows 可运行 `launch/start.bat`；Linux/macOS 可运行 `bash launch/start.sh`。**Windows 脚本尚未在 Windows 实机验收。** 如不需要 AI，可直接使用元数据检索、上传、下载、解析及导出；深度提取页面会明确说明未执行。

如需模型，在服务器复制 `.env.example` 为 `.env`，填写 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`。CLI 启动时读取 `.env`，不会把密钥写入浏览器。外部模型会接收到选定的论文片段；提交前确认论文许可和服务的数据政策。设置文件不要提交到 Git。

## 批量下载与材料科研汇总

旧版规则流水线继续可用，不需要模型密钥：

```bash
# 材料科学综合：在线搜索、核对CC许可、下载、规则汇总、导出
paperlens-research sync --online --count 20 \
  --workdir work/library --output results

# 使用已下载的本地论文清单；相同命令支持恢复
paperlens-research run --manifest /path/to/corpus/index.json \
  --workdir work/library --output results --workers 2
```

规则结果保留材料、方法、发现、结论和证据；不能当作已完成的深度算法分析。输出路径由命令打印。格式、失败队列与复核说明见[旧版交付文档](docs/RESEARCH_DELIVERY.md)。

新增材料角色和数值归属规则候选：区分本文对象、背景、对照，以及本文结果、模拟参数、实验条件和引用结果，保留原始候选及证据。导出包含六表Excel、JSONL、证据CSV、阅读预览和处理报告PDF，详见[规则归属与交付](docs/RESEARCH_ROLES.md)。本轮五篇真实PDF的实际结果和缺口见[验证报告](docs/qa/attribution-20261117/REPORT.md)。

## 新旧数据边界

- `src/contracts/` 与 `src/storage/` 的12个已冻结文件保持不变。
- 新平台使用独立的 `data/science-platform/platform.sqlite3`，不会自动升级旧 M02 数据库。
- `research` 库的规则记录、新版 `ScientificRecord` 和托管网站记录是不同格式；不会静默混为同一套分析结果。
- GitHub 存放源码、合成测试样本和评测报告，**不包含个人文献库、真实PDF缓存、密钥或数据库**。真实PDF需要合法重新获取或自行导入。
- `website/` 是此前托管Worker网站的源码快照，包含本轮未部署的存储修复；新版FastAPI网站在 `src/science_platform/web/`。GitHub仓库建立不等于网站或后端已经重新部署。

浏览器流程修复与实际截图：[本轮报告](docs/qa/workflow-20261117/REPORT.md)。复现见 [浏览器检查说明](tests/browser/README.md)。

## 复验

```bash
python scripts/verify_all.py
python -m unittest discover -s tests/master -v
python acceptance/master_a_integrity.py
python scripts/master_recovery.py
cd website
node verify-site.mjs
node verify-research.mjs
node verify-master-a.mjs
```

OCR测试要求系统安装 `tesseract` 和英文语言数据。Linux 本次重新运行结果、脚本依赖及未测项目见 [VALIDATION](docs/VALIDATION.md)。

**必须先读[当前问题](docs/KNOWN_ISSUES.md)：真实科学质量、模型集成、授权来源、浏览器、规模与部署仍有明确缺口。** 本仓库未授予原创代码的开源许可证；第三方组件与论文遵循各自许可，详见 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。

检索来源故障与恢复机制见[检索维修说明](docs/SEARCH_RELIABILITY.md)，2026-11-19真实正式站检索及20篇全文验收见[维修报告](docs/qa/search-recovery-20261119/REPORT.md)。
