# 第 01 项：年份、项目与题库归属管理验收

日期：2026-10-21。任务：`.scratch/department-question-bank/issues/01-directory-management.md`。
起点：`dd2e71851c53eeda0a37b65e902b44caefc86b55`，当前分支 `main`。

## 实现与范围

目录使用现有 SQLite objects 文档存储，新增 year/project 类型。题库可选 project_id，不改题库或题目 ID；目录关联检查与写入处于同一个 BEGIN IMMEDIATE 事务。删除项目检查所有题库，不按发布、下架或未来归档状态过滤；年份有任何项目即拒绝删除。

管理首页默认题库管理。桌面左目录右列表，手机下拉；可创建、改名年份和项目，删除空目录，在项目下新建多个题库并跨年份移动。旧题库缺少归属仍可读取，并有待整理管理入口。第 02–08 项及部署不在本次范围内；未提前改变学习者可见性和旧题库迁移规则。

## 自动验证

- 首轮新 API 测试先失败（年份 POST 返回 404），实现后通过。
- 最终 `.venv/Scripts/python.exe -m pytest -q`：16 passed，19.48 秒；既有 Starlette/AnyIO 弃用警告 1 条。
- 新增 3 项公开 HTTP API 集成测试：目录创建改名及持久化、多个题库、非空删除拒绝、空目录删除；普通人员越权和非法归属；跨年份移动保留题目、错题、收藏及已有练习，并验证旧版本冲突。
- `.venv/Scripts/python.exe -m mypy app.py ops --check-untyped-defs --ignore-missing-imports`：通过。
- `npm --prefix frontend run typecheck`、`npm --prefix frontend run build`：通过。Vite 仍有既存第三方 use client 忽略和 sourcemap 提示，构建退出码 0。
- controller.js/admin-view.js 的 `node --check` 及 `git diff --check`：通过。

## 浏览器验收

独立本地服务 `127.0.0.1:8766`，使用隔离测试数据库，不使用现有业务数据库。

- 管理员登录默认进入题库管理；创建 2026、2027 年份及两个备考项目，创建安全专业题库。
- 手机选择 2026 项目，将题库移动至 2027 项目；确认下拉选中项、当前位置和题库列表同步。
- 手机改名项目为“年度能力考试”，刷新后项目名称及移动后的题库归属保留。
- 桌面改名年份为“2027年度”；左目录右列表可操作。
- 请求视口 1440×1000、390×844；系统缩放下实际 CSS 宽分别为 1091 和 295，文档宽 1091 和 284，无内容区横向溢出。手机原有主导航保留横向滚动。
- 验收中定位并修复：分组 option 被现有表单适配器过滤；目录选择与列表切换不同步；预填 input 被当作受控值造成改名提交旧值。
- 截图：[桌面](screenshots/department-directories/desktop.png)、[手机](screenshots/department-directories/mobile.png)。本次未把删除操作的浏览器弹窗作为验收证据，删除规则由公开 API 测试验证。

## Standards

独立标准审查最初发现 1 项低优先级问题：提取的 bankList 接收未使用参数。已删除，复审剩余 0 项。

## Spec

独立规格审查最初发现 1 项 P2：手机选择器在移动题库后保留旧选中值。已修复并在手机浏览器验证，复审剩余 0 项。

两轴剩余发现均为 0，无未解决审查问题。保留任务开始前的 Dockerfile、部署配置、部署文档和其他未跟踪资料，不纳入本次提交。
