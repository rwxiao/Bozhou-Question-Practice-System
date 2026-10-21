# 腾讯云替换旧刷题系统

服务器：82.157.182.162，root，SSH22；域名 quiz.onwarddesk.asia。
用户确认迁移本机现有数据，授权SSH公钥连接及读取local-access.json用于验收，不输出密码。
新服务部署至 /opt/bozhou-practice，复用 network-workbench_default 和现有 Caddy，仅替换刷题域名路由。
本机数据库在线备份完整性通过；3账号、2题库，迁移副本清除旧登录会话，保留原库。
旧服务、旧卷保留；网关配置先备份和验证再reload，失败恢复原路由。
验收：镜像构建、健康检查、数据库迁移、自动备份、HTTPS、管理员/普通用户登录、桌面手机数据一致、刷新恢复及工作台可访问。
