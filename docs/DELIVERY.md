> 当前研究工作台为0.2.0，完整交付与限制见 [RESEARCH_DELIVERY.md](RESEARCH_DELIVERY.md)。以下0.1.2为冻结核心的历史说明，不能作为当前抽取准确率证明。

> 当前完整研究工作台为0.2.0。安装、使用与质量限制见[RESEARCH_DELIVERY.md](RESEARCH_DELIVERY.md)；下文为0.1.2历史交付记录。

当前完整工作台说明见 [RESEARCH_DELIVERY.md](RESEARCH_DELIVERY.md)。下文保留0.1.2历史交付记录。

# MatterLens 0.1.2 交付说明

半自动文献筛选工具，需人工复核，不保证完整性。**质量未达生产标准。**

## 交付清单

- 网站：https://matterlens-research-6af992.takheichen59.chatgpt.site ，保留拥有者私有访问。
- `dist/paper_extraction_contracts-0.1.2-py3-none-any.whl`：Python CLI＋完整本地网页。
- `dist/paperlens-0.1.2-source.zip`：源码、22份验收脚本、固定样本、网站源码、报告与复验工具。
- `dist/SHA256SUMS`：以上两个发行文件校验和。
- `docs/release/ACCEPTANCE.txt`：160活动场景、3开关、2恢复断言的真实输出。
- `docs/release/WEB_LOGIC.txt`：10项网页逻辑/API输出；不是浏览器交互测试。
- `docs/release/CONTRACT_INTEGRITY.json`：contracts/storage 12文件哈希未变。
- `docs/stage_b`、`stage_c`、`stage_d_final`、`stage_e`：逐阶段真实语料回归。
- `docs/PROGRESS.md`：完整变更记录与已知缺口。

## 安装与运行

Python3.11+，虚拟环境内执行：

```bash
python -m pip install paper_extraction_contracts-0.1.2-py3-none-any.whl
paperlens --help
paperlens-web --online
```

本地网页在 http://127.0.0.1:8765，实际调用Python流水线；上传PDF不离开本机。托管网站有arXiv检索、回归结果浏览和浏览器快速预筛，不托管PyMuPDF；预筛结果有独立extraction_method，不计入Python质量统计。

源码解压后最小JSONL示例：

```bash
python -m pip install -e .
paperlens run --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results
```

输出位置为 `work/demo/results/versions/<id>/`；CURRENT一次原子发布 results/failures/review/warnings_by_severity 四文件。读取使用README中的共享快照，禁止消费方直接open当前结果。skipped只进failures和报告。首次安装可能需联网，安装后的离线样本和验收无网络依赖。

## 实际质量与边界

- 同批10篇：submitted10、success4、partial5、failed0（内部分类0／内容处理0）、skipped1。
- methods长度200–3000：6/10，仅长度指标，不等于语义完整。
- sections含UNKNOWN：9/10；UNKNOWN还承载Introduction和前置文本，不能当作9篇都漏标题。
- 泄漏审计：3篇全部片段可判定、6篇unresolved、1篇不适用；199片段已判定、22未判定，已判定范围检出0条。逐篇原因在docs/stage_e/LEAKAGE.md，结论不覆盖未判定区间。
- 独立阳性审计自检检出00589致谢续段，退出码0；无缓存时可退出2并明确SKIP，不能冒充通过。
- 化学物20项有助理上下文审阅支持；不是独立人工金标准。未测recall，不以该观察值宣称达到生产准确率。
- 2501.01468：129565883字节来自Content-Length，实际接收0，size_limit跳过。2501.00600：40474244字节完整下载，未跳过。
- 00589的FIG.6不进候选、p6-b31归入方法而非结论；前后首段对照在docs/stage_b/REPORT.md。

已知缺口：扫描件需外部OCR；方法可能仅覆盖一个子节；补充材料保守排除；多栏和表格仍可能漏字/断句；小词典和有限价态不覆盖所有化学式；单进程协调、内存批次；无真实模型。success只表示证据结构满足政策，所有科研使用都需人工复核。

## 复验命令

```bash
python scripts/verify_all.py
python scripts/verify_resume.py
python acceptance/m20_end_to_end.py
node scripts/verify_web_assets.mjs website

paperlens run --manifest docs/audit/real_manifest.json --online --db work/eval/state.sqlite3 --workdir work/eval/cache --output work/eval/results
python scripts/audit_leakage.py --output work/eval/results --cache work/eval/cache --report work/eval/LEAKAGE.md
python scripts/audit_leakage_selfcheck.py --output samples/audit_positive --cache work/eval/cache
```

恢复检查确实强制终止子进程，再运行resume；已完成论文三个阶段attempts保持1，中断解析attempts变2。不是正常退出后重复运行的替代测试。

Node只用于可选网站逻辑验证；Python工具无需Node。HTTP网页适配器有5个离线场景。受管环境未提供cua_repl.js，未执行浏览器点击或响应式视觉验收；不能将逻辑/API通过称为浏览器验收。

## 完成边界

版本0.1.2，未修改M01契约、M02表结构或已有方法签名；未接入真实NER/LLM、密钥或新Python运行依赖。发布与隔离安装结果另附于docs/release。网站数据为固定回归样本，在线检索结果单独标注。

交付后科研质量提升另立项目，重新评估模型直抽、专用NER和人工标注路线。本轮不继续追加质量修复。
