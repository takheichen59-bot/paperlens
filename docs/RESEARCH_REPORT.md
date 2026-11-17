# MatterLens 0.2.0 实际复验与已知缺口

真实语料：同一批20篇CC许可材料科学arXiv论文，352页；全部生成结构化记录，处理失败0。PDF合计87,246,820字节。

字段非空：材料18/20、方法10/20（全部200–3000字符）、结论15/20、发现17/20；算法13/20、公式候选19/20、数值候选19/20。证据956条，按原始块字符切片和页码验证。无人为把空字段填成“成功”，所有20篇初始待人工复核。

## 已实际执行

```text
ALL MODULES: PASS (20 module scripts; 2 repair scripts; 160 active checks; historical skips excluded)
SCIENCE SUMMARY: 5 passed, 0 failed
INTELLIGENCE SUMMARY: 5 passed, 0 failed
BATCH SUMMARY: 5 passed, 0 failed
PHASE 1 WEB: 19 passed, 0 failed
RESEARCH WEB: 16 passed, 0 failed
SCALE DETAIL: 5000 synthetic tasks; killed=-9; resumed=23; processed=4977; failed=0
```

新批处理真实SIGKILL测试不是模拟异常：终止子进程后，从落盘的完整检查点恢复。5000条是合成工程任务，不能解释为5000篇真实PDF已处理。

真实20篇CLI完整运行返回submitted=20、processed=20、failed=0；同版本与哈希的恢复运行返回processed=0、resumed=20、failed=0。改变解析/抽取版本会使检查点失效，这是预期行为。

旧泄漏自检实际输出：`SKIP: cache unavailable`，退出码2。环境缺少对应旧缓存，不能当作逻辑自检通过。新全字段位置审计：2篇标签归属可判定，18篇含未知归属，414条unresolved；已标为排除区域的片段0。不能宣称全字段零泄漏。

## 重要限制

1. 没有独立人工标注的准确率评价。缺失方法等字段必须人工补充，质量未达生产标准。
2. 原文切片正确只证明出处，不证明其科学含义、完整性、阅读顺序或所属字段正确。
3. 未知章节、PDF图表、多栏、上下标和特殊符号仍影响提取；公式和数值仅候选，未经单位/条件归一化。
4. 固定20篇是Python基线；网页新增论文使用PDF.js基线，两者不承诺一致。
5. 检索为哈希向量和词项匹配，关系为正文提及，没有自由生成答案、真实NER或LLM。
6. 没有验证5000篇真实论文的下载/解析资源消耗；不提供分布式集群、OCR、全文语义理解或全学科全来源覆盖。
7. 浏览器控制工具不可用，未做点击、布局及辅助技术验收。逻辑/API/导出、线上HTTP与实际下载校验单独记录，不能冒充浏览器验收。
8. 当前单所有者私有工作区；PDF文件与科研准确性需按许可、原文和领域知识复核。

contracts/和storage/共12个受保护文件已与已验收0.1.2源码逐字节核对，全部相同。新增research包与paperlens-research命令；旧CLI签名不变。

本轮停止在此交付，不把质量限制用新增功能掩盖。后续若另立提升项目，优先独立标注20篇、方法定位与未知章节处理，再评估专用模型路线。

## 已部署网站实际复验

```text
PASS production corpus: 20 records, 956 raw-slice/page/field evidence checks
PASS production complete ZIP: 20 PDFs + scientific Excel/CSV/JSONL + review/failures + all hashes
PASS production official arXiv search: 20 records
PASS production docs, source ZIP, wheel and download checksum manifest
```

完整资料包：90,322,176 字节，SHA256 `88df5a408cbe08c20dd9870e9e9127f080aa01a22effd18bed189e66fc3688d5`。包内20份PDF的SHA256全部与原始索引一致；20条research.jsonl记录均通过字符切片与字段证据检查，Excel包含21行（表头+20篇），所有OOXML可解析。failures.jsonl为空，review.jsonl为20条待人工复核记录。

正式网址：https://matterlens-research-6af992.takheichen59.chatgpt.site

线上实际下载证明文件可获取、结构一致；它不能证明科研字段准确率或代替浏览器交互验收。
