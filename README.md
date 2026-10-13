# 知序 · 通用在线刷题网站

管理员统一发布题库，学习者使用用户名和密码登录。支持手机与电脑续刷、CSV/XLSX 模板导入、单选/多选/判断、顺序/随机/错题/收藏练习，以及题目版本和个人学习记录。

## 本地启动（PowerShell）

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
$env:ADMIN_USERNAME = 'admin'
$taskAdminCredential = Read-Host '首位管理员密码（至少10字符）' -AsSecureString
$env:ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $taskAdminCredential).Password
.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 。首次启动创建管理员，后续不会用环境变量覆盖现有密码。关闭后可清除当前终端的 `ADMIN_PASSWORD` 环境变量。数据库默认在 `data/practice.db`，刷新或重启不会丢失记录。正式服务没有内置题库或默认密码。

## 导入与发布

管理员登录后新建题库，下载 CSV 或 Excel 模板。表头须完全一致：编号、题型、题干、A、B、C、D、答案、解析、分类、标签。解析、分类、标签可空；答案用 A–D，多选用 `A|C`，判断填“正确”或“错误”。题目编号在同一题库内唯一且稳定。CSV 使用 UTF-8，可含按 CSV 规则引用的逗号和换行；Excel 公式不接受。

全量校验后预览前10题并显示新增/更新数量，确认保存草稿，再确认发布。存在错误时整批不保存。重新导入不删除文件中缺少的旧题。编辑或归档题目也需发布，历史练习固定旧版本。

## 测试与检查

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m mypy app.py ops/backup.py --check-untyped-defs --ignore-missing-imports
node --check web/app.js
```

测试通过公开 API 和真实临时数据库验证行为；浏览器验收结果见项目验证记录。测试账号只存在于临时数据库。

## Docker 与 HTTPS

复制 `.env.example` 为 `.env`，设置实际域名、管理员用户名及随机强密码，域名 DNS 指向服务器，开放80/443端口，运行 `docker compose up -d --build`。Caddy 自动取得 HTTPS 证书；应用不直接暴露端口，生产 cookie 仅通过 HTTPS 发送。数据库与 Caddy 数据位于命名卷。备份容器启动后执行首次备份，以后每24小时备份一次，保留最近14份。上线前验证域名、证书、管理员登录与两台真实设备续刷。

本实现使用 SQLite，适用于单应用实例；不要横向扩展多个应用容器。定期将备份另存到服务器之外，并检查备份容器日志及磁盘空间。

## 备份和恢复

本地备份：`.venv/Scripts/python.exe ops/backup.py once`。备份使用 SQLite 在线备份接口并验证完整性，不直接复制运行中的数据库文件。

恢复前停止应用、额外备份当前库。指定 `DATABASE` 为目标后运行 `.venv/Scripts/python.exe ops/backup.py restore --file backups/<备份文件>.db`。恢复后所有账号重新登录，学习数据保留。

Docker 恢复：先 `docker compose stop app backup`，把备份保留在备份卷，执行 `docker compose run --rm --no-deps backup python ops/backup.py restore --file /backups/<备份文件>.db`，最后 `docker compose up -d app backup`。恢复完成后检查用户、题库、历史记录及统计。不要在运行中的应用上恢复。
