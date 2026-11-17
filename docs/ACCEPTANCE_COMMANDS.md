# 模块验收命令

在项目根目录、依赖安装完成后运行。全部离线，无密钥或模型下载。

- `M01`：`python acceptance/m01_contracts.py`
- `M02`：`python acceptance/m02_storage.py`
- `M03`：`python acceptance/m03_arxiv_metadata.py`
- `M04`：`python acceptance/m04_http_policy.py`
- `M05`：`python acceptance/m05_pdf_download.py`
- `M06`：`python acceptance/m06_resume.py`
- `M07`：`python acceptance/m07_pdf_text.py`
- `M08`：`python acceptance/m08_layout_cleaning.py`
- `M09`：`python acceptance/m09_sections.py`
- `M10`：`python acceptance/m10_chemicals.py`
- `M11`：`python acceptance/m11_ner_adapter.py`
- `M12`：`python acceptance/m12_methods.py`
- `M13`：`python acceptance/m13_conclusions.py`
- `M14`：`python acceptance/m14_extraction_validation.py`
- `M15`：`python acceptance/m15_llm_contract.py`
- `M16`：`python acceptance/m16_single_pipeline.py`
- `M17`：`python acceptance/m17_batch_pipeline.py`
- `M18`：`python acceptance/m18_exports.py`
- `M19`：`python acceptance/m19_cli.py`
- `M20`：`python acceptance/m20_end_to_end.py`

全量：`python scripts/verify_all.py`
端到端：`python acceptance/m20_end_to_end.py`
可选 pytest：`python -m pytest -q acceptance/m20_end_to_end.py`
