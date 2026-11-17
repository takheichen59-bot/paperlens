模块 / 状态 / 验收命令 / 已知偏差
M02 / 已验收 / python acceptance/m02_storage.py / 方案B；upsert_task 每次增加 attempts；stage_runs 只追加
M03 / 已验收 / python acceptance/m03_arxiv_metadata.py / arXiv 单来源；离线模拟 HTTP；下载入口待 M05
M04 / 已验收 / python acceptance/m04_http_policy.py / 共享限速器为适配器实例级；默认3秒；在线策略未实测
M05 / 已验收 / python acceptance/m05_pdf_download.py / 任务级重下；基础PDF标识校验；未实现字节范围续传
M06 / 已验收 / python acceptance/m06_resume.py / 复用tasks；产物为原子JSON旁文件；仅单进程恢复
M07 / 已验收 / python acceptance/m07_pdf_text.py / 基础阅读顺序；多栏仅告警；扫描件需OCR；修复1次后通过
M08 / 已验收 / python acceptance/m08_layout_cleaning.py / 保留原始块；页边界阈值固定；仅词表允许的断词拼接
M09 / 已验收 / python acceptance/m09_sections.py / 英文固定标题；相邻同类标题合并；修复1次后通过
M10 / 已验收 / python acceptance/m10_chemicals.py / 小词典+保守化学式；无化学结构识别或实体标准化
M11 / 已验收 / python acceptance/m11_ner_adapter.py / 仅MockNER；偏移错误/重叠标记复核；失败保留规则结果
M12 / 已验收 / python acceptance/m12_methods.py / 方法章节优先；原文块级回退；未实现结论抽取
M13 / 已验收 / python acceptance/m13_conclusions.py / 结论章节优先；只返回作者原文；目的句不作结论
M14 / 已验收 / python acceptance/m14_extraction_validation.py / 块级原文证据；缺字段/质量告警降为partial；不验证科学语义
M15 / 已验收 / python acceptance/m15_llm_contract.py / 仅同步模拟客户端；无真实服务；超时与证据错误降级
M16 / 已验收 / python acceptance/m16_single_pipeline.py / 单篇串联及缓存；未含批调度与JSONL文件导出
M17 / 已验收 / python acceptance/m17_batch_pipeline.py / 有界异步队列；PDF解析单进程池；结果暂存内存；取消不强杀解析进程
M18 / 已验收 / python acceptance/m18_exports.py / 每篇最新策略结果；三文件分别原子替换；失败队列含历史错误事件
M19 / 已验收 / python acceptance/m19_cli.py / CLI离线默认；在线须显式--online；0成功/3部分失败/1运行错误/2参数错误
M20 / 已验收 / python acceptance/m20_end_to_end.py / 5个合成PDF端到端离线场景；未测真实arXiv网络和真实科研准确率

抽查 / 状态 / 验证材料 / 已知偏差
M01-M02 阶段契约 / 已核实 / docs/audit/storage_contract_snapshot.json / tasks 实际为方案B；Stage.STORAGE、EXPORT 可用；补记此前漏写的阶段补丁说明，未改实现
M02 验收强度 / 已抽查 / python scripts/audit_contract_checks.py / 原脚本缺独立CHECK断言；补充PK/FK/CHECK包装实测均通过；0002回滚原测试有效
M14 验收强度 / 发现盲区 / docs/audit/mutation_checks.json / 移除同block字符切片校验后原5项仍通过；补充错偏移/错页码检查现实现通过
合成输出 / 3篇核实 / python scripts/audit_demo_trace.py / 9条切片可回溯且字段顺序正确；不能推广为真实抽取质量
真实3篇冒烟 / 已运行 / docs/audit/smoke_cli.log / 0 success、2 partial、1 failed；1篇超过默认20MiB
真实10篇批次 / 已运行 / docs/audit/ten_cli_run.json / 0 success、8 partial、2 failed；两篇40.5MB/129.6MB超过默认体积；8篇进入质量审查
M07 真实版面 / 确认缺陷 / docs/audit/multicolumn_false_positive.json / 单栏居中页码同时命中左右列条件，产生多栏误报并降级status
M09-M13 真实字段 / 未达质量验收 / docs/audit/REPORT.md / 0/8识别方法章节；罗马数字/Calculation details未覆盖；参考文献和致谢泄漏；半句与大段关键词堆积
M10-M11 实体质量 / 暂定审阅 / docs/audit/chemical_annotations.csv / 37预测：19合格、13不合格、5边界；目标precision 51.4%-64.9%；非独立专家金标准，recall未测
M14 真实原文回溯 / 267条通过 / python scripts/audit_saved_evidence.py / 切片位置正确不等于实体、句子或字段语义正确
M18 失败统计 / 发现偏差 / docs/audit/real_failures.jsonl / 下载失败同时产生extract_failed汇总行，不能按失败队列行数计算失败论文数
修复0 / 已验收 / python acceptance/m08_layout_cleaning.py / spans列表与二分回映射，7场景通过；首次命名错误修正后通过
修复1 / 已验收 / python acceptance/m09_sections.py / raw_blocks不变；REFERENCES表示不可抽取后置内容，不等于引用列表；SectionView缺失缓存重解析
修复2 / 已验收 / python acceptance/m12_methods.py / M12回退规则收紧：单块回退从正例改为拒绝；历史正例保留并显式SKIP；真实ID和字段变化待本轮冻结语料重跑逐篇记录
修复3 / 已验收 / python acceptance/m09_sections.py / 配置化标题、罗马数字单词白名单、字体/位置提示；没有标题的连续编号引用列表保守识别为排除区
修复4 / 已验收 / python acceptance/m07_pdf_text.py / 边缘窄块页码；同一行不再同时充当左右列证据；6场景通过
修复5 / 已验收 / python acceptance/m14_extraction_validation.py / 9场景通过；3个配置开关仅测试关闭；同一错误样本关闭通过/开启拒绝
修复6 / 已验收 / python acceptance/m05_pdf_download.py / 100MiB可配置；仅体积超限skipped；非体积错误仍failed；7场景通过
M18 行 schema 扩展 / 已验收 / python acceptance/m18_exports.py / 新增skipped/skipped_reason；FailureRecord与ResultStatus分离；统一parse_failure_line；6场景通过
真实复核修正 / 已验收 / M07+M09验收脚本 / 补CMBX/Nimbus-Medi粗体识别、同高度列配对；第二次全新库/缓存重跑，初次记录另存real_run_initial.json
真实同批10篇 / 已运行 / docs/fixes/real_run.json / submitted10、success0、partial8、failed1、skipped1；methods长度200–3000由2/10变3/10，仅长度指标
M12 回退规则收紧：单块回退从正例改为拒绝 / 已记录 / docs/fixes/comparison.json / 2501.00620 methods 2018→0；2501.00534 6152→0、2501.00591 16238→0（连续候选超限）；2501.00564 6570→0（回退条件不足）；不能将丢失字段计作质量提升
字段级变化 / 已记录 / docs/fixes/REPORT.md / 2501.00679 methods5306→815；2501.00680 2491→1330且致谢移除；2501.00589 42376→925但仍是图注/错序；2501.00561候选8229被M14拒绝，partial→failed
视图泄漏回归 / 已核查 / python scripts/report_p0p1.py / 基线8参考实体+3基金编号在发布结果和9篇解析候选中均残留0；不代表全体precision/recall通过
下载逐篇核查 / 已核查 / docs/fixes/comparison.json / 2501.00600完整下载40474244字节、partial、未skipped；2501.01468 Content-Length129565883字节、size_limit跳过
真实质量限制 / 尚未解决 / docs/fixes/REPORT.md / 多栏阅读顺序仍会混入图注/方法；HK0/HK1误报仍在；保守排除丢失正文NbS2可能降低recall；success保持0
A1 warnings分级与M14降级 / 已验收 / python acceptance/m14_extraction_validation.py；python scripts/verify_m14_checks.py / 13场景+3独立开关检查；分类依据WARNINGS_INVENTORY；未知或矛盾告警属内部错误，不降低证据完整性门槛
A2 原子版本导出 / 已验收 / python acceptance/m18_exports.py / 11编号场景，11a/11b独立子测试；CURRENT文本指针；共享快照；保留最近3代不自动删；活跃/遗留读取租约可能额外保留版本
A3 分类异常隔离 / 已验收 / python acceptance/m16_single_pipeline.py；python acceptance/m17_batch_pipeline.py / 各6场景；异常对象身份保持；单次分类失败仅一条FailureRecord；批次继续；历史错误不删除
M14长度开关语义 / 已记录 / python scripts/verify_m14_checks.py / enable_length_check 语义从数据完整性检查变更为策略性降级开关；生产路径强制开启；测试关闭实例仅用于验证降级路径本身
多栏告警语义 / 已记录 / docs/stage_a/REPORT.md / page_<n>_possible_multicolumn 在本版本为 informational，跨栏错序、图注混入不反映在 status 上；success 仅表示证据结构完整，不表示内容顺序正确；M09 修复前 success 论文仍需人工抽查顺序。
A4 泄漏审计 / 独立自检通过 / python scripts/audit_leakage_selfcheck.py --output work/stage_a/real/results --cache work/stage_a/real/cache / 退出码0，00589致谢续段检出1条；4篇全部片段可判定、5篇unresolved、1篇不适用；未判定原因逐篇见LEAKAGE.md，不能宣称泄漏0
A5 消费方与回归 / 已验收 / python scripts/verify_all.py --results work/stage_a/real/results / 20脚本136活动场景+3开关检查；消费方用快照辅助函数；历史冻结语料用read_frozen_results；未新增模型或依赖
内部失败分类 / 已记录 / docs/stage_a/REPORT.md / warning_classification_error导致的failed是程序内部错误（分类遗漏/矛盾），不是论文内容问题；本次0篇；若出现标记“待下一轮排查的分类遗漏”，不混入内容质量统计
A真实同批10篇 / 已运行，停在P1 / docs/stage_a/real_run.json / 新库新缓存在线重跑80.88秒；success3/partial6/failed0/skipped1；3篇success均有多栏提示、内容未改善；00561恢复化学物与结论；methods200–3000仍3/10
A已知缺口 / 留待后续范围 / docs/stage_a/REPORT.md / parser_summary调试字段暂缓；00589致谢泄漏及跨栏图注、HK0/HK1误报未改；B–F、0.1.2打包和网站成品尚未开始，按P1暂停
B 多栏阅读视图 / 已验收 / python acceptance/m09_sections.py；python scripts/check_real_anchors.py --root work/stage_b/real / 20场景通过；真实00589两处锚点通过；raw_blocks不变，跨页段落用逐页证据；同块跨栏文本以raw范围细分
B 真实10篇 / 已回归 / docs/stage_b/REPORT.md / success2/partial7/failed0/skipped1；00589结论恢复作者摘要、图注不进候选；方法候选6879仍被M14清空，交给C处理；methods长度合格2/10
B UNKNOWN指标 / 已记录 / docs/stage_b/comparison.json / 9/10篇sections含UNKNOWN（9篇解析、1跳过）；P1与B均5篇unresolved；C项需优先处理标题识别，而非仅多栏排序；UNKNOWN也承载Introduction，不能直接等同漏标题
B caption标记 / 已登记 / docs/diagnosis/WARNINGS_INVENTORY.md / caption_block:<raw_block_id>为informational；排除区间仍保存raw证据；正文as shown in Fig.2保留
C 方法章节与主候选 / 已验收 / python acceptance/m12_methods.py；python acceptance/m09_sections.py / 11+20场景；命名方法区不走关键词回退；完整块连续选段<=3000并标methods_primary_bounded，不截断句子；无章节回退规则保持
C 真实10篇 / 已回归 / docs/stage_c/REPORT.md / success4/partial5/failed0/skipped1；methods200–3000为6/10，达到长度目标但未证明语义质量；UNKNOWN仍9/10，unresolved6篇；全套20脚本146场景通过
D 化学式与晶面 / 已验收 / python acceptance/m10_chemicals.py / 9场景通过；晶面语境、单符号编号、价态及纯大写缩写门控；首次实测新增HH/HPCC误报已在D内修正，初版日志保留work/stage_d，正式结果work/stage_d_final
D 真实10篇 / 已回归 / docs/stage_d_final/REPORT.md / success4/partial5/failed0/skipped1；HK0/HK1均无；它们已在B被caption排除，D验证防止正文误报回流，不能重复归功；20实体19有旧标注/上下文支持、1待复核，非独立人工金标准
E 后置内容与审计 / 已验收 / python acceptance/repair_e_views.py / 5离线场景；Data availability/作者贡献/利益冲突并入非抽取边界；已知Introduction等UNKNOWN别名可审计，未标标题区仍unresolved
E 最终10篇 / 已回归 / docs/stage_e/REPORT.md / success4/partial5/failed0/skipped1；methods200–3000为6/10；199片段已判定、22未判定，3篇全可判定/6篇unresolved/1不适用，已判定范围泄漏0，未覆盖未判定区间
E 审计阳性自检 / 通过，退出码0 / python scripts/audit_leakage_selfcheck.py --output samples/audit_positive --cache work/stage_e/real/cache / 使用明确标注的历史错误阳性夹具，避免修好泄漏后把“没检出”误当审计失败；无缓存退出2，夹具不进生产
F 本地网页与托管站点 / 实现验收通过 / python acceptance/repair_web.py；node scripts/verify_web_assets.mjs website / 5个HTTP场景、10个JS/API检查；托管浏览器预筛与本机Python明确区分；受管环境缺cua_repl.js，未做浏览器交互QA
F 强制终止恢复 / 已验收 / python scripts/verify_resume.py / 实际kill子进程后resume，已完成论文三个阶段attempts=1，中断解析attempts=2；2断言通过
F 完整回归 / 已验收 / python scripts/verify_all.py --results work/stage_e/real/results / 20模块脚本+2修复脚本160活动场景、3开关、2恢复断言通过；contracts/storage12文件哈希未变
F 科研质量声明 / 已记录 / docs/DELIVERY.md / methods长度6/10；化学物20项仅助理上下文审阅，非独立金标准；未知recall和22未判定证据，质量未达生产标准，需人工复核
F 安装兼容与隔离验收 / 已验收 / python scripts/verify_install.py --python work/release/isolated/bin/python / 新PyMuPDF的fitz别名弃用输出曾破坏CLI单行JSON，已用兼容pymupdf导入修复；安装4项通过；隔离依赖下22脚本160场景也通过
F 发行物 / 已构建并校验 / python scripts/build_release.py / 0.1.2 wheel、源码zip、SHA256SUMS；网站提供下载及完整安装/限制/复验说明；发布确认以交付消息和站点当前版本为准
F 网站发布 / 已完成 / docs/release/PUBLISHED.json / 原有MatterLens私有站点发布成功；0.1.2 wheel与源码下载字节经SHA256核对；正式URL见DELIVERY与交付消息；未改变访问受众

Phase 1 / 真实文件验收 5/5；网页逻辑/API 19/19 / python acceptance/phase1_acquisition.py --corpus work/phase1/corpus --feed samples/phase1/search.atom.xml；node website/verify-phase1.mjs / 材料科学综合20篇、352页、87,246,820字节；仅文件获取与索引，科研字段留 Phase 2；无浏览器交互验收
Phase 1 网站 / 已发布并实际下载核验 / docs/PHASE1_REPORT.md / 20个PDF服务端就绪；线上ZIP 87,338,027字节逐份SHA256一致；官方在线检索20条；未做浏览器交互验收；Phase 2–4未开始

Phase 2 科研记录 / 已运行，质量需复核 / python acceptance/research_science.py / 20篇处理成功、956条证据；材料18、方法10、结论15、发现17篇非空；414条章节未识别，不能宣称零泄漏或准确率达标
Phase 3 研究分析 / 基线已验收 / python acceptance/research_intelligence.py / 词项哈希向量、原文引用、提及关系和并列比较；没有语义模型或自由生成问答
Phase 4 批处理 / 工程验收通过 / python acceptance/research_batch.py / 5000合成任务SIGKILL恢复通过；真实语料仍20篇；本地单写入、有界调度、无分布式集群
0.2 网站 / 逻辑/API验收通过 / node website/verify-research.mjs / 16项；网页新增论文为PDF.js规则引擎，固定20篇来自Python；无浏览器交互验收
0.2 正式发布 / 线上实际复验通过 / docs/RESEARCH_PUBLISHED.json / 20PDF+20科研记录+956片段，ZIP 90,322,176字节且全部SHA256一致；160旧验收+15扩展场景及网页19/16项通过；质量需人工复核；浏览器交互未验收

| 0.3.0 GitHub source handoff | 源码/文档已整理，创建仓库权限受限 | scripts/verify_all.py; unittest tests/master | 科研金标准、真实模型、双解析器、浏览器、Windows与生产部署未验收；详见KNOWN_ISSUES.md |
