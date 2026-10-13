-- 当前 SQLite 初始结构；应用启动时以相同定义创建。
-- objects.body 为版本化领域文档：bank/import/session/learning/report。
-- 会话包含固定题目版本快照，用户账号与登录索引保持独立。
CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT UNIQUE, nickname TEXT, hash TEXT, role TEXT, must_change INTEGER DEFAULT 0);
CREATE TABLE logins(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL);
CREATE TABLE objects(kind TEXT, id TEXT, owner TEXT, body TEXT NOT NULL, PRIMARY KEY(kind,id));
CREATE TABLE audit(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, target TEXT, at REAL);
CREATE TABLE attempts(key TEXT PRIMARY KEY, count INTEGER, start REAL);
-- 每次命令以 BEGIN IMMEDIATE 在同一事务内校验权限、版本并写入。
-- 数据库与备份包含用户资料，不放入版本库。增加未来结构时需编写兼容迁移。
