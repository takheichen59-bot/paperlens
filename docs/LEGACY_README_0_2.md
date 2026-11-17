# MatterLens 0.2 — 批量论文下载与科研汇总

网站：https://matterlens-research-6af992.takheichen59.chatgpt.site

材料、方法、主要发现和结论的逐篇汇总，原文证据回查、人工修订、Excel/CSV/JSONL导出，跨论文比较、引用检索、提及关系图，以及最多5,000条本地任务的恢复处理。

**半自动工具，需人工复核，不保证完整性。** 真实20篇已处理；材料18/20、方法10/20、结论15/20、发现17/20非空，尚未独立标注准确率。算法/公式/数值为规则候选，质量未达生产标准。5,000条仅做合成工程恢复测试，不代表5,000篇真实论文已评估。

完整安装、使用、恢复、定期更新、复验与限制：[docs/RESEARCH_DELIVERY.md](docs/RESEARCH_DELIVERY.md)。

```sh
python -m pip install .
paperlens-research --help
python -m research run --manifest data/index.json --workdir work/library --output results
```

以下为0.1.2骨架的历史说明，接口保持兼容；当前网站与完整交付以上述0.2说明为准。

> 当前优先交付 Phase 1：材料科学综合 20 篇真实论文的获取、去重、下载与索引。使用与复验见 [docs/PHASE1.md](docs/PHASE1.md)；获取报告见 [docs/PHASE1_REPORT.md](docs/PHASE1_REPORT.md)。下方原规则抽取骨架不代表 Phase 2 准确性达标。

> 当前推进 Phase 1：材料科学综合 20 篇真实论文的搜索、去重、下载与索引。网站直接提供 PDF 资料包与 Excel。使用与复验见 [docs/PHASE1.md](docs/PHASE1.md)；实测见 [docs/PHASE1_REPORT.md](docs/PHASE1_REPORT.md)。下面保留既有 0.1.2 规则抽取骨架说明，不代表 Phase 2 科研信息准确性已达标。

# MatterLens 0.1.2 — 材料科学文献筛选工具

**半自动工具，需人工复核，不保证完整性。科研抽取质量未达生产标准。**

检索 arXiv、选择论文或上传本地 PDF，抽取 chemicals / conclusions / methods 和可回溯的原文片段。Python 流水线支持批处理、失败隔离、SQLite 状态、断点续跑及 JSONL。第一阶段只有 arXiv，NER / LLM 保持模拟，不需要密钥。

网站：https://matterlens-research-6af992.takheichen59.chatgpt.site （保留拥有者私有访问）。

## 安装与打开网页

Python 3.11+，建议虚拟环境。下载 wheel 后：

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install paper_extraction_contracts-0.1.2-py3-none-any.whl
paperlens-web --online
```

自动打开 `http://127.0.0.1:8765`。该本地网页直接使用已验收的 Python 流水线，可在线处理所选 arXiv 论文或上传 PDF。不要将服务暴露到公网；默认仅监听 127.0.0.1。文件和数据库保存在当前目录的 `work/paperlens-web`，恢复处理时保留该目录。

不加 `--online` 时可离线上传 PDF；在线检索和在线下载默认禁用。端口、工作目录、体积/长度限制可通过 `paperlens-web --help` 查看。托管网站提供 arXiv 检索、真实回归结果浏览及浏览器快速预筛，**不在托管端运行 PyMuPDF**。浏览器预筛使用 PDF.js，不等同于本次评估的 Python 引擎；要使用同一套验收流水线，请启动本地网页。仅加载阅读器时访问 CDN，上传文件不发送到托管站点。

从源码安装：解压源码 zip，进入包含 pyproject.toml 的目录，执行 `python -m pip install -e .`。首次安装可能访问包索引；安装后本地 PDF 与验收不需联网。`requirements-tested.txt` 记录原验证环境直接依赖。

## CLI 最小运行

```bash
# 三篇合成材料 PDF，离线运行
paperlens run --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results

# 关键词检索与在线 arXiv 单篇处理
paperlens search "solid state electrolytes" --max-results 5 --online
paperlens run --arxiv-id 2501.00589v2 --online --db work/real/state.sqlite3 --workdir work/real/cache --output work/real/results

# 同参数恢复；只重试失败论文；独立导出
paperlens resume --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results
paperlens retry-failed --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results
paperlens export --db work/demo/state.sqlite3 --output work/demo/results
```

批量本地清单格式见 `examples/demo_manifest.json`，pdf 相对清单所在目录解析；离线条目必须有 PaperMeta 与本地 PDF。仅使用真实 arXiv ID，不将任意本地文件伪装为其他来源。示例 PDF 是合成测试材料，不能当科研证据。

默认 PDF 上限 **100 MiB**，methods 上限 **3000 字符**。配置见 `examples/limits.toml`；CLI 显式值优先：

```bash
paperlens run --manifest examples/demo_manifest.json --config examples/limits.toml --max-pdf-mib 100 --methods-max-chars 3000 --db work/config/state.sqlite3 --workdir work/config/cache --output work/config/results
```

## 输出与成组读取

每次导出在输出根目录建立 `versions/<version_id>/`，完整写入并校验后，以一次原子替换提交文本 JSON 指针 `CURRENT`。任一输出写入失败不发布新版本。保留四份 JSONL：

- `results.jsonl`：M01 原字段 doi、title、source_url、chemicals、conclusions、methods、extraction_method、source_snippets、status，不额外加字段。
- `warnings_by_severity.jsonl`：paper_id、行号、结果摘要、status、informational、blocking；与主结果一行对应。
- `failures.jsonl`：failed / skipped 队列及安全错误历史，与 ResultStatus 分开。
- `review.jsonl`：部分结果或带告警的待人工复核记录，包括带提示性告警的 success。

分级文件只覆盖有抽取结果的论文；skipped 只在 failures 和报告中出现，不进入主结果或分级文件。

**消费方禁止直接 open 当前结果文件。成组读取共用快照：**

```python
from pathlib import Path
from exports import (open_current_snapshot, read_current_results,
    read_current_warnings_by_severity, read_current_failures,
    is_warning_classification_error, FailureStatus, prune_versions)

out = Path('work/demo/results')
with open_current_snapshot(out) as snapshot:
    print(snapshot.version_id, snapshot.published_at)
    records = read_current_results(out, snapshot=snapshot)
    warnings = read_current_warnings_by_severity(out, snapshot=snapshot)
    failures = read_current_failures(out, snapshot=snapshot)
    internal_errors = [r for r in failures if is_warning_classification_error(r)]
    skipped = [r for r in failures if r.status == FailureStatus.SKIPPED]

# 手动维护，不在发布路径自动删除；保留最近三代、当前和活跃快照
prune_versions(out, keep=3)
```

snapshot=None 时，读取函数内部进入一次快照上下文，完整读取后返回。**两次 snapshot=None 调用跨发布可能读到不同版本。** snapshot.destination 与请求 Path 不同会抛 ValueError，消息含两路径；相对/绝对路径保持同一写法。快照上下文关闭后不可继续使用。

活跃租约可能让保留数暂时超过三代；读进程异常退出可能留下 `.leases/` 租约，确认进程结束后再人工清理。旧平铺 JSONL 属历史文件，不是 CURRENT 指定的当前输出；`read_frozen_results` 只供明确冻结的历史夹具使用。

错误事件 append-only；不能把 failures 行数当失败论文数，历史失败不等于当前失败。只有体积超限记 skipped，其他下载错误仍 failed。`.skips.json` 旁文件保存字节数来源，随数据库保留。分类遗漏/矛盾由统一 predicate 识别，属于内部程序错误，不是论文内容质量失败。

## 状态、原文和抽取范围

告警清单见 `docs/diagnosis/WARNINGS_INVENTORY.md`。informational 保留但不阻断 success；blocking 必须对应实际缺失/失效字段。三字段有有效证据且无 blocking 才是 success。未知或矛盾分类只令该篇 failed，批次继续。

多栏告警目前为 informational。**success 仅表示证据结构完整，不保证内容顺序或科学含义正确。** 阅读视图按栏排序，caption、页边内容、参考文献、致谢和后置声明排除；raw_blocks 保持原文、顺序和稳定偏移。跨页段落用两条逐页 snippet，禁止伪造跨页 raw_block。

方法章节优先，取不超过上限的连续完整原文块；`methods_primary_bounded` 表示覆盖有界，不能当完整方法。无方法章节才走原回退：同 section、连续至少两块、每块至少两个方法关键词、不超过长度上限。完整性错误整条拒绝；合法但超长的 methods 字段降级清空，其余有效字段保留。

生产路径禁止关闭证据校验。enable_length_check 是策略降级开关，生产强制开启；测试关闭只用于比较超长字段是否保留。关闭切片/证据检查属于接受错误证据的破坏性测试。CLI、pipeline、demo 不暴露这些开关。

Stage 使用 M01 现有枚举，包含 STORAGE、EXPORT；不借用 VALIDATE 表示存储或导出。tasks 仍为方案 B：每个 `(paper_id, stage)` 一条当前记录；开始尝试增加 attempts，完成更新状态；stage_runs 只追加。M01 原说明保留于 `docs/M01_CONTRACTS.md`。

## 复验

源码包根目录：

```bash
python scripts/verify_all.py
python scripts/verify_resume.py
python acceptance/m20_end_to_end.py
# 可选网站逻辑/API复验，Node 20.11+
node scripts/verify_web_assets.mjs website
```

本轮：20份模块脚本＋2份修复脚本，160个活动场景通过；3项开关检查和2项真实强制终止恢复断言另计。网站有10项JS逻辑/API检查。历史单块回退正例保留并明确SKIP，不计通过。

真实语料清单为 `docs/audit/real_manifest.json`；复跑后审计：

```bash
paperlens run --manifest docs/audit/real_manifest.json --online --db work/eval/state.sqlite3 --workdir work/eval/cache --output work/eval/results
python scripts/audit_leakage.py --output work/eval/results --cache work/eval/cache --report work/eval/LEAKAGE.md
python scripts/audit_leakage_selfcheck.py --output samples/audit_positive --cache work/eval/cache
```

独立自检使用明确包含已知泄漏的历史阳性夹具，而非已修复的干净结果。ground truth 只在 `scripts/audit_ground_truth.json`，不进生产或主验收。自检退出0=检出；1=有效证据下未检出或标注无效；2=`SKIP: cache unavailable`，表示缺缓存/哈希不匹配等前置条件不足，不是逻辑通过或失败。

## 当前实测与已知缺口

最终同批10篇：**4 success / 5 partial / 0 failed / 1 skipped**，内部分类错误0。methods长度200–3000为6/10。3篇审计全可判定、6篇有unresolved、1篇不适用；199片段已判定、22片段未判定，已判定范围未发现泄漏，不能扩展到未判定范围。

化学物20项经过助理上下文审阅，非独立人工金标准；没有recall评估，不声明生产精度。晶面/缩写门控可能降低recall，价态规则不是完整化学本体；不支持任意非整数式、复杂配位和化学结构图。方法可能只覆盖一个子节，结论可能含断句；多栏、表格、补充材料和扫描件仍有限制。

受管环境缺少可调用的浏览器交互工具，本轮未做浏览器点击/响应式视觉验收；已验证实际HTTP流程、JS逻辑与部署。浏览器快速预筛及CDN可用性不属于Python准确率报告。arXiv在线服务可能限流或暂不可用。

仅支持单个协调写入进程；批次结果汇总在内存，大规模语料、多进程写入、OCR、真实NER/LLM和parser_summary调试字段不在交付范围。

退出码：CLI 0全部成功；3含partial/failed/skipped；1运行错误；2参数错误；130用户中断。审计自检退出码另见上文。

交付清单和实际复验记录见 `docs/DELIVERY.md`。本轮交付结束，进一步质量提升另立项目评估技术路线。

<details>
<summary>历史 0.1.2 核心接口与验收说明</summary>

# MatterLens 0.1.2 — 材料科学文献筛选工具

**半自动工具，需人工复核，不保证完整性。科研抽取质量未达生产标准。**

检索 arXiv、选择论文或上传本地 PDF，抽取 chemicals / conclusions / methods 和可回溯的原文片段。Python 流水线支持批处理、失败隔离、SQLite 状态、断点续跑及 JSONL。第一阶段只有 arXiv，NER / LLM 保持模拟，不需要密钥。

网站：https://matterlens-research-6af992.takheichen59.chatgpt.site （保留拥有者私有访问）。

## 安装与打开网页

Python 3.11+，建议虚拟环境。下载 wheel 后：

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install paper_extraction_contracts-0.1.2-py3-none-any.whl
paperlens-web --online
```

自动打开 `http://127.0.0.1:8765`。该本地网页直接使用已验收的 Python 流水线，可在线处理所选 arXiv 论文或上传 PDF。不要将服务暴露到公网；默认仅监听 127.0.0.1。文件和数据库保存在当前目录的 `work/paperlens-web`，恢复处理时保留该目录。

不加 `--online` 时可离线上传 PDF；在线检索和在线下载默认禁用。端口、工作目录、体积/长度限制可通过 `paperlens-web --help` 查看。托管网站提供 arXiv 检索、真实回归结果浏览及浏览器快速预筛，**不在托管端运行 PyMuPDF**。浏览器预筛使用 PDF.js，不等同于本次评估的 Python 引擎；要使用同一套验收流水线，请启动本地网页。仅加载阅读器时访问 CDN，上传文件不发送到托管站点。

从源码安装：解压源码 zip，进入包含 pyproject.toml 的目录，执行 `python -m pip install -e .`。首次安装可能访问包索引；安装后本地 PDF 与验收不需联网。`requirements-tested.txt` 记录原验证环境直接依赖。

## CLI 最小运行

```bash
# 三篇合成材料 PDF，离线运行
paperlens run --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results

# 关键词检索与在线 arXiv 单篇处理
paperlens search "solid state electrolytes" --max-results 5 --online
paperlens run --arxiv-id 2501.00589v2 --online --db work/real/state.sqlite3 --workdir work/real/cache --output work/real/results

# 同参数恢复；只重试失败论文；独立导出
paperlens resume --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results
paperlens retry-failed --manifest examples/demo_manifest.json --db work/demo/state.sqlite3 --workdir work/demo/cache --output work/demo/results
paperlens export --db work/demo/state.sqlite3 --output work/demo/results
```

批量本地清单格式见 `examples/demo_manifest.json`，pdf 相对清单所在目录解析；离线条目必须有 PaperMeta 与本地 PDF。仅使用真实 arXiv ID，不将任意本地文件伪装为其他来源。示例 PDF 是合成测试材料，不能当科研证据。

默认 PDF 上限 **100 MiB**，methods 上限 **3000 字符**。配置见 `examples/limits.toml`；CLI 显式值优先：

```bash
paperlens run --manifest examples/demo_manifest.json --config examples/limits.toml --max-pdf-mib 100 --methods-max-chars 3000 --db work/config/state.sqlite3 --workdir work/config/cache --output work/config/results
```

## 输出与成组读取

每次导出在输出根目录建立 `versions/<version_id>/`，完整写入并校验后，以一次原子替换提交文本 JSON 指针 `CURRENT`。任一输出写入失败不发布新版本。保留四份 JSONL：

- `results.jsonl`：M01 原字段 doi、title、source_url、chemicals、conclusions、methods、extraction_method、source_snippets、status，不额外加字段。
- `warnings_by_severity.jsonl`：paper_id、行号、结果摘要、status、informational、blocking；与主结果一行对应。
- `failures.jsonl`：failed / skipped 队列及安全错误历史，与 ResultStatus 分开。
- `review.jsonl`：部分结果或带告警的待人工复核记录，包括带提示性告警的 success。

分级文件只覆盖有抽取结果的论文；skipped 只在 failures 和报告中出现，不进入主结果或分级文件。

**消费方禁止直接 open 当前结果文件。成组读取共用快照：**

```python
from pathlib import Path
from exports import (open_current_snapshot, read_current_results,
    read_current_warnings_by_severity, read_current_failures,
    is_warning_classification_error, FailureStatus, prune_versions)

out = Path('work/demo/results')
with open_current_snapshot(out) as snapshot:
    print(snapshot.version_id, snapshot.published_at)
    records = read_current_results(out, snapshot=snapshot)
    warnings = read_current_warnings_by_severity(out, snapshot=snapshot)
    failures = read_current_failures(out, snapshot=snapshot)
    internal_errors = [r for r in failures if is_warning_classification_error(r)]
    skipped = [r for r in failures if r.status == FailureStatus.SKIPPED]

# 手动维护，不在发布路径自动删除；保留最近三代、当前和活跃快照
prune_versions(out, keep=3)
```

snapshot=None 时，读取函数内部进入一次快照上下文，完整读取后返回。**两次 snapshot=None 调用跨发布可能读到不同版本。** snapshot.destination 与请求 Path 不同会抛 ValueError，消息含两路径；相对/绝对路径保持同一写法。快照上下文关闭后不可继续使用。

活跃租约可能让保留数暂时超过三代；读进程异常退出可能留下 `.leases/` 租约，确认进程结束后再人工清理。旧平铺 JSONL 属历史文件，不是 CURRENT 指定的当前输出；`read_frozen_results` 只供明确冻结的历史夹具使用。

错误事件 append-only；不能把 failures 行数当失败论文数，历史失败不等于当前失败。只有体积超限记 skipped，其他下载错误仍 failed。`.skips.json` 旁文件保存字节数来源，随数据库保留。分类遗漏/矛盾由统一 predicate 识别，属于内部程序错误，不是论文内容质量失败。

## 状态、原文和抽取范围

告警清单见 `docs/diagnosis/WARNINGS_INVENTORY.md`。informational 保留但不阻断 success；blocking 必须对应实际缺失/失效字段。三字段有有效证据且无 blocking 才是 success。未知或矛盾分类只令该篇 failed，批次继续。

多栏告警目前为 informational。**success 仅表示证据结构完整，不保证内容顺序或科学含义正确。** 阅读视图按栏排序，caption、页边内容、参考文献、致谢和后置声明排除；raw_blocks 保持原文、顺序和稳定偏移。跨页段落用两条逐页 snippet，禁止伪造跨页 raw_block。

方法章节优先，取不超过上限的连续完整原文块；`methods_primary_bounded` 表示覆盖有界，不能当完整方法。无方法章节才走原回退：同 section、连续至少两块、每块至少两个方法关键词、不超过长度上限。完整性错误整条拒绝；合法但超长的 methods 字段降级清空，其余有效字段保留。

生产路径禁止关闭证据校验。enable_length_check 是策略降级开关，生产强制开启；测试关闭只用于比较超长字段是否保留。关闭切片/证据检查属于接受错误证据的破坏性测试。CLI、pipeline、demo 不暴露这些开关。

Stage 使用 M01 现有枚举，包含 STORAGE、EXPORT；不借用 VALIDATE 表示存储或导出。tasks 仍为方案 B：每个 `(paper_id, stage)` 一条当前记录；开始尝试增加 attempts，完成更新状态；stage_runs 只追加。M01 原说明保留于 `docs/M01_CONTRACTS.md`。

## 复验

源码包根目录：

```bash
python scripts/verify_all.py
python scripts/verify_resume.py
python acceptance/m20_end_to_end.py
# 可选网站逻辑/API复验，Node 20.11+
node scripts/verify_web_assets.mjs website
```

本轮：20份模块脚本＋2份修复脚本，160个活动场景通过；3项开关检查和2项真实强制终止恢复断言另计。网站有10项JS逻辑/API检查。历史单块回退正例保留并明确SKIP，不计通过。

真实语料清单为 `docs/audit/real_manifest.json`；复跑后审计：

```bash
paperlens run --manifest docs/audit/real_manifest.json --online --db work/eval/state.sqlite3 --workdir work/eval/cache --output work/eval/results
python scripts/audit_leakage.py --output work/eval/results --cache work/eval/cache --report work/eval/LEAKAGE.md
python scripts/audit_leakage_selfcheck.py --output samples/audit_positive --cache work/eval/cache
```

独立自检使用明确包含已知泄漏的历史阳性夹具，而非已修复的干净结果。ground truth 只在 `scripts/audit_ground_truth.json`，不进生产或主验收。自检退出0=检出；1=有效证据下未检出或标注无效；2=`SKIP: cache unavailable`，表示缺缓存/哈希不匹配等前置条件不足，不是逻辑通过或失败。

## 当前实测与已知缺口

最终同批10篇：**4 success / 5 partial / 0 failed / 1 skipped**，内部分类错误0。methods长度200–3000为6/10。3篇审计全可判定、6篇有unresolved、1篇不适用；199片段已判定、22片段未判定，已判定范围未发现泄漏，不能扩展到未判定范围。

化学物20项经过助理上下文审阅，非独立人工金标准；没有recall评估，不声明生产精度。晶面/缩写门控可能降低recall，价态规则不是完整化学本体；不支持任意非整数式、复杂配位和化学结构图。方法可能只覆盖一个子节，结论可能含断句；多栏、表格、补充材料和扫描件仍有限制。

受管环境缺少可调用的浏览器交互工具，本轮未做浏览器点击/响应式视觉验收；已验证实际HTTP流程、JS逻辑与部署。浏览器快速预筛及CDN可用性不属于Python准确率报告。arXiv在线服务可能限流或暂不可用。

仅支持单个协调写入进程；批次结果汇总在内存，大规模语料、多进程写入、OCR、真实NER/LLM和parser_summary调试字段不在交付范围。

退出码：CLI 0全部成功；3含partial/failed/skipped；1运行错误；2参数错误；130用户中断。审计自检退出码另见上文。

交付清单和实际复验记录见 `docs/DELIVERY.md`。本轮交付结束，进一步质量提升另立项目评估技术路线。

</details>
