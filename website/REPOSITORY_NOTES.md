# Worker网站源码快照

此目录来自已有MatterLens托管网站源码，并包含尚未线上验证的条件发布修复。它与根目录新版Python网站不同。

- 新版FastAPI网站请从仓库根目录执行`python -m science_platform serve`。
- 此目录的`node verify-*.mjs`是逻辑/API测试，不是浏览器测试。
- `build.mjs`需要`.openai/hosting.json`和实际发布制品；仓库只提供`hosting.example.json`模板，不含真实project_id或部署凭据。
- 历史`/downloads/*`依赖线上制品，GitHub源码不会附带这些旧wheel/ZIP；不要把源码快照当完整离线镜像。
- `web_assets/*index.json`来自既有公开论文元数据，不能将它当实时新检索结果。
- 本次推送GitHub不发布Worker、不改变访问范围，也不替代真实R2和浏览器验收。
