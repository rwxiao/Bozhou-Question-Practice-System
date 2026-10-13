# 正式服务器部署验收

Status: open
Type: task

## Scope

本地实现已交付。Docker 引擎未运行，且尚未指定实际服务器与域名，因此以下工作尚未验证。

## Acceptance

- 在运行 Docker 引擎的环境构建镜像并启动 Compose；核对非特权用户的数据卷写入权限。
- 配置实际域名和管理员凭据；验证 HTTPS 证书、生产 Secure cookie、注册登录及来源检查。
- 手机与电脑分别登录同一账号，验证未提交选择、当前位置、收藏与错题接续及冲突提示。
- 检查备份服务每日运行、14份保留及日志；另存离机备份并按 README 演练容器恢复。

## Context

完整需求见 ../spec.md；本地验证记录见 ../../../docs/verification.md。本任务没有执行外网发布。
