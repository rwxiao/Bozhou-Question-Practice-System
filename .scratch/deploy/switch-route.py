import datetime
import pathlib
import subprocess

path = pathlib.Path('/opt/network-workbench/deploy/Caddyfile')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = path.with_name('Caddyfile.before-bozhou-' + stamp)
original = path.read_bytes()
old = b'reverse_proxy onwarddesk-quiz-static:8080'
new = b'reverse_proxy bozhou-practice:8000'
assert original.count(old) == 1, 'Expected exactly one old quiz route'
candidate = original.replace(old, new)
candidate = candidate.replace(b'quiz.onwarddesk.asia {', b'quiz.onwarddesk.asia {\n    request_body {\n        max_size 11MB\n    }', 1)
backup.write_bytes(original)
container = 'network-workbench-caddy-1'
subprocess.run(['docker', 'exec', '-i', container, 'caddy', 'validate', '--config', '/dev/stdin', '--adapter', 'caddyfile'], input=candidate, check=True)
try:
    path.write_bytes(candidate)
    mounted = subprocess.check_output(['docker', 'exec', container, 'cat', '/etc/caddy/Caddyfile'])
    assert mounted == candidate, 'Gateway mount differs from host file'
    subprocess.run(['docker', 'exec', container, 'caddy', 'reload', '--config', '/etc/caddy/Caddyfile', '--adapter', 'caddyfile'], check=True)
    subprocess.run(['curl', '--fail', '--silent', '--show-error', '--resolve', 'quiz.onwarddesk.asia:443:127.0.0.1', 'https://quiz.onwarddesk.asia/'], stdout=subprocess.DEVNULL, check=True)
except Exception:
    path.write_bytes(original)
    subprocess.run(['docker', 'exec', container, 'caddy', 'reload', '--config', '/etc/caddy/Caddyfile', '--adapter', 'caddyfile'], check=True)
    raise
print('Quiz route switched; backup:', backup)
