# 安装和运行

## 环境

Python3.11或更高；新版网站另需FastAPI/uvicorn，`.[platform]`会安装。PDF规则流程不要求模型密钥。OCR需要系统Tesseract英文包：Ubuntu可安装 `tesseract-ocr tesseract-ocr-eng`。

## 从GitHub运行

```bash
git clone https://github.com/takheichen59-bot/paperlens.git
cd paperlens
python -m venv .venv
source .venv/bin/activate
# Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[platform,test]'
python -m science_platform --version
python -m science_platform serve --data ./data/science-platform
```

仓库写入需完成GitHub认证并获得该仓库的写权限。网站地址 http://127.0.0.1:8765 。服务默认仅监听本机。`launch/start.bat`和`launch/start.sh`可安装并启动；Windows启动未实机验证。

### 无模型使用

检索→选中论文→批量下载→解析→检查原文。公开元数据和OA获取需要网络；解析已有本地PDF可以离线。页面深度提取会返回NOT_EXECUTED，不会生成伪内容。JSONL/CSV/Excel仍可导出实际存在的元数据/解析记录。

### 配置模型与可选解析器

复制 `.env.example` 为 `.env`，在服务端设置：

- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`：兼容严格结构化输出的OpenAI API。
- `EMBEDDING_BASE_URL`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL`：真实语义重排。
- `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `SPRINGER_API_KEY`, `ELSEVIER_API_KEY`：来源授权。
- `GROBID_URL`, `DOCLING_COMMAND`：独立安装和运行的解析服务/程序。

不在浏览器输入模型/出版商密钥。配置可用不代表集成测试通过。本仓库没有替你部署GROBID/Docling或购买API权限。

### 分离worker

```bash
python -m science_platform serve --external-worker --data data/science-platform
# 第二个终端，激活相同环境
python -m science_platform worker --data data/science-platform
```

队列使用租约和有限尝试，暂停和恢复可在任务监控页执行。默认适用单机小批处理。不要将数据库改为旧M02数据库。

## 规则科研汇总

```bash
paperlens-research sync --online --count 20 --workdir work/library --output results
paperlens-research run --manifest /absolute/path/index.json --workdir work/library --output results --workers 2
```

本地清单可使用 `{ "papers": [...] }`，每篇有 `id`、`title`、`file`、作者/来源等元数据；file相对清单目录。也可使用meta/pdf条目列表。规则输出及新平台JSONL不是相同schema，详见旧版文档。

### 导入授权的已有语料到新版

```bash
python -m science_platform import-corpus --data data/science-platform --corpus /absolute/path/corpus --limit 20
```

corpus目录包含`index.json`及其`papers`中`file`指向的PDF。该命令保存实际本地路径，不会把文件上传GitHub。移动语料后需要重新导入。未配置模型时只完成解析，深度记录为NOT_EXECUTED。

## 打wheel

```bash
python -m pip wheel . --no-deps --wheel-dir dist
# 安装后运行：
python -m science_platform serve
```

独立安装网页依赖需选择平台extra，例如 `pip install 'dist/paper_extraction_contracts-0.3.0-py3-none-any.whl[platform]'` 。

## 新旧网站

`src/science_platform/web`由FastAPI直接提供。`website`是Worker站点源码快照，不会随GitHub push自动部署；缺少R2绑定时，涉及托管文件/保存的操作不能完整工作。历史下载制品不在仓库。不得把仓库创建描述为在线平台部署完成。
