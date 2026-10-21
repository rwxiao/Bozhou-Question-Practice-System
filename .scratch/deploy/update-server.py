import datetime
import os
import pathlib
import subprocess

def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

root = pathlib.Path('/opt/bozhou-practice')
os.chdir(root)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
folder = pathlib.Path('/root/bozhou-release-backups') / stamp
folder.mkdir(parents=True, mode=0o700)
old_image = subprocess.check_output(['docker', 'inspect', 'bozhou-practice-practice-1', '--format', '{{.Image}}'], text=True).strip()
rollback = 'bozhou-practice:before-' + stamp.lower()
run(['docker', 'tag', old_image, rollback])
run(['tar', '-czf', str(folder / 'source.tar.gz'), '-C', '/opt', 'bozhou-practice'])
(folder / 'source.tar.gz').chmod(0o600)
code = 'import sqlite3; s=sqlite3.connect("file:/data/practice.db?mode=ro",uri=True); d=sqlite3.connect("/snapshot/practice.db"); s.backup(d); assert d.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; d.close(); s.close()'
run(['docker', 'run', '--rm', '--user', '0', '--entrypoint', 'python', '-v', 'bozhou-practice_database:/data:ro', '-v', str(folder)+':/snapshot', old_image, '-c', code])
(folder / 'practice.db').chmod(0o600)
print('Source, image and online database backup:', folder, flush=True)
run(['tar', '-xzf', '/root/bozhou-practice-update-20261014.tar.gz', '-C', str(root)])
compose = ['docker', 'compose', '-f', 'compose.server.yaml']
run(compose + ['config', '--quiet'])
with open('/root/bozhou-practice-update-build.log', 'w') as log:
    run(compose + ['build', 'practice', 'backup'], stdout=log, stderr=subprocess.STDOUT)
try:
    run(compose + ['up', '-d', '--no-build', 'practice', 'backup'])
    run(['sh', '-c', 'for n in $(seq 1 40); do test "$(docker inspect bozhou-practice-practice-1 --format "{{.State.Health.Status}}")" = healthy && exit 0; sleep 3; done; exit 1'])
    run(['curl', '--fail', '--silent', '--show-error', 'https://quiz.onwarddesk.asia/'], stdout=subprocess.DEVNULL)
except Exception:
    run(['docker', 'tag', old_image, 'bozhou-practice:current'])
    run(compose + ['up', '-d', '--no-build', 'practice', 'backup'])
    raise
run(compose + ['ps'])
print('Update completed; rollback image:', rollback, flush=True)
