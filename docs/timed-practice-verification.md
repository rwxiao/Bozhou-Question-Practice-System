# 任务 06：可选限时练习验收

日期：2026-10-21。
任务：[06：四种练习方式的可选限时](../.scratch/department-question-bank/issues/06-timed-practice.md)。

## 行为

四种练习方式均可选不限时或填写 1–1440 整数分钟，默认不限时。服务端保存截止时间，前端基于服务端时间和单调时钟显示倒计时并定期同步。已有不限时会话兼容。

服务端在读取详情、历史或写入时按截止时间结算；到期拒绝新增作答及统一核对，只有已提交答案计分。无人在线时不依赖浏览器后台定时器；返回请求会持久化结束状态。两设备的写事务串行，结束幂等，已结束结果不变。服务端草稿保留为未答，本机待同步选择不会转成答案。

## 已执行

- `.venv/Scripts/python -m pytest -q`：50 passed，含 19 项限时测试；有一条既有 Starlette/AnyIO 弃用警告。
- 限时 API 测试通过临时数据库和公开 HTTP API 验证：四种方式、合法/非法时长、截止前和精确截止、跨客户端读取、不在线后访问历史、超时草稿/作答/统一核对、草稿不计分、并发提交、截止时并发结束/提交、重复结束及原不限时行为。测试只替换系统时钟边界，不通过数据库断言实现。
- `npm --prefix frontend run typecheck`、`npm --prefix frontend run build`：通过。构建有既有第三方 `use client`/sourcemap 提示，退出成功。
- `.venv/Scripts/python -m mypy app.py ops/backup.py --check-untyped-defs --ignore-missing-imports`：通过。
- `node --check frontend/src/controller.js`、`git diff --check`：通过。
- `python docs/timed-practice-browser.py`：Edge 无头浏览器通过。脚本使用独立临时数据库及仅测试进程可控时钟，不改生产数据或提供生产调时接口。验证不限时默认禁用分钟输入、四种方式均可开关限时、非法分钟数校验、倒计时递减、刷新后续计、390px 手机无横向溢出、到期自动显示结果、未提交草稿仍未答及新页面从历史返回相同结果；页面错误为 0。另验证错误密码仍显示服务端错误，覆盖审查发现的空会话错误处理问题。

截图：

- [桌面配置](screenshots/timed-practice/desktop-config.png)
- [手机倒计时](screenshots/timed-practice/mobile-countdown.png)
- [手机到期结果](screenshots/timed-practice/mobile-result.png)

浏览器使用同一登录上下文的新页面验证返回；双设备行为由两个独立登录的 API 客户端及并发请求验证，未声称使用两台物理设备。

## 代码审查

使用 code-review 技能，以起始提交 `5776336f72e53f0bda261e530494a4339e72b1bd` 的任务文件差异分别进行规范和需求审查，排除工作区既有部署等改动。

- Standards：项目规范违规 0。额外发现新错误处理条件在两个会话 ID 都缺失时误匹配，已添加会话存在性检查及浏览器回归断言，独立复核通过。
- Spec：第 06 项需求缺失、越界或错误 0。

未执行部署；既有部署文件及其他任务保持原状态。
