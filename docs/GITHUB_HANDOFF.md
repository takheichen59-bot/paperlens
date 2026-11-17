# GitHub交付说明

## 仓库

https://github.com/takheichen59-bot/paperlens

用户指定的公开仓库。2026-11-17已确认DerekChen315的协作者写权限生效。源码准备阶段的创建仓库/待接受邀请障碍已经解决。

## 上传核验

源码已推送到main分支，并逐一核对374个文件的Git blob SHA，全部一致。首次源码提交：`6a6def9641591923913e8963172176e5d68d369b`。核验回执见[GITHUB_UPLOAD.json](GITHUB_UPLOAD.json)。后续提交记录交付状态，不改变已验证的程序实现。

GitHub Actions已触发；其状态以仓库Actions页面为准，不把“已经触发”当作“已经通过”。

## 上传内容

Python源码、新版本地网站、旧版Worker网站源码快照、SQL迁移基线、合成测试样本、验收脚本、安装启动文件、功能介绍、25项已知问题及真实测试日志。

密钥、实际.env、运行数据库、个人文献库、真实论文PDF缓存、私人复核记录、备份和旧构建制品不在上传范围。

## 从仓库开始

```bash
git clone https://github.com/takheichen59-bot/paperlens.git
cd paperlens
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[platform,test]'
python -m science_platform serve --data ./data/science-platform
```

浏览器打开http://127.0.0.1:8765。完整安装见INSTALL.md。

## 主要文档

- README.md：功能概览、入口与限制。
- PROJECT_OVERVIEW.md：产品工作流、三条代码路径、数据和功能内容。
- KNOWN_ISSUES.md：25项现有问题、优先级、未执行验证。
- INSTALL.md：安装、运行、规则批处理、模型与解析器配置。
- ARCHITECTURE.md：架构、API路由与状态库数据字典。
- VALIDATION.md：实际测试、原始日志与验证边界。

上传GitHub与部署网站是不同操作。本次源码上传不自动部署Python服务，不变更既有托管网站或其访问范围。真实模型、人工金标准、浏览器E2E等未完成事项仍保持原状态，不因源码上传而视为完成。
