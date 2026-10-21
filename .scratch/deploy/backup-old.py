import datetime
import pathlib
import subprocess

folder = pathlib.Path('/root/quiz-migration-backups')
folder.mkdir(mode=0o700, exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
name = 'old-quiz-' + stamp + '.sqlite'
code = 'import sqlite3; s=sqlite3.connect("file:/old/quiz.sqlite?mode=ro",uri=True); d=sqlite3.connect("/backups/' + name + '"); s.backup(d); assert d.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; d.close(); s.close()'
subprocess.run(['docker', 'run', '--rm', '--user', '0', '--entrypoint', 'python', '-v', 'onwarddesk-quiz_quiz_data:/old:ro', '-v', str(folder)+':/backups', 'bozhou-practice:current', '-c', code], check=True)
(folder / name).chmod(0o600)
print('Old quiz online backup verified:', folder / name)
