# 检索故障维修与验收（2026-11-19）

## 故障与证据

正式站收到“2D”关键词请求时两次返回HTTP502，分别等待约25秒和12.7秒。请求路径为/api/discovery，requestId分别为81f24b2bf0c5cf2c9d10e60388d6acb3和3e019606cd0d956df350c046a4b510e7。日志不含可证明科研内容正确的依据。

实际诊断时，OpenAlex匿名检索返回HTTP503并明确暂停匿名搜索；arXiv主来源也有瞬时失败，后续同词可恢复。原实现只有这两条来源、缺少精确请求缓存；检索尚无论文时的失败批次没有重新检索按钮，用户只能重开批次。

## 修复

新增DataCite arXiv登记元数据后备，并从已知DOI的真实API响应核实客户端为arxiv.content。只接受匹配的arXiv DOI、客户端和官方原文ID，不把其他出版商或固定示例当作检索结果。原文继续从arXiv取得。短暂HTTP失败有限重试，超时直接后备；尊重Retry-After，区分HTML错误页/损坏Atom与合法零结果。

成功检索存独立discovery/v1精确请求缓存，15分钟内复用，7天内旧结果只在全部实时来源失败后展示，标记历史及取得时间。缓存和来源信息进入界面、批次、PDF、Excel及ZIP。失败的空批次可在同一检查点重新检索。静态界面脚本不长期缓存，减少发布后模块混用。

实测还发现DOM超时异常的数字code=23会遮蔽错误类型，导致多一次主源等待；已修为按字符串错误码和异常类型判断，并增加回归。

## 工程验收

- 新增故障恢复检查15项通过，含限流/Retry-After、DataCite重试、超时、主源坏格式、全部来源失败、精确缓存/旧缓存/过期缓存、ID/语法边界及取消。
- 原网页19项、工作区10项、批次15项、阅读8项、PDF专门10项、导出一致性7项和构建通过。
- Chromium托管界面23项通过，原流程12项通过；含缓存时间标记、零论文失败批次重新检索、同一检查点恢复、损坏PDF隔离、所选/全部/单篇真实下载事件、PDF/Excel/JSONL/ZIP生成与刷新后下载。明确使用合成工程fixture，不作为科研准确率或正式站浏览器登录验收。
- Python/原模块及最终工程检查以[代码提交9fc233f的CI](https://github.com/takheichen59-bot/paperlens/actions/runs/44352116579)和PR #8最新状态为准；没有把历史分支测试数量相加。中间9113b59的旧浏览器导航失败及本轮修复明确保留，不以先前绿灯掩盖。
- 最终待提交源码审计结果见source-audit.json，无凭据发现；不提交真实论文全文、作者联系信息或完整科研JSONL到公开GitHub。

## 正式站实际检索

初始检索修复于同一所有者私有站点第8版实测；完整维修现已发布第9版，来源提交14c86045c6d1ed37dfe6321b4959af0e51b03f51。真实请求回执见 [search-probes.json](search-probes.json)：

- 2D / 20条：HTTP200，真实arXiv元数据；重复请求从新保存的同词缓存返回，实测约445毫秒，带取得时间。
- two-dimensional magnetic materials / 5条：主arXiv超时后，DataCite实际返回5条，正式站真实后备成功，未注入模拟结果。
- graphene / 5条与2501.00680v1精确ID均HTTP200。精确ID读取预先核对版本，回执明确PINNED来源，不冒充关键词实时检索。

## 真实全文批次

针对2D启动20篇正式私有站点批次，首次19篇完成、1篇因材料片段校验失败；同批次只重试失败篇后20篇全部处理完成，20份原PDF真实下载并按SHA256逐份校验。原19条已完成JSONL记录逐字保持一致。最终PDF为43页、21个目录书签，文字可选择，U+02DC保留，未发现单词越过纸张边界；Excel含10个工作表及20条汇总，JSONL有20条记录，证据CSV与原文一起放入完整ZIP，CRC及各文件哈希均通过。1386条核心来源片段与原始块字符切片相等。完整计数、版本分布和文件哈希见[production-batch.json](production-batch.json)。该运行使用正式HTTP/R2和相同PDF.js/通用提取器的Node执行路径；与上述Chromium合成界面验收分开记录，不称为正式站浏览器登录测试。

## 数据与剩余边界

修改前备份28条唯一文献、复核和11份既有文件。没有修改冻结src/contracts、旧src/storage或SQL结构，main保持原提交092874a2899de87e646d91d0b3de1bb8a5b39f77，原17113833cb76595123e012551c58de95bfa053e3仍为祖先。新功能在新分支/PR #8，发布网站与合并main是不同状态。实际批次重处理了6条已存在的自动记录，保留旧版本及本地修改前备份；人工复核未被改写，不把重新处理的自动记录称为逐字未变。

持续上游故障仍可能发生；无可用来源和匹配缓存时返回可重试错误，不保证外部网站永久可用。未配置模型、OCR、外部翻译或独立专家金标准。status/成功记录/来源切片通过不能证明科研准确。批次需保持网页开启，用户可从检查点恢复；20篇全文测试结果不能推广为所有领域或所有PDF可提取。

## 20篇全文实测暴露并继续修复

首轮取得20份原PDF，19篇提取完成，2512.14973v1因GeTe/MoTe关键词位于Fe₅GeTe₂、MoTe₂内部，旧严格归属校验无独立提及而中止。browser-context-roles-v1.2保留这类原始片段候选、原句和偏移，明确标记partial_token及归属未确认，禁止提升为本文样品；提取器升级browser-scientific-rules-v1.6。不是删除误报来掩盖问题。

首轮Excel/JSONL/证据CSV及20原文ZIP已可下载；PDF因字体缺U+02DC明确失败，没有冒充已生成。字体第2版补齐源NotoSans尚缺的1483个字形，保持原Unicode文字不变，并用新哈希及浏览器字体版本URL。包含全部20篇的本地PDF重新生成验证。之后只重试失败篇，保留19条已完成检查点；正式重试与完整文件校验结果见production-batch.json。

## 页面异步竞态补修

完整CI在原FastAPI界面快速从算法浏览器切换到跨论文比较时发现 `Cannot set properties of null (setting innerHTML)`。旧守卫只在HTTP响应头到达后检查路由，JSON正文稍后解析时旧页面可能继续写入已销毁节点。修为正文解析后再检查路由，失效页面的错误也不覆盖新页面。Chromium工程测试延迟一次真实API响应正文，再切换页面并释放正文，确认跨论文比较仍保留；不替换真实API响应数据。这份旧本地界面不属于托管站点入口，因此未重新发布无关网站版本。

## 可直接下载的本批交付

以下均为同一所有者私有站点的正式下载，需使用站点已授权身份：

- [43页处理报告PDF](https://paperlens-research-workspace.halvedbolt3.chatgpt.site/api/batches/file?id=024c6231-f147-4e46-8512-a4e58f5ae395&name=report.pdf)
- [20篇Excel](https://paperlens-research-workspace.halvedbolt3.chatgpt.site/api/batches/file?id=024c6231-f147-4e46-8512-a4e58f5ae395&name=research.xlsx)
- [20篇JSONL](https://paperlens-research-workspace.halvedbolt3.chatgpt.site/api/batches/file?id=024c6231-f147-4e46-8512-a4e58f5ae395&name=research.jsonl)
- [完整ZIP，约128MB，含20份原文](https://paperlens-research-workspace.halvedbolt3.chatgpt.site/api/batches/bundle?id=024c6231-f147-4e46-8512-a4e58f5ae395)

处理报告不是任何一篇原始论文。所有20条记录仍为unreviewed；部分方法、发现、结论未命中，保持缺失，不因流程20/20完成而编造。全文输出只留在私有站点及被忽略的本地工作目录，公开PR只含代码和不含全文的验收回执。
