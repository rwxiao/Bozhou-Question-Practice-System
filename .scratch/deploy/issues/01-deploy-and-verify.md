# 替换部署并验收
Status: resolved

本地12项API测试、前端构建、Compose配置校验通过。
已部署至82.157.182.162的/opt/bozhou-practice，quiz.onwarddesk.asia已切换。
3账号、2题库以及学习记录与会话迁移完成，users/objects/audit内容校验值与本机快照一致。
生产镜像构建成功，practice健康检查通过，首次自动备份完成；旧系统在线备份完整性通过。
公网浏览器验证HTTPS、管理员/普通用户登录、两上下文数据一致、刷新会话、角色隔离、Secure/HttpOnly Cookie及390px无横向溢出。
工作台HTTP200；新服务名practice避免共享网络app别名冲突。旧服务及卷保留。

## Comments

首次生产构建因PyPI下载慢耗时较长；生产Dockerfile排除仅用于本地检查的pytest/mypy，保留本地requirements。后端业务代码未改动。
公网浏览器首次验收受本机代理影响，测试浏览器使用no-proxy-server及disable-quic后完成验收；第二次等待选择器针对旧控制器而非React输出，纠正为真实header.site-header后通过，非线上应用故障。
