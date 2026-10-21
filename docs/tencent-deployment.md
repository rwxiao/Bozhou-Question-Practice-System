# 腾讯服务器部署准备

目标：以现有 quiz.onwarddesk.asia 域名接入工作台 Caddy。新服务不绑定主机80/443端口，避免与已有网关冲突。使用 compose.server.yaml，而非自带独立 proxy 的 compose.yaml。

部署包：.scratch/deploy/bozhou-practice-tencent.tar.gz。包含应用源码、前端源码、锁文件和部署文件，不包含数据库、local-access.json、.env、Git、虚拟环境或 node_modules。

服务器建议目录 /opt/bozhou-practice，与 /root/onwarddesk-quiz 分离，保留旧服务与旧数据以便切回。新数据库使用 bozhou-practice_database 卷，备份位于 bozhou-practice_backups 卷。两个系统数据库结构不兼容，不直接覆盖。

2026-10-13已完成部署：82.157.182.162，/opt/bozhou-practice，HTTPS域名quiz.onwarddesk.asia。用户授权SSH连接和本机账号凭据验收，凭据未输出。已迁移本机数据，3账号、2题库、3份learning和3份session对象；保留本机源库，迁移副本移除旧登录会话。

users/objects/audit内容SHA256在本机迁移快照与服务器一致：82bf3749813b5e90f8434430fa1553a02eafeb5e4d8012b2650538d75370ade4。
现有Caddy通过验证并reload，工作台HTTP200。旧服务和旧卷保留；旧库在线备份为/root/quiz-migration-backups/old-quiz-20261013T144616Z.sqlite；路由备份为/opt/network-workbench/deploy/Caddyfile.before-bozhou-20261013T144646Z。

## 接入步骤（连接服务器后核实实际配置）

1. 上传并解压部署包至 /opt/bozhou-practice。
2. 确认正在运行的工作台 Caddy 所属网络，设置 GATEWAY_NETWORK；默认按此前记录为 network-workbench_default。
3. 以权限600创建 .env，填写 DOMAIN=quiz.onwarddesk.asia、ADMIN_USERNAME、至少10字符的管理员密码。不要将真实密码写入项目仓库或输出到日志。
4. 如迁移本机数据，使用 SQLite 在线备份生成独立快照并检查完整性，应用首次启动前将快照写入新数据库卷，属主10001。不要上传 local-access.json；旧登录会话需要重新登录。
5. 执行 docker compose -f compose.server.yaml up -d --build practice backup。检查 practice healthcheck 与备份日志。切换路由前检查新服务HTTP页面和API。服务名使用 practice，避免共享网络中的 app 别名与工作台冲突。
6. 备份工作台实际 Caddy 配置，只将 quiz.onwarddesk.asia 站点指向 reverse_proxy bozhou-practice:8000，保留 request_body max_size 11MB。其他站点配置保持原样。验证配置再 reload，并检查容器内文件与宿主一致，避免此前单文件挂载内容不一致问题。
7. 验证公网 HTTPS、静态资源、登录和两台设备续刷。失败时恢复旧站点配置并 reload，旧容器和旧数据暂不删除。

不要直接运行原 compose.yaml 开启第二个80/443网关；不要执行 down -v。

## 本次本地检查

2026-10-13：12项API测试通过；前端TypeScript与生产构建通过。Radix客户端指令由Vite忽略，构建成功。生产镜像已在真实服务器构建并运行，healthcheck healthy；自动备份首次执行成功。
公网Edge浏览器验证管理员及普通用户登录、两独立上下文读取同一账号题库/会话/学习记录一致、刷新保持登录、角色隔离、Secure/HttpOnly Cookie，390px无横向溢出。截图在.scratch/deploy/live-admin.png和live-mobile.png。
浏览器验收用无代理模式，避免本机代理导致的网络超时。真实物理手机的网络体验由用户上线后确认。
Dockerfile生产安装排除pytest/mypy，不改本地开发依赖。首次构建受服务器PyPI下载速度影响，后续镜像层可复用。

迁移后的两份题库当前均为草稿，未代用户发布。普通人员开始新练习前，管理员需要在题库管理检查内容并确认发布。已有历史会话和学习记录已保留。

## 回退旧站点

旧刷题容器仍运行，可通过恢复网关路由切回。服务器执行：

```bash
cat /opt/network-workbench/deploy/Caddyfile.before-bozhou-20261013T144646Z > /opt/network-workbench/deploy/Caddyfile
docker exec network-workbench-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

回退不会迁移新系统上线后产生的记录到旧系统，两套数据库均保留。

## 2026-10-14版本更新

已更新至be9947d对应界面版本；本地12项测试与前端构建通过，服务器新镜像healthy。保留线上数据库及管理员配置，不覆盖成本机数据库。
代码、镜像与在线数据库快照备份完成：/root/bozhou-release-backups/20261014T005543Z；旧镜像bozhou-practice:before-20261014t005543z。
上线前后users/objects/audit内容校验一致（dbc3a3915bcd56938f38fff9b650f0f3781d2448f8af0dc61eb17e43d5e7e173），保留3账号、2题库、4会话和3学习对象。
公网验证管理员/普通用户登录、刷新会话、两端数据一致及已有练习显示、移动端无溢出、角色隔离；备份服务正常，工作台HTTP200。未更改网关配置。

## 2026-10-14 第二次更新（33cc56c）

已部署最新固定配色和布局版本；12项测试、前端构建、真实镜像健康检查及公网登录/手机刷题页面验收通过。
更新前后users/objects/audit内容SHA256一致：85abdbb4c05610c9c6a7ff6557cb582afac9054e5728f1ddb1c0f0c421530a95；保留3账号、2题库、6会话及3学习对象。
备份目录：/root/bozhou-release-backups/20261014T012346Z；回退镜像：bozhou-practice:before-20261014t012346z。
自动备份完成，工作台HTTP200；页面已使用index-CgNwFcve.js和index-DNvhU1rR.css。网关未修改，未覆盖线上数据库。

## 2026-10-14 9:47版本更新（dd2e718）

统一核对模式及简化操作版本已部署。13项API测试、前端构建、真实镜像健康检查及公网浏览器验收通过；验证统一核对入口和接口、两端数据一致及已有练习显示。
保留线上3账号、2题库、3学习对象及7会话，更新前后内容校验一致：e959c1839c5615d0b0c90d72ee5ddefbb2637ebf35f42f8a6c1504c9bf7ce95e。
备份目录/root/bozhou-release-backups/20261014T014840Z；回退镜像bozhou-practice:before-20261014t014840z。页面使用index-Cf05vzQN.js及index-sfcLAqOK.css，自动备份和工作台正常。
