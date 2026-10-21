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


## 年份、备考项目与题库归属（第 01 项）

以下目录接口仅管理员可用；普通用户返回 403，未登录返回 401。

| 方法 | 路径 | 请求与行为 |
| --- | --- | --- |
| GET | /api/directories | 返回 `years`、`projects`；项目含 `year_id` |
| POST | /api/years | `{name}` 新建年份，返回 `{id,name}` |
| PATCH | /api/years/{id} | `{name}` 改名年份 |
| DELETE | /api/years/{id} | 仅无项目时删除，否则 409 |
| POST | /api/projects | `{name,year_id}` 新建备考项目 |
| PATCH | /api/projects/{id} | `{name}` 改名备考项目 |
| DELETE | /api/projects/{id} | 仅无任何关联题库时删除，否则 409；下架、归档状态也阻止删除 |

名称须为去除两端空白后 1–100 字符的字符串。归属须为存在的年份／项目 ID；类型不合法返回 400，不存在返回 404。
`POST /api/banks` 可传 `project_id`；`PATCH /api/banks/{id}` 可用 `{revision,project_id}` 调整归属（冲突返回 409）。年份通过项目关联推导，不接受独立的题库年份，避免年份与项目不一致。移动只改变归属和题库 revision，不改变题库 ID、题目、草稿、练习及个人记录。
为兼容旧题库，未传 `project_id` 的旧创建方式继续可用，旧数据无需回填；新管理页面创建题库要求选择项目，未分配题库在待整理入口管理。本项不改变旧题库对学习者的可见性，迁移规则由第 05 项实施。

## 按目录选择练习（第 02 项）

`GET /api/learning/directories` 向已登录用户返回 `years`、`projects`，仅包含有已发布题库的项目及其年份；不暴露仅有私有草稿的目录。目录写入和管理查询仍使用管理员接口，权限不变。

普通用户的 `GET /api/banks` 摘要新增 `project_id`（旧题库为 `null`），保留 `count`、`categories`，不返回题目、答案或草稿。知识分类只在所属题库内生效；空分类允许导入，全部无分类时前端隐藏分类筛选。

`POST /api/sessions` 继续接收一个 `bank_id`、可选 `category`（空为全部）、`mode`（顺序练习／随机练习／错题练习／收藏练习），保留原有 `amount`、`restart`、`review_mode`。空范围返回 400 且不创建会话，错题、收藏和历史按登录用户隔离。

首页按年份→备考项目→题库选择；切换上级清空下级。本机按用户 ID 保存目录、题库、分类和练习方式，刷新及重新登录可恢复，失效后明确提示并等待重新选择，不自动替换题库。记忆选择属于当前浏览器；已有练习的进度继续由服务端跨设备同步。第 05 项迁移前保留“未分配年份／未分配项目”的旧题库兼容选择。
