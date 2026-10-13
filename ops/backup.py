"""SQLite online backup and offline restore. Restore only with the app stopped."""
import argparse
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path


def backup(database, directory):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.db')
    with sqlite3.connect(database) as source, sqlite3.connect(target) as dest:
        source.backup(dest)
        if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('备份完整性检查失败')
    for path in sorted(directory.glob('*.db'))[:-14]:
        path.unlink()
    return target


def restore(source, database):
    if not source.is_file():
        raise ValueError('备份文件不存在')
    with sqlite3.connect(source) as src:
        if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('备份损坏')
        if not src.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone():
            raise ValueError('不是刷题网站数据库')
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database) as dst:
            src.backup(dst)
            dst.execute('DELETE FROM logins')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['once', 'daily', 'restore'])
    parser.add_argument('--file')
    args = parser.parse_args()
    database = os.getenv('DATABASE', 'data/practice.db')
    directory = Path(os.getenv('BACKUP_DIR', 'backups'))
    if args.action == 'restore':
        if not args.file:
            parser.error('restore 需要 --file；先停止应用并备份现有数据库')
        restore(Path(args.file), database)
    else:
        while True:
            if Path(database).exists():
                print(backup(database, directory), flush=True)
            if args.action == 'once':
                break
            time.sleep(86400)
