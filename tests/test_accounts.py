import time
import sqlite3

from fastapi.testclient import TestClient
from test_app import system, login, setup_practice


def test_registration_requires_name_and_lists_real_registration_time(system):
    admin, learner = TestClient(system.app), TestClient(system.app)
    login(admin)
    body = {'username': 'named_user', 'name': ' 张三 ', 'password': 'Learn-test-12345'}
    for invalid in [None, '', '   ', 123, '张' * 51]:
        assert learner.post('/api/register', json=body | {'name': invalid}).status_code == 400
    assert learner.post('/api/register', json={k: v for k, v in body.items() if k != 'name'}).status_code == 400
    before = time.time()
    assert learner.post('/api/register', json=body).status_code == 200
    account = login(learner, body['username'], body['password'])
    assert account['name'] == '张三'
    assert before <= account['created_at'] <= time.time()
    assert account['disabled'] == 0
    assert not {'hash', 'password'} & account.keys()
    assert account in admin.get('/api/users').json()
    assert learner.get('/api/users').status_code == 403
    assert TestClient(system.app).get('/api/users').status_code == 401
    assert learner.post('/api/register', json=body | {'username': 'NAMED_USER'}).status_code == 409
    assert learner.post('/api/register', json=body | {'username': 'weak_user', 'password': 'short'}).status_code == 400


def test_disable_revokes_all_sessions_without_deleting_learning_records(system):
    admin, learner, device, other, bid = setup_practice(system)
    account = learner.get('/api/me').json()
    path = f"/api/users/{account['id']}/disable"
    practice = learner.post('/api/sessions', json={'bank_id': bid}).json()
    sid, qid = practice['id'], practice['questions'][0]['id']
    assert learner.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 200
    assert learner.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).status_code == 200
    assert learner.get('/api/learning').json()['mistakes']
    assert len(learner.get('/api/sessions').json()) == 1
    with sqlite3.connect(system.DATABASE) as db:
        before = db.execute('SELECT kind,id,owner,body FROM objects WHERE owner=? ORDER BY kind,id', (account['id'],)).fetchall()
    assert other.post(path).status_code == 403
    assert learner.post(path).status_code == 403
    assert TestClient(system.app).post(path).status_code == 401
    assert admin.post('/api/users/missing/disable').status_code == 404
    assert admin.post(f"/api/users/{admin.get('/api/me').json()['id']}/disable").status_code == 400
    assert admin.post(path).status_code == 200
    assert admin.post(path).status_code == 200
    for client in [learner, device]:
        for url in ['/api/me', '/api/banks', '/api/learning', '/api/sessions', f'/api/sessions/{sid}']:
            assert client.get(url).status_code == 401
        assert client.post('/api/password', json={'old': 'Learn-test-12345', 'password': 'Changed-12345'}).status_code == 401
        assert client.post('/api/favorite', json={'question_id': qid, 'value': False}).status_code == 401
    assert learner.post('/api/login', json={'username': 'learner', 'password': 'Learn-test-12345'}).status_code == 403
    assert next(u for u in admin.get('/api/users').json() if u['id'] == account['id'])['disabled'] == 1
    # Storage inspection is necessary here: a disabled account has no public record-reading interface.
    with sqlite3.connect(system.DATABASE) as db:
        assert db.execute('SELECT kind,id,owner,body FROM objects WHERE owner=? ORDER BY kind,id', (account['id'],)).fetchall() == before


def test_old_accounts_keep_logins_and_records_with_unknown_registration_time(system):
    admin, learner, device, _, bid = setup_practice(system)
    account = learner.get('/api/me').json()
    practice = learner.post('/api/sessions', json={'bank_id': bid}).json()
    before = learner.get('/api/learning').json()
    # Recreate the pre-ticket schema, including an existing session and personal data.
    with sqlite3.connect(system.DATABASE) as db:
        for column in ['name', 'created_at', 'disabled']:
            db.execute(f'ALTER TABLE users DROP COLUMN {column}')
    system.initialize()
    system.initialize()
    old = learner.get('/api/me').json()
    assert old['id'] == account['id'] and old['nickname'] == account['nickname']
    assert old['name'] is None and old['created_at'] is None and old['disabled'] == 0
    assert learner.get('/api/learning').json() == before
    assert device.get(f"/api/sessions/{practice['id']}").json() == practice
    assert login(TestClient(system.app), 'learner', 'Learn-test-12345') == old
    assert old in admin.get('/api/users').json()


def test_delete_requires_admin_and_explicit_confirmation_and_revokes_sessions(system):
    admin, learner, device, other, bid = setup_practice(system)
    uid = learner.get('/api/me').json()['id']
    path = f'/api/users/{uid}'
    for client, status in [(learner, 403), (other, 403), (TestClient(system.app), 401)]:
        assert client.request('DELETE', path, json={'confirm': True}).status_code == status
    for body in [{}, {'confirm': False}, {'confirm': 'true'}]:
        assert admin.request('DELETE', path, json=body).status_code == 400
    aid = admin.get('/api/me').json()['id']
    assert admin.request('DELETE', f'/api/users/{aid}', json={'confirm': True}).status_code == 400
    assert admin.request('DELETE', path, json={'confirm': True}).status_code == 200
    assert admin.request('DELETE', path, json={'confirm': True}).status_code == 200
    assert uid not in [u['id'] for u in admin.get('/api/users').json()]
    for client in [learner, device]:
        for url in ['/api/me', '/api/learning', '/api/sessions', '/api/banks']:
            assert client.get(url).status_code == 401
    assert learner.post('/api/login', json={'username': 'learner', 'password': 'Learn-test-12345'}).status_code == 401
    assert other.get('/api/me').status_code == 200


def test_delete_cleans_personal_records_preserves_banks_others_and_anonymizes_reports(system):
    admin, learner, _, other, bid = setup_practice(system)
    uid = learner.get('/api/me').json()['id']
    for client in [learner, other]:
        practice = client.post('/api/sessions', json={'bank_id': bid}).json()
        sid, qid = practice['id'], practice['questions'][0]['id']
        assert client.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 200
        assert client.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).status_code == 200
        assert client.post('/api/reports', json={'session_id': sid, 'index': 0, 'type': '答案有误', 'text': '请检查答案'}).status_code == 200
        assert client.post(f'/api/sessions/{sid}/finish', json={'revision': 1}).status_code == 200
        assert client.post('/api/sessions', json={'bank_id': bid, 'restart': True}).status_code == 200
    banks = admin.get('/api/banks').json()
    other_state = {url: other.get(url).json() for url in ['/api/me', '/api/learning', '/api/sessions', '/api/reports']}
    reports = admin.get('/api/reports').json()
    assert admin.post(f'/api/users/{uid}/disable').status_code == 200
    assert admin.request('DELETE', f'/api/users/{uid}', json={'confirm': True}).status_code == 200
    assert admin.get('/api/banks').json() == banks
    for url, expected in other_state.items():
        assert other.get(url).json() == expected
    assert admin.get('/api/reports').json() == [r | {'user_id': None} if r['user_id'] == uid else r for r in reports]
    # Deleted data has no readable API; inspect persistence to distinguish deletion from access denial.
    with sqlite3.connect(system.DATABASE) as db:
        assert db.execute('SELECT COUNT(*) FROM objects WHERE owner=?', (uid,)).fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM logins WHERE user_id=?', (uid,)).fetchone()[0] == 0
    # Reusing a username must never recover the removed account's learning history.
    assert learner.post('/api/register', json={'username': 'learner', 'name': '新用户', 'password': 'Learn-test-12345'}).status_code == 200
    assert login(learner, 'learner', 'Learn-test-12345')['id'] != uid
    assert learner.get('/api/sessions').json() == []
    state = learner.get('/api/learning').json()
    assert state['favorites'] == [] and state['mistakes'] == {}
    assert learner.get('/api/reports').json() == []


def test_delete_failure_rolls_back_account_sessions_records_and_reports(system):
    admin, learner, device, other, bid = setup_practice(system)
    uid = learner.get('/api/me').json()['id']
    practice = learner.post('/api/sessions', json={'bank_id': bid}).json()
    assert learner.post('/api/favorite', json={'question_id': practice['questions'][0]['id'], 'value': True}).status_code == 200
    assert learner.post(f"/api/sessions/{practice['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['A']}).status_code == 200
    assert learner.post('/api/reports', json={'session_id': practice['id'], 'index': 0, 'type': '答案有误', 'text': '保留纠错'}).status_code == 200
    before = {url: learner.get(url).json() for url in ['/api/me', '/api/learning', '/api/sessions', '/api/reports']}
    reports = admin.get('/api/reports').json()
    # Force a real storage failure at the final write, after the preceding delete operations.
    with sqlite3.connect(system.DATABASE) as db:
        db.execute("CREATE TRIGGER reject_deletion BEFORE INSERT ON audit WHEN NEW.action='delete_user' BEGIN SELECT RAISE(ABORT, 'simulated storage failure'); END")
    failed_admin = TestClient(system.app, raise_server_exceptions=False)
    failed_admin.cookies.update(admin.cookies)
    assert failed_admin.request('DELETE', f'/api/users/{uid}', json={'confirm': True}).status_code == 500
    for url, expected in before.items():
        assert learner.get(url).json() == expected
    assert device.get('/api/me').status_code == 200
    assert admin.get('/api/reports').json() == reports
    with sqlite3.connect(system.DATABASE) as db:
        db.execute('DROP TRIGGER reject_deletion')
    assert admin.request('DELETE', f'/api/users/{uid}', json={'confirm': True}).status_code == 200
