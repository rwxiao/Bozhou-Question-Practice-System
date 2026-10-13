import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def system(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE', str(tmp_path / 'test.db'))
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'Admin-test-12345')
    import app
    importlib.reload(app)
    app.initialize()
    return app


def login(client, username='admin', password='Admin-test-12345'):
    response = client.post('/api/login', json={'username': username, 'password': password})
    assert response.status_code == 200, response.text
    return response.json()


def test_register_permissions_and_password_reset(system):
    admin, user = TestClient(system.app), TestClient(system.app)
    login(admin)
    assert user.post('/api/register', json={'username': 'learner', 'password': 'Learn-test-12345', 'nickname': '学习者'}).status_code == 200
    login(user, 'learner', 'Learn-test-12345')
    assert user.post('/api/banks', json={'title': '非法题库'}).status_code == 403
    uid = user.get('/api/me').json()['id']
    assert admin.post(f'/api/users/{uid}/reset', json={'password': 'Temporary-12345'}).status_code == 200
    assert user.get('/api/me').status_code == 401
    login(user, 'learner', 'Temporary-12345')
    assert user.get('/api/banks').status_code == 403
    assert user.post('/api/password', json={'old': 'Temporary-12345', 'password': 'Changed-12345'}).status_code == 200
    assert user.get('/api/banks').status_code == 200


SAMPLE = '编号,题型,题干,A,B,C,D,答案,解析,分类,标签\nQ1,单选,一加一？,一,二,三,,B,加法,基础,数学\nQ2,多选,偶数？,二,三,四,,A|C,偶数,基础,数学\nQ3,判断,地球是平的？,,,,,错误,地球,地理,常识\n'


def import_bank(admin, bid, text=SAMPLE):
    p = admin.post(f'/api/banks/{bid}/preview', files={'file': ('bank.csv', text.encode('utf-8-sig'), 'text/csv')})
    assert p.status_code == 200, p.text
    return p.json()


def test_import_is_atomic_and_drafts_are_private(system):
    admin, user = TestClient(system.app), TestClient(system.app)
    login(admin)
    user.post('/api/register', json={'username': 'learner', 'password': 'Learn-test-12345'})
    login(user, 'learner', 'Learn-test-12345')
    bank = admin.post('/api/banks', json={'title': '基础题库'}).json()
    bad = import_bank(admin, bank['id'], SAMPLE.replace('Q2,多选', 'Q1,多选'))
    assert bad['errors'][0]['row'] == 3
    assert admin.get('/api/banks').json()[0]['draft'] is None
    p = import_bank(admin, bank['id'])
    assert p['added'] == 3 and p['updated'] == 0
    assert admin.post(f"/api/imports/{p['id']}/commit").status_code == 200
    assert user.get('/api/banks').json() == []
    assert admin.post(f"/api/imports/{p['id']}/commit").status_code == 200
    assert admin.post(f"/api/banks/{bank['id']}/publish", json={'revision': 1}).status_code == 200
    visible = user.get('/api/banks').json()[0]
    assert visible['count'] == 3
    assert 'questions' not in visible and 'draft' not in visible


def test_xlsx_template_import_and_preview_conflict(system):
    admin = TestClient(system.app)
    login(admin)
    bid = admin.post('/api/banks', json={'title': '模板题库'}).json()['id']
    template = admin.get('/api/template.xlsx').content
    p = admin.post(f'/api/banks/{bid}/preview', files={'file': ('template.xlsx', template)}).json()
    assert not p['errors'] and p['added'] == 3
    other = import_bank(admin, bid)
    assert admin.post(f"/api/imports/{other['id']}/commit").status_code == 200
    assert admin.post(f"/api/imports/{p['id']}/commit").status_code == 409


def setup_practice(system):
    admin, a, b, other = [TestClient(system.app) for _ in range(4)]
    login(admin)
    a.post('/api/register', json={'username': 'learner', 'password': 'Learn-test-12345'})
    other.post('/api/register', json={'username': 'other', 'password': 'Other-test-12345'})
    login(a, 'learner', 'Learn-test-12345')
    login(b, 'learner', 'Learn-test-12345')
    login(other, 'other', 'Other-test-12345')
    bid = admin.post('/api/banks', json={'title': '基础'}).json()['id']
    p = import_bank(admin, bid)
    admin.post(f"/api/imports/{p['id']}/commit")
    admin.post(f'/api/banks/{bid}/publish', json={'revision': 1})
    return admin, a, b, other, bid


def test_cross_device_draft_conflict_scoring_and_isolation(system):
    admin, a, b, other, bid = setup_practice(system)
    session = a.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '20'}).json()
    sid = session['id']
    assert len(session['questions']) == 3 and 'answer' not in session['questions'][0]
    assert other.get(f'/api/sessions/{sid}').status_code == 404
    assert a.patch(f'/api/sessions/{sid}', json={'revision': 0, 'index': 0, 'selected': ['B']}).status_code == 200
    fresh = b.get(f'/api/sessions/{sid}').json()
    assert fresh['drafts']['0'] == ['B']
    assert b.patch(f'/api/sessions/{sid}', json={'revision': 0, 'index': 1, 'selected': []}).status_code == 409
    answer = {'revision': 1, 'index': 0, 'selected': ['B']}
    assert b.post(f'/api/sessions/{sid}/answer', json=answer).json()['answers']['0']['correct'] is True
    assert b.post(f'/api/sessions/{sid}/answer', json=answer).status_code == 200
    assert a.get('/api/learning').json()['total'] == 1
    assert other.get('/api/learning').json()['total'] == 0
    assert a.post(f'/api/sessions/{sid}/finish', json={'revision': 2}).status_code == 200
    assert a.get('/api/learning').json()['total'] == 1


def test_versions_mistakes_favorites_and_offline_bank(system):
    admin, a, b, other, bid = setup_practice(system)
    s = a.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '10'}).json()
    sid, qid = s['id'], s['questions'][0]['id']
    assert a.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).status_code == 200
    assert a.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 200
    assert a.post('/api/mastered', json={'question_id': qid, 'value': True}).status_code == 200
    p = import_bank(admin, bid, SAMPLE.replace(',B,加法', ',A,加法'))
    admin.post(f"/api/imports/{p['id']}/commit")
    assert admin.post(f'/api/banks/{bid}/publish', json={'revision': 3}).status_code == 200
    assert a.get('/api/learning').json()['mistakes'][qid]['mastered'] is False
    old = a.get(f'/api/sessions/{sid}').json()
    assert old['questions'][0]['answer'] == ['B']
    fresh = a.post('/api/sessions', json={'bank_id': bid, 'mode': '收藏练习', 'amount': '20'}).json()
    assert len(fresh['questions']) == 1
    assert a.post(f"/api/sessions/{fresh['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['A']}).json()['answers']['0']['correct'] is True
    assert admin.patch(f'/api/banks/{bid}', json={'revision': 4, 'status': 'offline'}).status_code == 200
    assert a.post('/api/sessions', json={'bank_id': bid, 'mode': '随机练习', 'amount': '20'}).status_code == 400
    assert a.get(f'/api/sessions/{sid}').status_code == 200


def test_modes_scoring_reports_and_csrf(system):
    admin, a, b, other, bid = setup_practice(system)
    for amount in ('10', '20', '50', '全部'):
        r = a.post('/api/sessions', json={'bank_id': bid, 'mode': '随机练习', 'amount': amount})
        assert r.status_code == 200
        qs = r.json()['questions']
        assert len(qs) == 3 and len({q['id'] for q in qs}) == 3
    assert a.post('/api/sessions', json={'bank_id': bid, 'mode': '错题练习', 'amount': '20'}).status_code == 400
    s = a.post('/api/sessions', json={'bank_id': bid, 'category': '基础', 'mode': '顺序练习', 'amount': '20'}).json()
    sid = s['id']
    assert len(s['questions']) == 2
    response = a.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 1, 'selected': ['C', 'A']})
    assert response.json()['answers']['1']['correct'] is True
    assert 'answer' not in response.json()['questions'][0]
    r = a.post('/api/reports', json={'session_id': sid, 'index': 1, 'type': '解析有误', 'text': '请补充解析'})
    assert r.status_code == 200
    rid = admin.get('/api/reports').json()[0]['id']
    assert other.get('/api/reports').json() == []
    assert admin.patch(f'/api/reports/{rid}', json={'status': '已处理'}).status_code == 200
    assert a.get('/api/reports').json()[0]['status'] == '已处理'
    assert a.post('/api/favorite', json={'question_id': s['questions'][0]['id'], 'value': True}, headers={'Origin': 'https://attacker.example'}).status_code == 403


def test_backup_restore_retains_learning_but_revokes_logins(system, tmp_path):
    from ops.backup import backup, restore
    admin, a, b, other, bid = setup_practice(system)
    s = a.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '20'}).json()
    a.post(f"/api/sessions/{s['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['B']})
    saved = backup(system.DATABASE, tmp_path / 'backups')
    target = tmp_path / 'restored.db'
    restore(saved, str(target))
    system.DATABASE = str(target)
    assert a.get('/api/me').status_code == 401
    login(a, 'learner', 'Learn-test-12345')
    assert a.get('/api/learning').json()['total'] == 1
    assert a.get('/api/banks').json()[0]['count'] == 3
    assert a.get(f"/api/sessions/{s['id']}").json()['answers']['0']['correct'] is True


def test_update_preserves_missing_questions_and_archive_is_a_draft(system):
    admin, a, b, other, bid = setup_practice(system)
    bank = admin.get('/api/banks').json()[0]
    qid = bank['questions'][0]['id']
    assert admin.post(f'/api/banks/{bid}/archive', json={'revision': 2, 'question_id': qid}).status_code == 200
    assert a.get('/api/banks').json()[0]['count'] == 3
    assert admin.post(f'/api/banks/{bid}/publish', json={'revision': 3}).status_code == 200
    assert a.get('/api/banks').json()[0]['count'] == 2
    partial = '\n'.join(SAMPLE.splitlines()[:2]) + '\n'
    p = import_bank(admin, bid, partial)
    assert p['updated'] == 1 and p['added'] == 0
    admin.post(f"/api/imports/{p['id']}/commit")
    assert admin.post(f'/api/banks/{bid}/publish', json={'revision': 5}).status_code == 200
    assert a.get('/api/banks').json()[0]['count'] == 3
