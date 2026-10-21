# 第 07 项：姓名注册、用户列表与账号停用验收

日期：2026-10-21

## 实现结果

- 注册只要求用户名、姓名、密码，无审批；姓名去首尾空白并校验 1–50 字符，保留原有用户名唯一与密码规则。
- 独立用户管理页显示用户名、姓名、真实注册时间、角色及停用状态，保留密码重置入口，不显示密码或个人成绩。
- 启动时幂等添加 `name`、`created_at`、`disabled` 列；旧账号姓名及注册时间保留 NULL，界面显示未知，原昵称、登录及个人记录保留。
- 仅管理员可停用普通用户；事务内设置停用状态并撤销全部登录。新登录及受保护功能均在服务端拒绝，管理员不能被停用。
- 停用不修改个人练习、历史、错题或收藏，操作留有审计记录。

## 自动验证

- `.venv/Scripts/python.exe -m pytest tests/test_accounts.py -q`：3 passed。
- `.venv/Scripts/python.exe -m pytest -q`：53 passed；仅现有 Starlette/AnyIO 弃用警告。
- `npm --prefix frontend run typecheck`：通过。
- `npm --prefix frontend run build`：通过；已有组件的 `use client`/sourcemap 打包提示不影响产物。
- `git diff --check`：通过。

API 测试覆盖必填姓名、空白及非字符串姓名、长度、用户名大小写唯一、密码规则、返回字段不含密码/哈希、未登录及普通用户越权、管理员保护、重复停用、两个设备登录失效、新登录拒绝、个人记录逐字保留；真实旧表结构迁移并重复初始化后，旧登录、密码、昵称及练习记录仍可使用，注册时间明确为未知。

## 浏览器验证

使用隔离临时数据库及本机 Edge（Playwright headless）。启动临时服务器后运行：

```powershell
$env:BROWSER_CHANNEL='msedge'
python docs/registration-disable-browser.py
```

默认服务器地址 `http://127.0.0.1:8771`，可通过 `BROWSER_BASE` 指定；测试管理员为 `admin`，密码为 `Admin-test-12345`。仅用于隔离测试环境。

结果：PASS。验证手机端必填姓名与注册、普通用户登录和列表越权、管理员用户管理页与刷新恢复、注册信息、手机无横向溢出、取消停用、确认停用、已有登录失效和停用后登录提示。无浏览器脚本错误。

人工查看截图：

- [手机注册](screenshots/registration-disable/registration-mobile.png)
- [桌面用户列表](screenshots/registration-disable/users-desktop.png)
- [手机用户列表](screenshots/registration-disable/users-mobile.png)

## 审查

按照 code-review 技能分别进行 Standards / Spec 独立审查。已清理不可达用户列表模板，并为四个既有浏览器脚本补齐必填姓名的注册数据。复核结果：Standards 0 项剩余发现，Spec 0 项剩余发现。
