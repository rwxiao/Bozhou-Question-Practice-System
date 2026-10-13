# 前端产物

在 frontend 目录执行 `npm ci` 与 `npm run build`，生成本目录下的 build/。

构建产物不提交版本库。FastAPI 从 build/index.html 提供入口，从 build/assets 提供静态资源。Docker 多阶段构建自动生成并复制产物。
