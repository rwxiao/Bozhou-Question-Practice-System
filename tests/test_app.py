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


def assigned_bank(admin, title):
    year = admin.post('/api/years', json={'name': '练习年份'}).json()
    project = admin.post('/api/projects', json={'name': '练习项目', 'year_id': year['id']}).json()
    return admin.post('/api/banks', json={'title': title, 'project_id': project['id']}).json()


def import_bank(admin, bid, text=SAMPLE):
    p = admin.post(f'/api/banks/{bid}/preview', files={'file': ('bank.csv', text.encode('utf-8-sig'), 'text/csv')})
    assert p.status_code == 200, p.text
    return p.json()


def test_import_is_atomic_and_drafts_are_private(system):
    admin, user = TestClient(system.app), TestClient(system.app)
    login(admin)
    user.post('/api/register', json={'username': 'learner', 'password': 'Learn-test-12345'})
    login(user, 'learner', 'Learn-test-12345')
    bank = assigned_bank(admin, '基础题库')
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


def setup_practice(system, assigned=True):
    admin, a, b, other = [TestClient(system.app) for _ in range(4)]
    login(admin)
    a.post('/api/register', json={'username': 'learner', 'password': 'Learn-test-12345'})
    other.post('/api/register', json={'username': 'other', 'password': 'Other-test-12345'})
    login(a, 'learner', 'Learn-test-12345')
    login(b, 'learner', 'Learn-test-12345')
    login(other, 'other', 'Other-test-12345')
    bid = (assigned_bank(admin, '基础') if assigned else admin.post('/api/banks', json={'title': '基础'}).json())['id']
    p = import_bank(admin, bid)
    admin.post(f"/api/imports/{p['id']}/commit")
    admin.post(f'/api/banks/{bid}/publish', json={'revision': 1})
    return admin, a, b, other, bid


def test_bank_archive_preserves_practice_and_learning(system):
    admin, learner, _, other, bid = setup_practice(system)
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '技能比赛', 'year_id': year['id']}).json()
    bank = admin.patch(f'/api/banks/{bid}', json={'revision': 2, 'project_id': project['id']}).json()
    session = learner.post('/api/sessions', json={'bank_id': bid}).json()
    sid = session['id']
    qid = session['questions'][0]['id']
    assert learner.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 200
    answered = learner.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).json()
    before = learner.get('/api/learning').json()
    assert learner.patch(f'/api/banks/{bid}', json={'revision': bank['revision'], 'status': 'archived'}).status_code == 403
    archived = admin.patch(f'/api/banks/{bid}', json={'revision': bank['revision'], 'status': 'archived'})
    assert archived.status_code == 200, archived.text
    assert archived.json()['status'] == 'archived'
    assert archived.json()['questions'] == bank['questions']
    assert admin.patch(f'/api/banks/{bid}', json={'revision': bank['revision'], 'status': 'archived'}).status_code == 409
    assert learner.get('/api/banks').json() == []
    assert learner.get('/api/learning/directories').json() == {'years': [], 'projects': []}
    for mode in ['顺序练习', '随机练习', '错题练习', '收藏练习']:
        response = learner.post('/api/sessions', json={'bank_id': bid, 'mode': mode, 'restart': True})
        assert response.status_code == 400
        assert '归档' in response.json()['detail']
    assert len(learner.get('/api/sessions').json()) == 1
    assert learner.get(f'/api/sessions/{sid}').json() == answered
    continued = learner.post(f'/api/sessions/{sid}/answer', json={'revision': answered['revision'], 'index': 1, 'selected': ['A', 'C']})
    assert continued.status_code == 200
    finished = learner.post(f'/api/sessions/{sid}/finish', json={'revision': continued.json()['revision']}).json()
    assert finished['ended'] and len(finished['answers']) == 2
    history = learner.get('/api/sessions').json()[0]
    assert history['project']['name'] == '技能比赛'
    assert history['project']['year_name'] == '2026'
    after = learner.get('/api/learning').json()
    assert after['mistakes'] == before['mistakes'] and after['favorites'] == before['favorites']
    assert after['total'] == 2 and after['correct'] == 1
    assert after['records'][0]['question']['stem'] == '一加一？'
    assert after['records'][0]['question']['answer'] == ['B']
    assert after['records'][0]['project']['name'] == '技能比赛'
    assert other.get('/api/learning').json()['records'] == []
    assert admin.delete('/api/projects/' + project['id']).status_code == 409
    assert admin.delete('/api/years/' + year['id']).status_code == 409
    assert admin.delete(f'/api/banks/{bid}').status_code == 405


def test_hidden_project_keeps_banks_and_history_available(system):
    admin, learner, _, _, bid = setup_practice(system)
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '年度考试', 'year_id': year['id']}).json()
    admin.patch(f'/api/banks/{bid}', json={'revision': 2, 'project_id': project['id']})
    original = learner.post('/api/sessions', json={'bank_id': bid}).json()
    for value in ['true', 1, None]:
        assert admin.patch('/api/projects/' + project['id'], json={'hidden': value}).status_code == 400
    assert learner.patch('/api/projects/' + project['id'], json={'hidden': True}).status_code == 403
    hidden = admin.patch('/api/projects/' + project['id'], json={'hidden': True})
    assert hidden.status_code == 200, hidden.text
    assert hidden.json() == project | {'hidden': True}
    assert learner.get('/api/learning/directories').json()['projects'] == [project | {'hidden': True}]
    assert len(learner.get('/api/banks').json()) == 1
    assert learner.post('/api/sessions', json={'bank_id': bid, 'mode': '随机练习'}).status_code == 200
    assert learner.get('/api/sessions/' + original['id']).json() == original
    renamed = admin.patch('/api/projects/' + project['id'], json={'name': '已结束考试'}).json()
    assert renamed['hidden'] is True
    assert learner.get('/api/sessions').json()[1]['project']['name'] == '年度考试'
    assert admin.delete('/api/projects/' + project['id']).status_code == 409
    assert admin.patch('/api/projects/' + project['id'], json={'hidden': False}).json()['hidden'] is False


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
    bid = assigned_bank(admin, '五选项题库')['id']
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
    bid = assigned_bank(admin, '核对测试')['id']
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
    admin, learner, _, _, bid = setup_practice(system, assigned=False)
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


def test_learner_directory_filters_and_bank_categories(system):
    admin, learner, _, _, legacy = setup_practice(system, assigned=False)
    assert TestClient(system.app).get('/api/learning/directories').status_code == 401
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '能力考试', 'year_id': year['id']}).json()
    private = admin.post('/api/projects', json={'name': '未发布项目', 'year_id': year['id']}).json()
    admin.post('/api/banks', json={'title': '私有草稿', 'project_id': private['id']})
    bank = admin.post('/api/banks', json={'title': '安全', 'project_id': project['id']}).json()
    preview = import_bank(admin, bank['id'], SAMPLE.replace('基础', '安全'))
    assert admin.post(f"/api/imports/{preview['id']}/commit").status_code == 200
    assert admin.post(f"/api/banks/{bank['id']}/publish", json={'revision': 1}).status_code == 200
    assert learner.get('/api/learning/directories').json() == {'years': [year], 'projects': [project]}
    visible = {b['id']: b for b in learner.get('/api/banks').json()}
    assert visible[bank['id']]['project_id'] == project['id']
    assert visible[bank['id']]['categories'] == ['地理', '安全']
    assert legacy not in visible
    assert 'questions' not in visible[bank['id']]
    moved_year = admin.post('/api/years', json={'name': '2027'}).json()
    moved_project = admin.post('/api/projects', json={'name': '比赛', 'year_id': moved_year['id']}).json()
    assert admin.patch(f"/api/banks/{bank['id']}", json={'revision': 2, 'project_id': moved_project['id']}).status_code == 200
    assert learner.get('/api/learning/directories').json() == {'years': [moved_year], 'projects': [moved_project]}


def test_learner_modes_category_scope_and_personal_records(system):
    admin, learner, device, other, first = setup_practice(system)
    second = assigned_bank(admin, '同名分类另一题库')['id']
    p = import_bank(admin, second)
    admin.post(f"/api/imports/{p['id']}/commit")
    admin.post(f'/api/banks/{second}/publish', json={'revision': 1})
    for bid in [first, second]:
        for mode in ['顺序练习', '随机练习']:
            s = learner.post('/api/sessions', json={'bank_id': bid, 'category': '基础', 'mode': mode, 'amount': '全部'}).json()
            assert len(s['questions']) == 2
            assert all(q['id'].startswith(bid + ':') and q['category'] == '基础' for q in s['questions'])
    s = learner.post('/api/sessions', json={'bank_id': first, 'amount': '全部'}).json()
    sid, qid = s['id'], s['questions'][0]['id']
    assert learner.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).status_code == 200
    assert learner.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 200
    for mode in ['错题练习', '收藏练习']:
        result = learner.post('/api/sessions', json={'bank_id': first, 'category': '基础', 'mode': mode}).json()
        assert [q['id'] for q in result['questions']] == [qid]
        for client, bid, category in [(other, first, '基础'), (learner, second, '基础'), (learner, first, '地理')]:
            before = client.get('/api/sessions').json()
            assert client.post('/api/sessions', json={'bank_id': bid, 'category': category, 'mode': mode}).status_code == 400
            assert client.get('/api/sessions').json() == before
    assert device.get(f'/api/sessions/{sid}').json()['answers']['0']['correct'] is False
    assert other.get(f'/api/sessions/{sid}').status_code == 404
    assert other.get('/api/learning').json()['favorites'] == []
    assert other.get('/api/learning').json()['mistakes'] == {}
    before = learner.get('/api/sessions').json()
    assert learner.post('/api/sessions', json={'bank_id': first, 'category': '不存在'}).status_code == 400
    assert learner.get('/api/sessions').json() == before


def test_uncategorized_and_empty_bank_do_not_create_invalid_session(system):
    admin, learner, _, _, bid = setup_practice(system)
    p = import_bank(admin, bid, SAMPLE.replace('基础', '').replace('地理', ''))
    admin.post(f"/api/imports/{p['id']}/commit")
    admin.post(f'/api/banks/{bid}/publish', json={'revision': 3})
    assert learner.get('/api/banks').json()[0]['categories'] == []
    assert len(learner.post('/api/sessions', json={'bank_id': bid, 'amount': '全部'}).json()['questions']) == 3
    bank = admin.get('/api/banks').json()[0]
    assert admin.post(f'/api/banks/{bid}/archive-batch', json={'revision': bank['revision'], 'all': True}).status_code == 200
    assert admin.post(f'/api/banks/{bid}/publish', json={'revision': bank['revision'] + 1}).status_code == 200
    assert learner.get('/api/banks').json()[0]['count'] == 0
    before = learner.get('/api/sessions').json()
    for mode in ['顺序练习', '随机练习', '错题练习', '收藏练习']:
        result = learner.post('/api/sessions', json={'bank_id': bid, 'mode': mode})
        assert result.status_code == 400 and '没有可练习题目' in result.json()['detail']
    assert learner.get('/api/sessions').json() == before


@pytest.mark.parametrize('format', ['csv', 'xlsx'])
def test_import_can_publish_directly_or_save_draft(system, format):
    admin, learner, _, _, bid = setup_practice(system)
    before = learner.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '20'}).json()
    template = admin.get('/api/template.' + format)
    assert template.status_code == 200
    preview = admin.post(f'/api/banks/{bid}/preview', files={'file': ('bank.' + format, template.content)}).json()
    assert not preview['errors']
    assert (preview['added'], preview['updated']) == (0, 3)
    result = admin.post(f"/api/imports/{preview['id']}/commit", json={'publish': True})
    assert result.status_code == 200, result.text
    bank = next(b for b in admin.get('/api/banks').json() if b['id'] == bid)
    assert bank['status'] == 'published' and bank['draft'] is None
    assert bank['questions'][0]['stem'] == '一加一等于？'
    assert learner.get('/api/sessions/' + before['id']).json() == before
    revision = bank['revision']
    assert admin.post(f"/api/imports/{preview['id']}/commit", json={'publish': True}).status_code == 200
    assert next(b for b in admin.get('/api/banks').json() if b['id'] == bid)['revision'] == revision
    assert admin.post(f"/api/imports/{preview['id']}/commit", json={'publish': False}).status_code == 409
    draft = import_bank(admin, bid, SAMPLE)
    assert admin.post(f"/api/imports/{draft['id']}/commit", json={'publish': False}).status_code == 200
    bank = next(b for b in admin.get('/api/banks').json() if b['id'] == bid)
    assert bank['questions'][0]['stem'] == '一加一等于？'
    assert bank['draft'][0]['stem'] == '一加一？'
    assert admin.post(f'/api/banks/{bid}/publish', json={'revision': bank['revision']}).status_code == 200


@pytest.mark.parametrize('format', ['csv', 'xlsx'])
@pytest.mark.parametrize('publish_now', [False, True])
def test_new_bank_import_paths_and_permissions(system, format, publish_now):
    admin, learner, _, _, _ = setup_practice(system)
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '比赛', 'year_id': year['id']}).json()
    bank = admin.post('/api/banks', json={'title': '新题库', 'project_id': project['id']}).json()
    template = admin.get('/api/template.' + format).content
    path = f"/api/banks/{bank['id']}/preview"
    assert learner.post(path, files={'file': ('bank.' + format, template)}).status_code == 403
    preview = admin.post(path, files={'file': ('bank.' + format, template)}).json()
    assert (preview['added'], preview['updated']) == (3, 0)
    path = f"/api/imports/{preview['id']}/commit"
    assert learner.post(path, json={'publish': publish_now}).status_code == 403
    assert admin.post(path, json={'publish': publish_now}).status_code == 200
    visible = lambda: next((b for b in learner.get('/api/banks').json() if b['id'] == bank['id']), None)
    if not publish_now:
        assert visible() is None
        saved = next(b for b in admin.get('/api/banks').json() if b['id'] == bank['id'])
        assert admin.post(f"/api/banks/{bank['id']}/publish", json={'revision': saved['revision']}).status_code == 200
    assert visible()['count'] == 3
    assert visible()['project_id'] == project['id']


def test_direct_import_atomic_conflicts_retention_and_bank_isolation(system):
    admin, learner, _, _, bid = setup_practice(system)
    original = next(b for b in admin.get('/api/banks').json() if b['id'] == bid)
    other = admin.post('/api/banks', json={'title': '独立题库'}).json()['id']
    preview = import_bank(admin, other)
    assert admin.post(f"/api/imports/{preview['id']}/commit", json={'publish': True}).status_code == 200
    bad = import_bank(admin, bid, SAMPLE.replace('Q2,多选', 'Q1,多选'))
    assert bad['errors'][0]['row'] == 3 and bad['errors'][0]['field'] == '编号'
    assert admin.post(f"/api/imports/{bad['id']}/commit", json={'publish': True}).status_code == 404
    assert next(b for b in admin.get('/api/banks').json() if b['id'] == bid) == original
    partial = SAMPLE.splitlines()[0] + '\n' + SAMPLE.splitlines()[1].replace('一加一？', '更新题干') + '\n' + SAMPLE.splitlines()[2].replace('Q2', 'Q4') + '\n'
    stale = import_bank(admin, bid)
    preview = import_bank(admin, bid, partial)
    assert (preview['added'], preview['updated']) == (1, 1)
    assert admin.post(f"/api/imports/{preview['id']}/commit", json={'publish': True}).status_code == 200
    updated = next(b for b in admin.get('/api/banks').json() if b['id'] == bid)
    assert [q['code'] for q in updated['questions']] == ['Q1', 'Q2', 'Q3', 'Q4']
    assert updated['questions'][0]['stem'] == '更新题干'
    assert updated['questions'][0]['id'] == original['questions'][0]['id']
    isolated = next(b for b in admin.get('/api/banks').json() if b['id'] == other)
    assert isolated['questions'][0]['stem'] == '一加一？'
    assert isolated['questions'][0]['id'] != updated['questions'][0]['id']
    assert admin.post(f"/api/imports/{stale['id']}/commit", json={'publish': True}).status_code == 409
    assert next(b for b in admin.get('/api/banks').json() if b['id'] == bid) == updated


def test_direct_import_preserves_finished_score_and_active_answers(system):
    admin, learner, device, _, bid = setup_practice(system)
    session = learner.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '20'}).json()
    answered = learner.post(f"/api/sessions/{session['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['B']}).json()
    ended = learner.post(f"/api/sessions/{session['id']}/finish", json={'revision': answered['revision']}).json()
    active = learner.post('/api/sessions', json={'bank_id': bid, 'mode': '顺序练习', 'amount': '20', 'restart': True}).json()
    p = import_bank(admin, bid, SAMPLE.replace(',B,加法', ',A,加法'))
    assert admin.post(f"/api/imports/{p['id']}/commit", json={'publish': True}).status_code == 200
    assert device.get(f"/api/sessions/{ended['id']}").json() == ended
    assert device.get(f"/api/sessions/{active['id']}").json() == active
    result = learner.post(f"/api/sessions/{active['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['B']})
    assert result.status_code == 200, result.text
    assert result.json()['answers']['0']['correct'] is True
