# 八项任务审查修复验收

日期：2026-10-21。修复基线：`d554673`。

- 收藏回看：无练习快照的个人收藏使用题库已发布内容补齐，归档后仍可回看；不会显示不存在的原练习入口，也不读取草稿或其他用户的收藏。
- 历史归属：旧会话在首次分配项目时补齐快照，在题库移动、年份或项目改名前固定已有归属；快照不修改答案、进度及会话 revision。
- 维护性：四个视图/控制器共享 HTML 转义函数，提交事件按账号、练习、目录和导入拆成处理函数，保留现有事件协议。
- 类型检查：明确失败函数不会返回，注册密码沿用校验后字符串转换，消除两项 mypy 错误。

验证结果：

- 新增两个缺陷回归测试，修改实现前均失败；历史用例进一步覆盖移动、项目改名、年份改名及重启。
- `.venv/Scripts/python -m pytest -q`：60 passed，1 项既有 Starlette/AnyIO 弃用警告。
- `.venv/Scripts/python -m mypy app.py ops/backup.py --check-untyped-defs --ignore-missing-imports`：通过。
- `npm --prefix frontend run build`：类型检查及构建通过，有既有第三方 `use client`/sourcemap 警告。
- `node --check frontend/src/controller.js`、`node --check frontend/src/learner-view.js`、`git diff --check`：通过。
- `python docs/review-fixes-browser.py`：独立临时数据库和本地服务，Edge 无头浏览器验证注册、登录、目录创建、新建题库上传及直接生效、归档、1440px/390px 收藏题目答案回看、无错误的原练习入口、无横向溢出；页面异常为 0。

未操作生产数据或部署文件。工作区原有部署改动、未跟踪规格和术语表不纳入本次修复提交。
