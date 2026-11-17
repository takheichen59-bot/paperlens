# Phase 1 实际获取报告

主题：材料科学综合。来源：arXiv 官方 API + 官方摘要页许可 + 官方 PDF。

实际文件：20 篇 / 352 页 / 87,246,820 字节。20 个唯一来源 ID、20 个唯一 PDF SHA256。

| arXiv ID | 页数 | 字节数 | 可读文本字符数 | 许可 |
|---|---:|---:|---:|---|
| 2501.00680v1 | 11 | 6027220 | 23070 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00591v1 | 7 | 8110924 | 32692 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00589v2 | 13 | 2683474 | 57337 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00561v1 | 9 | 4348948 | 39062 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00534v2 | 5 | 3702933 | 21275 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00453v3 | 15 | 12204200 | 62594 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00447v1 | 9 | 836130 | 29497 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00423v1 | 16 | 974554 | 25225 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.03254v1 | 34 | 2525102 | 44073 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00132v1 | 13 | 3459720 | 23939 | https://creativecommons.org/licenses/by/4.0/ |
| 2501.00091v3 | 29 | 3808912 | 91997 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.21119v2 | 14 | 18606100 | 56835 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20938v2 | 8 | 681390 | 39254 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20865v1 | 12 | 2190803 | 52436 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20653v1 | 20 | 1005604 | 34485 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20552v1 | 14 | 1592442 | 31026 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20531v2 | 18 | 4005122 | 61723 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20497v1 | 54 | 2938806 | 75225 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20448v1 | 16 | 1077073 | 38898 | https://creativecommons.org/licenses/by/4.0/ |
| 2412.20394v1 | 35 | 6467363 | 43619 | https://creativecommons.org/licenses/by/4.0/ |

逐篇校验全部页面可访问、文本≥200字符、首屏可渲染、页数/字节数/哈希与索引一致。

实际验收：`PHASE 1 SUMMARY: 5 passed, 0 failed`；网页逻辑/API：`PHASE 1 WEB: 19 passed, 0 failed`。

范围：仅证明文献获取与文件可用性；未执行科研字段准确率验收。没有修改 contracts/ 或数据库表结构。

## 网站实际下载核验

服务端存储：20 / 20 个文件存在。线上官方搜索 HTTP 200，返回20条真实记录。

从已部署网站实际下载 PDF ZIP 后：20份PDF、所有ZIP CRC及逐份SHA256相等。

- ZIP字节数：87,338,027
- ZIP SHA256：`f75ee99873174a945b93b5ccfdde1de40eb09ee78255f6fe2f7e0831dbf008b2`
- PDF原件合计字节数：87,246,820（与ZIP大小不同，ZIP还包含索引和说明）

网页入口、脚本、随站点提供的PDF阅读器、Excel、源码ZIP和说明文档均由线上HTTP实际读取并返回200。源码ZIP已在独立临时目录解压，19项网页逻辑/API测试及Worker构建均通过。当前环境缺少Sites指定的浏览器控制工具，因此没有声称完成浏览器点击或布局验收。

## 实际验收输出摘要

```text
PASS 20 unique papers, DOI deduplication and 20 unique PDF hashes
PASS Official source URLs and explicit redistributable CC licenses
PASS All 20 PDFs: bytes, SHA256, every page, readable text and rendering
PASS All records trace to the exact official materials-science search feed
PASS Resume performs zero network requests and does not rewrite completed PDFs
PHASE 1 SUMMARY: 5 passed, 0 failed
PHASE 1 WEB: 19 passed, 0 failed (logic/API/archive generation; browser interaction not tested)
PASS production ZIP: 20 PDFs, all CRCs and SHA256 hashes match
PASS production official live search: 20 results
```
