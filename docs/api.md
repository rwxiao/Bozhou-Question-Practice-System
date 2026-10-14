# 当前公开 API

认证使用 HttpOnly、SameSite=Strict cookie，生产设置 Secure。所有状态修改检查来源；用户资源按登录身份授权。API 错误为 HTTP 状态码及 detail，版本冲突返回409。服务端负责判分，未提交题目的响应不包含正确答案和解析。

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| POST | /api/register、/api/login、/api/logout | 用户名注册与登录退出 |
| GET | /api/me | 身份与强制改密状态 |
| POST | /api/password | 验证原密码、更改密码、撤销旧登录 |
| GET | /api/users | 管理员列出账号 |
| POST | /api/users/{id}/reset | 管理员重置并强制改密 |
| GET/POST | /api/banks | 查询可见题库 / 管理员创建 |
| PATCH | /api/banks/{id} | 管理员修改名称或下架，带 revision |
| GET | /api/template.csv、/api/template.xlsx | 下载管理员模板 |
| POST | /api/banks/{id}/preview | multipart 文件，全量校验及预览 |
| POST | /api/imports/{id}/commit | 幂等保存草稿，校验预览版本 |
| POST | /api/banks/{id}/publish | 带 revision 发布草稿 |
| POST | /api/banks/{id}/archive | 带 revision 与 question_id 保存归档草稿 |
| GET/POST | /api/sessions | 个人会话历史 / 发起新会话 |
| GET/PATCH | /api/sessions/{id} | 查询 / 保存 index、selected、revision |
| POST | /api/sessions/{id}/answer | 按 index、selected、revision 服务端判分；相同答案重复提交幂等 |
| POST | /api/sessions/{id}/finish | 带 revision 结束，不提交未答题 |
| GET | /api/learning | 个人错题、收藏、派生统计 |
| POST | /api/favorite、/api/mastered | question_id 与 value，修改个人状态 |
| GET/POST | /api/reports | 按权限读取 / 已答题反馈 |
| PATCH | /api/reports/{id} | 管理员处理状态 |

完整字段契约可在运行中的 /docs 查看。SQLite 事务串行化版本校验和写入；相同会话的旧版本不会静默覆盖新版本。后台资源不会向普通用户返回草稿或题库答案。管理员不是学习记录的代理身份，不能通过会话 ID 查看其他用户会话。


## 核对方式
创建练习可传 `review_mode`：`immediate`（默认，单题提交）或 `deferred`（先保存全部选择）。`POST /api/sessions/{sid}/review` 接收 `revision`，仅在统一核对练习的所有题目已有选择时提交整场。核对在单事务内进行，重复成功请求返回已核对状态；未完成返回 400、版本冲突返回 409。统一核对前 `/answer` 不接受提交，正确答案和解析不返回。
