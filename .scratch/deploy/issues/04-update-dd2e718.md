# 9:47版本更新部署（dd2e718）
Status: resolved

2026-10-14完成部署，新增统一核对模式及简化操作。13项API测试、前端构建与真实服务器镜像健康检查通过。
公网验证管理员及学习者登录、两端数据一致、刷新会话、角色隔离、手机页面无溢出、已有练习显示及统一核对页面入口和OpenAPI路由存在。未创建或修改线上练习答案。
更新前后users/objects/audit内容SHA256一致：e959c1839c5615d0b0c90d72ee5ddefbb2637ebf35f42f8a6c1504c9bf7ce95e；3账号、2题库、3学习对象、7会话。
备份：/root/bozhou-release-backups/20261014T014840Z；回退镜像bozhou-practice:before-20261014t014840z。自动备份正常，个人工作台HTTP200。
