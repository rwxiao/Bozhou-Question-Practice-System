import sqlite3
from pathlib import Path

target = Path(__file__).with_name('practice-migration.db')
if target.exists():
    raise SystemExit('Snapshot already exists; not overwriting it.')
source = sqlite3.connect('file:data/practice.db?mode=ro', uri=True)
destination = sqlite3.connect(target)
try:
    source.backup(destination)
    destination.execute('DELETE FROM logins')
    destination.commit()
    assert destination.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    print('Migration snapshot ready; accounts:', destination.execute('SELECT count(*) FROM users').fetchone()[0])
    print('Banks:', destination.execute("SELECT count(*) FROM objects WHERE kind='bank'").fetchone()[0])
finally:
    destination.close()
    source.close()
