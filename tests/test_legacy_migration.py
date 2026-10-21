"""Legacy database fixtures; observations use the public HTTP API."""
import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient
from ops.backup import backup, restore
from test_app import system, setup_practice, import_bank, login


def inventory(path):
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        return {
            'objects': db.execute('SELECT kind,id,owner,body FROM objects ORDER BY kind,id').fetchall(),
            'users': db.execute('SELECT * FROM users ORDER BY id').fetchall(),
        }


def test_legacy_banks_are_private_until_assigned(system):
    admin, learner, device, other, bid = setup_practice(system)
    ongoing = learner.post('/api/sessions', json={'bank_id': bid}).json()
    sid = ongoing['id']
    qid = ongoing['questions'][0]['id']
    learner.post('/api/favorite', json={'question_id': qid, 'value': True})
    answered = learner.post(f'/api/sessions/{sid}/answer', json={'revision': 0, 'index': 0, 'selected': ['A']}).json()
    history = learner.post('/api/sessions', json={'bank_id': bid, 'restart': True}).json()
    learner.post(f"/api/sessions/{history['id']}/finish", json={'revision': 0})
    draft = admin.post('/api/banks', json={'title': '2025比赛草稿'}).json()
    preview = import_bank(admin, draft['id'])
    admin.post(f"/api/imports/{preview['id']}/commit")
    # Reproduce pre-directory objects, including sessions without project snapshots.
    with sqlite3.connect(system.DATABASE) as db:
        db.execute("DELETE FROM objects WHERE kind IN ('year','project')")
        for kind, oid, body in db.execute("SELECT kind,id,body FROM objects WHERE kind IN ('bank','session')").fetchall():
            obj = json.loads(body)
            obj.pop('project_id' if kind == 'bank' else 'project', None)
            db.execute('UPDATE objects SET body=? WHERE kind=? AND id=?', (json.dumps(obj), kind, oid))
    before_banks = admin.get('/api/banks').json()
    before_session = learner.get(f'/api/sessions/{sid}').json()
    before_history = learner.get('/api/sessions').json()
    before_learning = learner.get('/api/learning').json()
    before_inventory = inventory(system.DATABASE)
    system.initialize()
    system.initialize()
    assert inventory(system.DATABASE) == before_inventory
    assert admin.get('/api/banks').json() == before_banks
    assert learner.get('/api/banks').json() == []
    assert learner.get('/api/learning/directories').json() == {'years': [], 'projects': []}
    assert learner.get('/api/learning').json()['available'] == 0
    for client in [admin, learner]:
        for mode in ['顺序练习', '随机练习', '错题练习', '收藏练习']:
            assert client.post('/api/sessions', json={'bank_id': bid, 'mode': mode}).status_code == 400
    assert other.post('/api/favorite', json={'question_id': qid, 'value': True}).status_code == 404
    assert learner.get('/api/sessions').json() == before_history
    assert device.get(f'/api/sessions/{sid}').json() == before_session
    assert other.get(f'/api/sessions/{sid}').status_code == 404
    continued = device.patch(f'/api/sessions/{sid}', json={'revision': answered['revision'], 'index': 1, 'selected': ['A', 'C']})
    assert continued.status_code == 200
    before_session = continued.json()
    year = admin.post('/api/years', json={'name': '2026'}).json()
    project = admin.post('/api/projects', json={'name': '技能比赛', 'year_id': year['id']}).json()
    for bank in before_banks:
        payload = {'revision': bank['revision'], 'project_id': project['id']}
        assert learner.patch('/api/banks/' + bank['id'], json=payload).status_code == 403
        assigned = admin.patch('/api/banks/' + bank['id'], json=payload)
        assert assigned.status_code == 200
        assert assigned.json() == bank | {'project_id': project['id'], 'revision': bank['revision'] + 1}
        assert admin.patch('/api/banks/' + bank['id'], json=payload).status_code == 409
    system.initialize()
    visible = learner.get('/api/banks').json()
    assert [b['id'] for b in visible] == [bid]
    assert visible[0]['project_id'] == project['id']
    assert learner.get('/api/learning/directories').json() == {'years': [year], 'projects': [project]}
    assert device.get(f'/api/sessions/{sid}').json() == before_session
    after_learning = learner.get('/api/learning').json()
    for key in ['mistakes', 'favorites', 'cursors', 'total', 'correct']:
        assert after_learning[key] == before_learning[key]
    assert after_learning['records'][0]['question'] == before_learning['records'][0]['question']
    assert len(learner.get('/api/sessions').json()) == 2
    continued = device.post(f'/api/sessions/{sid}/answer', json={'revision': before_session['revision'], 'index': 1, 'selected': ['A', 'C']})
    assert continued.status_code == 200
    assert learner.post(f'/api/sessions/{sid}/finish', json={'revision': continued.json()['revision']}).status_code == 200
    assert learner.post('/api/sessions', json={'bank_id': bid, 'restart': True}).status_code == 200
    assert other.get('/api/learning').json()['favorites'] == []


def test_migration_backup_restore_preserves_all_objects(system, tmp_path):
    admin, learner, _, _, bid = setup_practice(system)
    session = learner.post('/api/sessions', json={'bank_id': bid}).json()
    learner.post('/api/favorite', json={'question_id': session['questions'][0]['id'], 'value': True})
    learner.post(f"/api/sessions/{session['id']}/answer", json={'revision': 0, 'index': 0, 'selected': ['A']})
    # Only fixture construction uses SQL; API checks below prove restored behavior.
    with sqlite3.connect(system.DATABASE) as db:
        bank = json.loads(db.execute("SELECT body FROM objects WHERE kind='bank' AND id=?", (bid,)).fetchone()[0])
        bank.pop('project_id')
        db.execute("UPDATE objects SET body=? WHERE kind='bank' AND id=?", (json.dumps(bank), bid))
    original = learner.get('/api/sessions/' + session['id']).json()
    learning = learner.get('/api/learning').json()
    source = Path(system.DATABASE)
    saved = backup(source, tmp_path / 'backups')
    # Counts, stable keys, owners and full object bodies are the migration audit seam.
    before = inventory(source)
    system.initialize()
    assert inventory(source) == before == inventory(saved)
    restored = tmp_path / 'restored.db'
    restore(saved, str(restored))
    assert inventory(restored) == before
    system.DATABASE = str(restored)
    system.initialize()
    assert inventory(restored) == before
    client = TestClient(system.app)
    assert client.get('/api/me').status_code == 401
    login(client, 'learner', 'Learn-test-12345')
    assert client.get('/api/banks').json() == []
    assert client.get('/api/sessions/' + session['id']).json() == original
    assert client.get('/api/learning').json() == learning
