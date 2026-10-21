import hashlib
import json
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else '/data/practice.db')
assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
content = {table: db.execute(query).fetchall() for table, query in {
    'users': 'SELECT * FROM users ORDER BY id',
    'objects': 'SELECT * FROM objects ORDER BY kind,id',
    'audit': 'SELECT * FROM audit ORDER BY id',
}.items()}
digest = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
print(json.dumps({'integrity': 'ok', 'accounts': len(content['users']), 'object_counts': db.execute('SELECT kind,count(*) FROM objects GROUP BY kind ORDER BY kind').fetchall(), 'content_sha256': digest}))
db.close()
