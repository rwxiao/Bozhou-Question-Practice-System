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


def test_admin_overview_is_separate_from_learner_access(system):
    admin, learner = TestClient(system.app), TestClient(system.app)
    login(admin)
    learner.post('/api/register', json={'username':'worker', 'password':'Worker-test-12345', 'role':'admin'})
    login(learner, 'worker', 'Worker-test-12345')
    assert learner.get('/api/me').json()['role'] == 'user'
    assert learner.get('/api/admin/summary').status_code == 403
    summary = admin.get('/api/admin/summary')
    assert summary.status_code == 200
    assert summary.json()['learners'] == 1


def test_login_role_choice_must_match_account(system):
    client = TestClient(system.app)
    client.post('/api/register', json={'username':'worker', 'password':'Worker-test-12345'})
    assert client.post('/api/login', json={'username':'worker', 'password':'Worker-test-12345', 'role':'admin'}).status_code == 403
    assert client.get('/api/me').status_code == 401
    assert client.post('/api/login', json={'username':'worker', 'password':'Worker-test-12345', 'role':'user'}).status_code == 200


def test_five_options_import_and_scoring(system):
    admin = TestClient(system.app)
    login(admin)
    bid = admin.post('/api/banks', json={'title':'五选项题库'}).json()['id']
    text = '编号,题型,题干,A,B,C,D,E,答案,解析,分类,标签\nF1,多选,选五项中的两项,一,二,三,四,五,A|E,解析,基础,测试\n'
    p = import_bank(admin, bid, text)
    assert p['errors'] == []
    admin.post(f"/api/imports/{p['id']}/commit")
    admin.post(f'/api/banks/{bid}/publish', json={'revision':1})
    s = admin.post('/api/sessions', json={'bank_id':bid,'amount':'20','mode':'顺序练习'}).json()
    assert s['questions'][0]['options']['E'] == '五'
    r = admin.post(f"/api/sessions/{s['id']}/answer", json={'revision':0,'index':0,'selected':['A','E']})
    assert r.json()['answers']['0']['correct'] is True


def test_bulk_and_all_delete_are_atomic_and_keep_history(system):
    admin, a, b, other, bid = setup_practice(system)
    old = a.post('/api/sessions', json={'bank_id':bid,'mode':'随机练习','amount':'全部'}).json()
    qs = admin.get('/api/banks').json()[0]['questions']
    url = f'/api/banks/{bid}/archive-batch'
    assert a.post(url, json={'revision':2,'all':True}).status_code == 403
    assert admin.post(url, json={'revision':2,'question_ids':[qs[0]['id'],'missing']}).status_code == 400
    assert admin.get('/api/banks').json()[0]['draft'] is None
    result = admin.post(url, json={'revision':2,'question_ids':[qs[0]['id'],qs[1]['id']]})
    assert result.status_code == 200 and result.json()['archived'] == 2
    assert a.get('/api/banks').json()[0]['count'] == 3
    assert admin.post(url, json={'revision':2,'all':True}).status_code == 409
    admin.post(f'/api/banks/{bid}/publish', json={'revision':3})
    assert a.get('/api/banks').json()[0]['count'] == 1
    result = admin.post(url, json={'revision':4,'all':True})
    assert result.json()['archived'] == 1
    admin.post(f'/api/banks/{bid}/publish', json={'revision':5})
    assert a.get('/api/banks').json()[0]['count'] == 0
    assert len(a.get(f"/api/sessions/{old['id']}").json()['questions']) == 3

def test_deferred_review_is_atomic_private_and_idempotent(system):
    admin, learner, other = TestClient(system.app), TestClient(system.app), TestClient(system.app)
    login(admin)
    for client, name in [(learner, 'learner'), (other, 'other')]:
        client.post('/api/register', json={'username': name, 'password': 'Learn-test-12345'})
        login(client, name, 'Learn-test-12345')
    bid = admin.post('/api/banks', json={'title': '核对测试'}).json()['id']
    preview = import_bank(admin, bid)
    admin.post(f"/api/imports/{preview['id']}/commit")
    admin.post(f'/api/banks/{bid}/publish', json={'revision': 1})
    session = learner.post('/api/sessions', json={'bank_id': bid, 'review_mode': 'deferred'}).json()
    url = f"/api/sessions/{session['id']}"
    assert all('answer' not in q for q in session['questions'])
    assert other.post(url+'/review', json={'revision': 0}).status_code == 404
    assert learner.post(url+'/review', json={'revision': 0}).status_code == 400
    assert learner.post(url+'/answer', json={'revision': 0, 'index': 0, 'selected': ['B']}).status_code == 400
    for i, selected in enumerate([['B'], ['A', 'C'], ['A']]):
        session = learner.patch(url, json={'revision': session['revision'], 'index': i, 'selected': selected}).json()
        assert session['answers'] == {}
        assert all('answer' not in q for q in session['questions'])
    assert learner.post(url+'/review', json={'revision': 0}).status_code == 409
    result = learner.post(url+'/review', json={'revision': session['revision']})
    assert result.status_code == 200
    result = result.json()
    assert result['ended'] and len(result['answers']) == 3
    assert sum(a['correct'] for a in result['answers'].values()) == 2
    assert all('answer' in q for q in result['questions'])
    assert learner.post(url+'/review', json={'revision': session['revision']}).json() == result
    assert learner.get('/api/learning').json()['total'] == 3


def test_directory_management_persistence_and_empty_deletion(system):
    admin = TestClient(system.app)
    login(admin)
    year = admin.post('/api/years', json={'name': '2026'} )
    assert year.status_code == 200, year.text
    year = year.json()
    project = admin.post('/api/projects', json={'name': '技能比赛', 'year_id': year['id']}).json()
    bank = admin.post('/api/banks', json={'title': '安全专业', 'project_id': project['id']}).json()
    assert bank['project_id'] == project['id']
    second = admin.post('/api/banks', json={'title': 'AI专业', 'project_id': project['id']}).json()
    assert second['id'] != bank['id']
    assert admin.patch('/api/years/' + year['id'], json={'name': '2027'}).json()['name'] == '2027'
    assert admin.patch('/api/projects/' + project['id'], json={'name': '网络比赛'}).json()['name'] == '网络比赛'
    system.initialize()
    assert admin.get('/api/directories').json() == {
        'years': [{'id': year['id'], 'name': '2027'}],
        'projects': [{'id': project['id'], 'name': '网络比赛', 'year_id': year['id']}]}
    assert admin.delete('/api/years/' + year['id']).status_code == 409
    assert admin.delete('/api/projects/' + project['id']).status_code == 409
    assert admin.patch('/api/banks/' + bank['id'], json={'revision': 0, 'status': 'offline'}).status_code == 200
    assert admin.delete('/api/projects/' + project['id']).status_code == 409
    empty = admin.post('/api/projects', json={'name': '空项目', 'year_id': year['id']}).json()
    assert admin.delete('/api/projects/' + empty['id']).status_code == 200
    empty_year = admin.post('/api/years', json={'name': '2028'}).json()
    assert admin.delete('/api/years/' + empty_year['id']).status_code == 200


def test_directory_permissions_and_invalid_ownership(system):
    admin, learner, _, _, bid = setup_practice(system)
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '比赛', 'year_id': year['id']}).json()
    for path, payload in [('/api/years', {'name': '2027'}),
                          ('/api/projects', {'name': '越权', 'year_id': year['id']})]:
        assert learner.post(path, json=payload).status_code == 403
    assert learner.get('/api/directories').status_code == 403
    for path in ['/api/years/' + year['id'], '/api/projects/' + project['id']]:
        assert learner.patch(path, json={'name': '越权'}).status_code == 403
        assert learner.delete(path).status_code == 403
    for value in [None, '', [], {}, 123, 'missing']:
        expected = 404 if value == 'missing' else 400
        assert admin.post('/api/projects', json={'name': '无效', 'year_id': value}).status_code == expected
        assert admin.post('/api/banks', json={'title': '无效', 'project_id': value}).status_code == expected
        assert admin.patch('/api/banks/' + bid, json={'revision': 2, 'project_id': value}).status_code == expected
    for name in ['', '   ', None, [], 'a' * 101]:
        assert admin.post('/api/years', json={'name': name}).status_code == 400
        assert admin.patch('/api/projects/' + project['id'], json={'name': name}).status_code == 400
    assert learner.patch('/api/banks/' + bid, json={'revision': 2, 'project_id': project['id']}).status_code == 403
    assert len(admin.get('/api/banks').json()) == 1
    assert admin.get('/api/banks').json()[0].get('project_id') is None


def test_moving_bank_preserves_questions_and_personal_records(system):
    admin, learner, _, _, bid = setup_practice(system)
    before = admin.get('/api/banks').json()[0]
    session = learner.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '全部'}).json()
    qid = session['questions'][0]['id']
    learner.post('/api/sessions/' + session['id'] + '/answer', json={'revision': 0, 'index': 0, 'selected': ['A']})
    learner.post('/api/favorite', json={'question_id': qid, 'value': True})
    learning = learner.get('/api/learning').json()
    for name in ['2026', '2027']:
        year = admin.post('/api/years', json={'name': name}).json()
        project = admin.post('/api/projects', json={'name': '比赛', 'year_id': year['id']}).json()
        current = admin.get('/api/banks').json()[0]
        moved = admin.patch('/api/banks/' + bid, json={'revision': current['revision'], 'project_id': project['id']})
        assert moved.status_code == 200
        assert moved.json()['id'] == bid and moved.json()['questions'] == before['questions']
        assert moved.json()['project_id'] == project['id']
    assert admin.patch('/api/banks/' + bid, json={'revision': 2, 'project_id': project['id']}).status_code == 409
    system.initialize()
    assert admin.get('/api/banks').json()[0]['project_id'] == project['id']
    assert learner.get('/api/learning').json() == learning
    resumed = learner.get('/api/sessions/' + session['id']).json()
    assert resumed['answers']['0']['correct'] is False
    assert resumed['questions'][0]['id'] == qid
    assert learner.post('/api/sessions/' + session['id'] + '/finish', json={'revision': resumed['revision']}).status_code == 200
