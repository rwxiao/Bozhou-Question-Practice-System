# 05：旧题库待整理与安全迁移

日期：2026-10-21。用户已确认待整理题库禁止新建练习、允许继续已有练习，以及公开 API、浏览器与迁移数据核对边界。本次仅使用隔离测试数据，未操作生产数据或部署。

## 迁移方式

现有 JSON 对象存储中，没有 `project_id` 的题库直接被解释为待整理；无需一次性重写脚本、迁移标记或复制对象。重复启动不会创建目录、猜测年份或改变题库状态。已整理题库保留原归属，管理员分配沿用事务和 revision 冲突检查。历史会话无项目字段时沿用当前题库归属的兼容展示，有项目快照时仍保留快照。

## API 与数据核对

`tests/test_legacy_migration.py` 构造代表性目录改造前数据：2 个旧题库（已发布、草稿）、每库 3 道题、进行中与已结束会话、错题、收藏及顺序游标；去除旧版本不存在的项目字段。检查启动两次前后的全部对象键、owner、JSON 原文及用户行完全相同，管理员仍能看到原题库，普通用户看不到待整理题库。

覆盖四种练习方式禁止新建、管理员与普通用户分配权限、版本冲突、分配保持题库和题目 ID／草稿／生效状态、旧会话继续保存作答和结束、跨客户端进度、历史数量、错题收藏和用户隔离。已整理后再启动仍保留归属，旧快照不改写。原有练习测试使用明确分配的目录，目录权限测试保留未分配样本。

备份恢复测试对 SQLite 在线备份及独立目标库恢复执行完整性检查，逐行比对全部对象及用户数据，恢复后登录并通过 API 核对练习快照和个人记录。登录令牌按既有恢复工具设计清除。

## 备份与恢复演练办法

实施真实数据迁移前先保存当前版本和数据库备份；此处命令只示范隔离演练库，不代表授权生产操作。

```powershell
$env:DATABASE = 'data/migration-rehearsal.db'
$env:BACKUP_DIR = 'backups/migration-rehearsal'
.venv/Scripts/python.exe ops/backup.py once
```

保存命令打印的备份路径及备份副本（现有工具只保留最近 14 份）。服务停止后，将该备份恢复到全新演练目标，避免覆盖正在运行的数据库：

```powershell
$env:DATABASE = 'data/migration-restored.db'
.venv/Scripts/python.exe ops/backup.py restore --file 'backups/migration-rehearsal/实际备份文件.db'
```

迁移前后及恢复后运行 SQLite `PRAGMA integrity_check`；按 kind 统计 objects 数量、核对 `(kind,id,owner)` 集合，逐题核对题目 ID，逐会话核对 bank_id、题目快照、answers、drafts、index、revision、ended，核对 learning 中 favorites、mistakes、cursors 及用户行。自动测试还比较未编辑对象的 JSON 原文。分配本身只允许对应 bank 的 project_id 和 revision 变化；人工新建年份／项目会按操作增加目录对象。登录令牌清理是恢复的预期差异。恢复演练重新登录，验证继续练习、历史、错题与收藏，再讨论实际迁移窗口。

## 浏览器与前端

脚本 `docs/legacy-migration-browser.py` 使用隔离服务 `127.0.0.1:8770` 和无头 Edge。桌面 1440×1000 从待整理入口找到旧题库并分配；手机 390×844 分配草稿，验证刷新持久化、草稿仍私有、用户目录仅出现已分配的已发布题库，以及页面没有文档横向溢出。截图位于 `docs/screenshots/legacy-migration/`，已人工查看。复用既有管理界面，无需新增页面。

前端 typecheck、生产 build、Python mypy、git diff --check 均通过；全套 pytest 为 31 passed。保留既有第三方 use client／sourcemap 提示及 AnyIO 弃用警告。最终浏览器隔离库为 `data/legacy-migration-final-20261021.db`。

## Standards

独立审查 0 项发现。任务范围内未发现违反仓库文档规范或需要处理的基线代码异味；共享可用性判定集中于 `bank_available`，目录与学习记录沿用既有接口和术语。已排除工作区原有无关变更。

## Spec

独立审查 0 项发现。实现符合第 05 项及用户补充确认：未分配题库仅管理员可管理，禁止四种方式新建练习，保留已有会话与个人记录；分配归属不会发布草稿或改写稳定标识、题目和快照。已补充重启幂等、权限、迁移数据核对、隔离备份恢复及桌面／手机分配验收，无范围外行为。

两轴各 0 项发现。起点 `4952fa3b4e494154a9bfacd39265a8c2f4202e98`；原有 Dockerfile、部署配置、其他任务／规格草案、GLOSSARY 等工作区内容未纳入本次提交。
