# P0/P1 修复与同批真实语料重跑

实际输出：`{"submitted": 10, "duplicates": 0, "success": 0, "partial": 8, "failed": 1, "skipped": 1, "exported": 9, "results": "work/fixes/real-final/results/results.jsonl"}`。退出码 3；85.22 秒；全新数据库、全新缓存。

methods 长度200–3000：2/10 → 3/10。新名单：arxiv:2501.00589, arxiv:2501.00679, arxiv:2501.00680。这仅是长度指标，不代表可用方法数。

基线8个参考文献实体+3个基金编号：发布结果残留 0；对9篇解析产物在M14拒绝前的chemical候选复核，残留 0。因此不是仅靠清空failed结果得到0。

172 条发布证据与原始raw_blocks切片、页码、视图范围核对一致；9篇缓存均具有匹配PDF哈希和解析版本的SectionView。

## 原8个partial逐篇对照

| arXiv | 修复前问题类别 | 修复后 | methods字符前→后 | conclusions字符前→后 | 根因 |
|---|---|---|---:|---:|---|
| 2501.00534 | 长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | partial | 6152→0 | 3684→3684 | M12连续候选超限，清空methods；保留其他有证据字段，仍partial |
| 2501.00561 | 视图泄漏；长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | failed | 14513→0 | 2762→0 | M14拒绝超长methods候选（8229字）；整条结果failed，未保留其他候选字段 |
| 2501.00564 | 视图泄漏；长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | partial | 6570→0 | 1980→1715 | M12正文/双块/关键词/同section条件不满足，拒绝方法回退；仍有字段缺失或告警 |
| 2501.00589 | 视图泄漏；长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | partial | 42376→925 | 467→11036 | 章节/边界改善；仍有版面告警，保持partial；非科学语义验收通过 |
| 2501.00591 | 视图泄漏；字段缺失；长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | partial | 16238→0 | 0→0 | M12连续候选超限，清空methods；保留其他有证据字段，仍partial |
| 2501.00620 | 字段缺失；其他：原质量告警/版面问题 | partial | 2018→0 | 0→2046 | M12正文/双块/关键词/同section条件不满足，拒绝方法回退；仍有字段缺失或告警 |
| 2501.00679 | 长度超限（按本轮上限复核）；其他：原质量告警/版面问题 | partial | 5306→815 | 166→5205 | 章节/边界改善；仍有版面告警，保持partial；非科学语义验收通过 |
| 2501.00680 | 视图泄漏；其他：原质量告警/版面问题 | partial | 2491→1330 | 789→405 | 章节/边界改善；仍有版面告警，保持partial；非科学语义验收通过 |

## 两篇原下载失败论文

- `arxiv:2501.01468`：{"paper_id": "arxiv:2501.01468", "status": "skipped", "file_bytes": 129565883, "file_bytes_source": "content_length", "limit_bytes": 104857600, "bytes_received": 0, "skipped_reason": "size_limit"}
- `arxiv:2501.00600`：{"paper_id": "arxiv:2501.00600", "status": "partial", "download_status": "success", "file_bytes": 40474244, "file_bytes_source": "filesystem_after_full_download", "skipped_reason": null}

## 字段级改进和仍未解决的问题

- 2501.00680：识别 Calculation details，methods 2491→1330；conclusions 789→405，排除致谢。仍有首页版面告警，状态保持partial。
- 2501.00679：识别 METHOD、SUMMARY AND OUTLOOK，methods 5306→815；不是把原5306截取前3000字符。结论166→5205，仍需检查完整性。
- 2501.00589：methods 42376→925，但925字符含FIG.6图注；conclusions 467→11036并混入方法。长度通过不能称为抽取有用，多栏阅读顺序仍未解决。
- 2501.00561：识别实验章节后methods候选8229字，M14按3000上限拒绝整条结果，因此partial→failed；不能把化学物清空误报成实体质量提高。
- 2501.00620：原2018字单块/零散回退不满足新规则，methods清空；这是保护性收紧造成的覆盖下降。
- 2501.00591：基金编号和文献化学物被排除，但HK0/HK1仍是误报，正文曾出现的NbS2也不再输出。尚未评估recall。

没有success增长，不能宣称完成真实质量验收。当前修复证明边界、长度和状态政策执行；不证明科研字段整体正确。

## 验收与实现边界

- 20份模块脚本125个活动场景通过；历史单块正例保留并SKIP，不计通过；3项配置开关验证另计。
- contracts、schema.sql、0001_init.sql哈希保持不变；没有新模型、密钥或表结构。
- SectionView不进入ParsedPaper、不挂私有属性、不使用全局字典；缺失/错PDF哈希/错版本的缓存均重解析。
- M18行schema扩展：FailureStatus与ResultStatus分离，parse_failure_line统一解析failed/skipped；字节数超限使用专用异常，不吸收非体积错误。
- 单栏居中页码的双列误报已修；不同高度行不得配对，仍保留其他可疑版面告警。

复验：`python scripts/verify_all.py`、`python scripts/verify_m14_checks.py`；实际逐项输出见本目录00–06与REGRESSION.txt。
重建此报告：`python scripts/report_p0p1.py`，需保留work/fixes/real-final的数据库和缓存。
