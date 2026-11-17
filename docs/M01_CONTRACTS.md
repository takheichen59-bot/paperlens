# M01：论文信息抽取契约

本目录仅包含 M01 的数据模型、抽象接口、错误类型与 JSONL 记录校验。
不包含来源访问、PDF 解析、抽取算法、pipeline、SQLite 或导出器。

## 安装与验收

需要 Python 3.11+。第三方运行依赖只有 Pydantic v2。

```bash
python -m pip install 'pydantic>=2,<3'
python acceptance/m01_contracts.py
```

验收脚本自行将本目录的 `src` 插入导入路径，无需预先安装本项目。
可选 editable install：

```bash
python -m pip install -e .
```

setuptools 是构建工具依赖，不是额外的运行依赖。

## 模型和 JSON 边界

- `models.py`：7 个顶层模型、4 个嵌套模型；全部字段必须显式提供。
- 模型配置均为 `ConfigDict(frozen=True, extra="forbid", strict=True)`。
- Python 直接构造时使用枚举实例、tuple、Path、date 和带时区 datetime。
- JSON 输入使用 `model_validate_json`，允许 JSON 数组对应 tuple、枚举字符串、ISO 日期时间和路径字符串。
- `model_dump_json` 输出普通 JSON 数组，所有 tuple 保序，包括嵌套集合。
- 哈希和配置指纹均采用 64 位小写十六进制 SHA-256。
- DOI 接受标识符，不接受 DOI URL；规范化为小写，不推断未知 DOI。
- `PageText` 使用 `page_number`、`text`。
- `TextBlock` 使用 `block_id`、`page_number`、`text`、`bbox`；`bbox` 可为 null。
- `Section.value` 是按阅读顺序排列的原始文本块 ID tuple；不包含可变字典。
- `ExtractionResult.field_status` 是有序 `(ExtractionField, FieldStatus)` 对的 tuple，三个字段各出现一次；JSON 形式为嵌套数组。
- `TaskRecord.error` 是 `ErrorKind | None`，仅保存错误分类。统一异常的其他安全信息通过 `ContractError.to_dict()` 获取。本模块不执行任何存储或日志写入。

## JSONL 记录校验

`validate_record(dict)` 先构造 `JSONLRecord`，再检查字段、证据和 status 的关联。
返回不可变 `RecordValidationResult(valid, record, errors)`：无效结果的 `record` 必定为 null。

所有输出字段必须存在。doi 和 SourceSnippet.section 可为 null；化学物列表、方法、结论均不可为 null。
空值使用 `[]` 或 `""`。化学物列表成员和原文片段必须为非空白文本。

校验包括：

- 正整数页码；原文偏移为 Python Unicode 字符位置，采用左闭右开区间。
- 偏移长度必须与片段长度一致；跨页证据应拆分为单页片段。
- 非空字段必须有同字段证据，空字段不得挂该字段证据。
- 每个化学物须在某个化学物证据片段出现；方法与结论证据须包含在对应字段文本中。
- success 要求三字段均有证据；partial 要求至少一个字段有证据，允许完整结果因后续质量告警降级；failed 不得包含有效字段证据。

这里无法验证证据是否真实存在于 PDF 原始块中，也无法验证科学语义。全文定位校验属于后续 M14。
直接构造 JSONLRecord 只做字段结构校验；对外的有效记录判定必须经过 validate_record。

## 错误安全

`ContractError` 包含 stage、error_kind、retryable、safe_message、cause。
`from_exception()` 不使用原始异常消息生成日志；`to_dict()` 只返回受控的四字段白名单，永不返回 cause。

safe_message 采用固定错误目录；如显式传入，必须匹配该错误类型的目录值。
原始 cause 及 Python 异常链仅保留在内存中。需要安全日志时只序列化 to_dict()，不得输出原始异常链。
JSONL 校验错误只返回受控错误代码和计数，不包含输入值或输入字段名。
验收失败时也不输出记录全文、原始异常文本或调用栈。

## 五份固定样本

所有论文内容为合成数据，不是实际论文或真实研究结论。

1. 完整合法记录：1 个 case，接受。
2. DOI 为 null：1 个 case，接受。
3. 非法 null：2 个 case，chemicals 和 conclusions 为 null，均拒绝。
4. success 缺少 methods 及其证据：1 个 case，拒绝。
5. 三个抽象类直接实例化：分别抛 TypeError。

预期汇总：`SUMMARY: 8 passed, 0 failed; 5 fixture files`，退出码 0。
任何预期不满足时退出码 1。

## Stage 枚举增量补丁

`Stage.EXPORT = "export"` 已在原有成员中，本次保留其值和位置；
仅在 Stage 末尾追加 `Stage.STORAGE = "storage"`。其他枚举及契约接口不变。

新增 `samples/m01/06_stage_enum.json`，作为单个验收 case，检查 STORAGE、EXPORT
可由字符串构造，原有成员及顺序保持，未知阶段字符串仍抛出 ValueError。

补丁后的验收汇总为 `SUMMARY: 9 passed, 0 failed; 6 fixture files`，退出码 0。
上文的 8 项汇总保留为原始五份样本的基线说明。
