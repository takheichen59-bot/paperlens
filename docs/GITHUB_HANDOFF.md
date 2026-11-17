# GitHub交付说明

## 用户指定的仓库

https://github.com/takheichen59-bot/paperlens

2026-11-17检查：仓库已存在、当前为public；连接账户为DerekChen315，对目标仓库的权限为pull=true、push=false。当前还不能将源码推送到该仓库。

需要将GitHub连接切换/重新授权到有写权限的账户，并授权访问paperlens；或为DerekChen315授予该仓库写权限及连接访问权限。不需要提供或粘贴任何密钥。

## 已准备内容

源码、网站源码、SQL基线迁移、合成样本、验收脚本、真实测试日志、功能说明和25项问题清单。密钥、运行数据库、真实PDF缓存、私人复核记录、备份与旧制品不在上传范围。

## 在自己电脑上传

在本机认证为目标仓库有写权限的账户，解压源码后：

```bash
gh auth login
git init -b main
git add .
git commit -m "Import PaperLens 0.3.0 source and documentation"
git remote add origin https://github.com/takheichen59-bot/paperlens.git
git push -u origin main
```

以上用于仍为空的目标仓库。如目标已新增文件/提交，先获取并保留原有历史；不要force覆盖。上传GitHub与部署网站是不同操作，本次上传不会自动部署后端或变更线上访问范围。
