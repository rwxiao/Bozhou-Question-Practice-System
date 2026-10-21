# 任务 03：简化题库导入与更新验收

日期：2026-10-21。任务：`.scratch/department-question-bank/issues/03-import-and-update.md`。

## 实现

- 项目内新建题库并上传，已有题库提供更新入口；CSV/Excel 模板及分类空值沿用已有能力。
- 选择文件后自动校验，显示文件题数、新增/修改数量、前 10 道样题和行/字段错误。
- 预览后可直接生效或保存草稿，草稿可稍后发布；直接生效复用发布逻辑，在单个事务内合并并确认。
- 保留版本冲突、同方式重复确认幂等和题库内编号匹配；缺失题保留，历史和进行中练习保留快照。
- 有已有草稿时提示本次合并基于草稿，直接生效将一并发布。新建时文件失败会留下空草稿题库供重试，重试使用同一题库。

## 验证

- `.venv/Scripts/python.exe -m pytest -q`：27 passed。仅现有 Starlette/anyio 弃用警告。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过；现有 Radix 的 use client 指令和 sourcemap 警告不阻止构建。
- 隔离数据库 `data/import-ticket03-browser.db`；本地 uvicorn 端口 8768，管理员测试凭据。
- `python docs/import-update-browser.py`：桌面 CSV 新建并直接生效、Excel 更新存草稿、手机发布草稿、错误行编号、手机直接生效均通过，无页面异常和横向溢出。脚本另外覆盖新建后解析失败重试，确认不重复建库。
- [桌面截图](screenshots/import-update/desktop-preview.png)、[手机截图](screenshots/import-update/mobile-preview.png) 已逐张查看。
- 新增公开 API 测试先验证直接生效失败，再实现事务内发布使 CSV/Excel 两条测试通过；随后扩展权限、新建/更新、草稿隐私、计数、冲突、编号隔离、缺失保留与快照回归。

## Standards

独立审查 0 项文档标准或基线异味发现；另提示的新建预览失败重试风险已修复，并补浏览器回归。

## Spec

独立审查 0 项需求实现发现。

审查起点：4736b970c53cb9ecad803da01f21e2699d629220。排除任务开始前的 Dockerfile、部署文件、GLOSSARY、其他任务规格和草案。未部署。
