# 实测结果与验证边界

本次上传前复验：2026-11-17，Linux/Python3.12。原始日志在 [logs/github](../logs/github/)。测试分别计数，不合并成“科研能力全部通过”。

## 本次重新执行

| 项目 | 实际结果 | 日志 |
|---|---|---|
| M01–M20 +2个修复脚本 |160项通过；另有3个M14变异检查和2个恢复检查通过 |source-legacy-tests.log |
| 新平台6个测试文件 |30项通过，0失败 |source-platform-tests.log |
| 库历史、失效、条目隔离、快照修复 |5项通过 |source-master-a.log |
| research_science +research_intelligence |各5项通过 |source-research.log |
| Worker/网页逻辑与API |19+16+5项通过 |source-website-tests.log |
| 新队列真实进程终止/恢复 |12篇合成工程样本，SIGKILL后已落盘项未重复处理 |recovery.log；docs/master/RECOVERY.json |
| 独立wheel安装 |0.3.0从site-packages导入，静态资源/元数据API/筛选/导出通过 |isolated-install.log |
| 上传前源码扫描 |未发现所检查的常见密钥格式及实际.env/数据库文件 |secret-scan.json |

测试含故障注入、真实sqlite/子进程、真实PyMuPDF及Tesseract；外部HTTP/R2部分采用fixture/mock。这些不等价于真实外部服务通过。原文件哈希对比确认冻结的contracts/storage共12个文件不变。

独立安装使用本次构建的wheel（189,923字节），SHA-256：

`56e124e2e46ad3c2f73d5f5ef84ec081b888a930c9acbc658ac0406dda72bc74`

测试通过不代表任意未来依赖版本均兼容；运行依赖版本见`logs/github/installed-dependencies.txt`。

## 前一工作会话的真实网络/语料结果（2026-11-16）

不是本次重新发起的在线请求；保留原始回执供复核。

- Crossref20条、OpenAlex20条，合计40条/去重后40条真实元数据：`docs/master/LIVE_DISCOVERY.json`。
- SemanticScholar真实请求限流HTTP429；Springer/Elsevier缺授权，NOT EXECUTED。
- 官方主机白名单代理模式下载arXiv2501.00534v2：3,702,933字节、5页、SHA256回执：`docs/master/LIVE_ACQUISITION.json`。
- 通用IP固定公网下载在该环境失败，没有用另一模式的成功掩盖它。
- 10篇真实PDF新解析器解析成功：`docs/master/REAL_PARSING.json`。未独立验证多页表格、算法框覆盖完整。
- 既有20篇真实材料论文导入/解析完成，0失败；深度提取均NOT_EXECUTED：`logs/github/master-import.log`。
- 旧版5000条合成任务的工程恢复已执行；不等于5000篇真实论文的质量/吞吐测试。

原始PDF缓存、个人数据和凭据不随GitHub上传。重跑真实测试需合法取得相应PDF、来源服务与授权。

## 没有执行 / 不可宣称完成

真实LLM、真实嵌入、真实生成式科研问答、出版商授权、GROBID/Docling联测、人工金标准、真实浏览器交互/截图、Windows运行、5000篇真实语料、生产部署及托管R2修复线上验证。

## 复验命令

```bash
python -m pip install -e '.[platform,test]'
python scripts/verify_all.py
python -m unittest discover -s tests/master -v
python acceptance/master_a_integrity.py
python acceptance/research_science.py
python acceptance/research_intelligence.py
python scripts/master_recovery.py
python scripts/check_repository_secrets.py
cd website
node verify-site.mjs
node verify-research.mjs
node verify-master-a.mjs
```

OCR用例要求`tesseract`英文数据。GitHub Actions工作流已编写，但在未上传/未实际运行之前不计为远端CI通过。`scripts/verify_install.py`是历史0.1.2脚本；新版使用 `scripts/check_installed_platform.py --python /path/to/isolated/python`。

## GitHub上传后的远端复验

2026-11-17：[GitHub Actions #44029712362](https://github.com/takheichen59-bot/paperlens/actions/runs/44029712362)完成，conclusion=success；python(3.11)、python(3.12)、worker三个job均通过。被测源码提交为`6a6def9641591923913e8963172176e5d68d369b`，其后的提交仅记录交付文档。此CI仅验证离线工程行为，不补足本文列出的真实模型、人工金标准、浏览器和授权来源等验证。
