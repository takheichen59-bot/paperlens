# Phase 1 — 材料科学综合文献获取与索引

本阶段只完成搜索、识别、去重和下载。固定语料集包含 **20 篇真实 arXiv 论文、352 页、87,246,820 字节**，逐篇核验 CC BY / CC BY-SA / CC0 许可、所有页面的文本可读取性、首屏渲染和 SHA256。

网站： https://matterlens-research-6af992.takheichen59.chatgpt.site

安装：Python 3.11+；解压源码 ZIP 后在根目录运行 `python -m pip install .`。网页用户无需安装 Python。

## 直接使用

1. 网站进入“已核验的 20 篇”，下载 PDF 资料包和文献索引 Excel。
2. 或在“搜索论文”输入英文关键词，留空检索材料科学综合。勾选后点击“批量下载 PDF”。
3. 下载完成后点击“保存 PDF 资料包”，保存实际文件到电脑；也可导出 Excel、CSV、JSONL 索引。
4. ID 列表支持 arXiv 链接及版本号，同一来源 ID / DOI 去重，下载后再次按 PDF SHA256 去重。失败项单独保留，可重试。

固定文献集是一次材料科学综合获取样本，不是系统综述，不保证覆盖完整或最新。来源检索参数、原始 Atom 响应与文件哈希随源码提供。许可来自每篇官方摘要页的 Rights to this article 链接，保留作者和原文 URL 以支持署名。

## 输出

- `PDF/*.pdf`：实际获取的原始 PDF；固定文献集 20 个文件。
- `index.json` / `index.jsonl`：标识符、作者、标题、DOI（允许为空）、官方 URL、许可、页数、字节数、文本字符数、SHA256。
- `SHA256SUMS`：PDF 文件校验值。
- Excel / CSV：可在网站单独下载；自选批次的资料包也包含这两个格式。
- `attempts.json`：Python 获取脚本的逐候选处理日志，保留许可不符、超限和失败原因。

固定资料集 PDF 持久化在本站文件存储中；浏览器自选批次的 PDF 仅在当前页面暂存，需保存资料包。刷新后本设备索引可恢复，PDF 要重新获取。

## Python 安装与获取

需要 Python 3.11+，只使用项目原有依赖。解压 Phase 1 源码到新目录：

```bash
python -m venv .venv
# Linux / macOS
. .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -e .
python scripts/phase1_acquire.py --feed samples/phase1/search.atom.xml --dest work/phase1/corpus --count 20
```

上面复用此次官方候选列表，重新逐篇核验许可并下载。若要重新检索最新材料科学候选，指定一个不存在的 feed 路径：

```bash
python scripts/phase1_acquire.py --feed work/new-search.atom.xml --dest work/new-corpus --count 20
```

脚本默认每份 PDF 上限 20 MiB、官方请求最少间隔 3 秒，允许 CC BY / BY-SA / CC0。`--max-pdf-mib 100` 可调整限制。它继续遍历候选直到获得 20 篇；100 个候选不足以凑齐时明确退出 1，不伪造完成结果。同样命令重跑会重新核验已完成 PDF 的哈希和可读取性后跳过，不重复下载。候选失败不影响其他论文。

## 复验实际文件

获取完成后，或把网站下载包解压到 `work/phase1/corpus` 后：

```bash
python acceptance/phase1_acquisition.py --corpus work/phase1/corpus --feed samples/phase1/search.atom.xml
```

5 项分别检查：20 个唯一来源 ID / DOI / PDF 哈希、官方来源与许可、每篇文件与页面可读性、原始检索响应的来源追溯、重跑零网络与不重写已完成文件。

网页源码在 `website/`，逻辑/API 测试：

```bash
cd website
node verify-phase1.mjs
node build.mjs
```

构建与逻辑测试已运行；本环境未提供受支持的浏览器操作工具，未声称已完成浏览器交互验收。

## 范围和下一阶段

这是需人工复核的半自动工具，不保证完整性。文件可读性不等于科研可靠性，arXiv 预印本不一定经同行评审。扫描件、加密 PDF 和超过限制的文件需要人工处理；不绕过付费墙。网页每批最多 50 篇、单篇 100 MiB、暂存合计 300 MiB，暂无跨设备个人文献库。

**当前不把材料、方法、公式、实验数据、结论和发现列为已验证输出。** 原有规则抽取骨架保持不变，作为 Phase 2 的起点而非准确率证明。Phase 2 应基于这 20 篇逐字段核验，再决定 Phase 3 跨论文研究分析，Phase 4 才扩至 500–5,000 篇。
