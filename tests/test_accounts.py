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
