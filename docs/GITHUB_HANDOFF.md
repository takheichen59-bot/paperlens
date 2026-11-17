# GitHub交付说明

## 上传范围

源码、网站源码、SQL基线迁移、合成样本、验收脚本、真实测试日志、当前功能/问题文档。工作区内原始数据、数据库、PDF缓存、备份、密钥、构建目录与旧下载制品不会上传。

## 仓库与权限

默认建议私有仓库`DerekChen315/paperlens`。当前GitHub连接具有已有仓库写权限，但创建仓库操作返回：

`GraphQL: Resource not accessible by integration (createRepository)`

这不是上传成功。需要账户所有者新建空私有仓库并向GitHub连接授予该仓库访问权限，或明确选择一个已有仓库/分支。不会擅自把源码写入已存在的公开agent系列仓库。

## 在自己电脑上传的替代方式

解压源码后，在根目录：

```bash
gh auth login
git init -b main
git add .
git commit -m "Import PaperLens 0.3.0 source and validation documentation"
# 由你自己的GitHub授权创建私有仓库；不要对已有同名仓库重复创建
gh repo create paperlens --private --source . --remote origin --push
```

如已有目标空仓库，则使用其HTTPS地址添加origin后push，不要force覆盖原仓库历史。GitHub上传与网站部署是两件事，上传不会自动部署Python服务或变更已托管网站。
