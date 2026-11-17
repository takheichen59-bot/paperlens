# PaperLens

<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
需要批量发现、合法获取、比较和导出科学论文的研究者；本轮真实验证语料主要来自材料科学。中文操作界面，保留论文原文语言。

## Product Purpose
将真实文献检索、PDF获取、规则科研记录、证据回查与可读文件导出串成可操作流程。用户明确要求首页优先突出文献检索。

## Positioning
四核心字段为材料、方法、主要发现和结论。规则候选保留原文页码、块、字符偏移和PDF哈希；材料角色与数值归属独立显示，原始候选不静默改写。

## Operating Context
检索关键词、DOI或arXiv ID，选中文献，批量处理并检查证据，保存复核意见，导出Excel、CSV、JSONL或处理报告。桌面研究场景优先，同时支持移动浏览和键盘操作。

## Capabilities and Constraints
- 唯一用户源码仓库为takheichen59-bot/paperlens。main保持不动；本轮网站工作从保留1711383的新分支开展。
- 已有Python本地平台与Worker网站是独立实现。Sites托管使用Worker ESM和独立R2，不将research-1冒充ScientificRecord，也不修改冻结contracts/storage/SQL。
- 首页优先文献检索（用户已确认）。下载、导出、复核和证据都必须真实可用；缺失字段明确留空。
- 无真实LLM、OCR或双解析器服务时明确未执行；不购买模型，不把私有论文上传到外部模型。
- 默认发布为仅所有者可访问的网站，保留用户数据。新的R2不迁移旧库。
- 规则提取与来源切片校验不是科研正确性认证，没有独立科研准确率金标准。

## Brand Commitments
PaperLens名称，中文清晰直接的任务文案。用户要求下载并使用官方Impeccable skill改进网站设计。

## Evidence on Hand
五篇真实CC BY 4.0论文，来源和SHA256在samples/research/real_role_corpus.json；已有实际记录、单篇/批次Excel、JSONL与处理报告。结构状态为2 success、2 partial、1 failed。早期20篇统计只作历史记录，不作为本轮结果或实时搜索。

## Product Principles
先找到论文，再检查可回查的来源；原始自动结果与修订分开；空白和失败如实显示；优先批量获取和可用导出，不扩展复杂Agent或知识图谱。

## Accessibility & Inclusion
表单带标签，键盘焦点可见，错误可读，状态不只依赖颜色。长英文标题、中文标签和证据段落在手机与桌面均可读取。
