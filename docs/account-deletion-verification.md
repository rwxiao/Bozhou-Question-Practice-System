# 第 08 项账号彻底删除验收

日期：2026-10-21。

## 已确认规则

用户明确确认删除普通用户账号、全部登录凭证、个人练习与历史、错题和收藏；公共题库、其他用户账号与记录保留。停用仍可用，不支持删除管理员。

纠错内容保留并清除提交者关联，历史操作审计保留。实现前已将这些处理写入任务；确认弹窗准确说明所有影响和不可撤销性，并建议仅禁止访问时使用停用。全部数据库变更在同一事务中执行。

## 验证结果

- `.venv/Scripts/python -m pytest tests/test_accounts.py -q`：6 passed。新增 3 项集成测试，覆盖匿名及普通用户越权、服务端明确确认、禁止删除管理员、重复请求、跨设备旧登录失效、已停用账号删除、进行中练习和历史清理、错题收藏清理、其他用户隔离、题库保留、纠错去关联、同名重新注册不恢复历史。
- 最后写入审计时使用 SQLite 触发器注入存储失败，通过 API 验证账号、登录、练习、收藏、纠错全部回滚，然后移除故障重试成功。仅对无可读 API 的已删数据补充存储断言。
- `.venv/Scripts/python -m pytest -q`：56 passed，1 条现有 Starlette/AnyIO 弃用警告。
- `npm --prefix frontend run typecheck` 和 `npm --prefix frontend run build`：通过；构建仍有组件 `use client` 与 sourcemap 警告。
- `python docs/account-deletion-browser.py`：Edge 无头浏览器，隔离临时数据库；桌面 1440×1000 和手机 390×844 验证影响提示、取消、必选确认、删除、刷新后列表移除、旧登录及旧密码失效，无页面脚本错误。
- 浏览器验收发现渲染层未传递 Checkbox 的 `required`，已修复并验证未勾选时不会删除。
- 后端 mypy 检查仍有 `app.py:164` 两条注册参数类型错误；对起始提交 `ffdc5182a27c5042539fdc17164485e711809192` 的原始 `app.py` 复查得到相同两条错误，本次未新增后端类型错误。

截图：`docs/screenshots/account-deletion/confirmation-desktop.png`、`confirmation-mobile.png`。

## 代码审查

起点 `ffdc5182a27c5042539fdc17164485e711809192`；仅审查本任务代码、测试及文档，排除既有部署等无关改动。规范与需求两个独立审查均为 0 项发现，无阻断问题。
