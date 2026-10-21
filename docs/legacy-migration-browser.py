"""Run against an isolated server, never a production database."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8770'
out = Path('docs/screenshots/legacy-migration')
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    admin = p.request.new_context(base_url=BASE)
    assert admin.post('/api/login', data={'username': 'admin', 'password': 'Admin-test-12345'}).ok
    suffix = uuid4().hex[:8]
    year = admin.post('/api/years', data={'name': '2026-' + suffix}).json()
    project = admin.post('/api/projects', data={'name': '技能比赛', 'year_id': year['id']}).json()
    banks = []
    for published in [True, False]:
        bank = admin.post('/api/banks', data={'title': ('旧生效题库-' if published else '旧草稿-') + suffix}).json()
        template = admin.get('/api/template.csv').body()
        preview = admin.post('/api/banks/' + bank['id'] + '/preview', multipart={'file': {'name': 'bank.csv', 'mimeType': 'text/csv', 'buffer': template}}).json()
        assert admin.post('/api/imports/' + preview['id'] + '/commit', data={'publish': published}).ok
        banks.append(bank)
    user = p.request.new_context(base_url=BASE)
    username = 'migration_' + suffix
    assert user.post('/api/register', data={'username': username, 'name': username, 'password': 'Learn-test-12345'}).ok
    assert user.post('/api/login', data={'username': username, 'name': username, 'password': 'Learn-test-12345'}).ok
    assert not any(b['id'] in [bank['id'] for bank in banks] for b in user.get('/api/banks').json())
    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/admin', wait_until='networkidle')
    page.get_by_label('用户名', exact=True).fill('admin')
    page.get_by_label('密码', exact=True).fill('Admin-test-12345')
    page.get_by_role('button', name='登录', exact=True).click()
    page.get_by_role('button', name='题库管理', exact=True).click()
    page.locator('button[data-directory="unassigned"]').click()
    expect(page.get_by_role('heading', name=banks[0]['title'], exact=True)).to_be_visible()
    page.screenshot(path=str(out / 'pending-desktop.png'), full_page=True)
    for i, bank in enumerate(banks):
        if i:
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('#admin-directory').select_option('unassigned')
            page.screenshot(path=str(out / 'pending-mobile.png'), full_page=True)
        page.locator(f'button[data-move-bank="{bank["id"]}"]').click()
        page.locator('select[name="project_id"]').select_option(project['id'])
        page.get_by_role('button', name='确认', exact=True).click()
        expect(page.locator('#dialog')).not_to_be_visible()
        page.reload(wait_until='networkidle')
        if i:
            page.locator('#admin-directory').select_option(project['id'])
        else:
            page.locator(f'button[data-directory="{project["id"]}"]').click()
        expect(page.get_by_role('heading', name=bank['title'], exact=True)).to_be_visible()
        assert [b['id'] for b in user.get('/api/banks').json() if b['id'] in [bank['id'] for bank in banks]] == [banks[0]['id']]
        if i:
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(out / 'assigned-mobile.png'), full_page=True)
    assert not errors, errors
    learner_page = browser.new_page(viewport={'width': 390, 'height': 844}, storage_state=user.storage_state())
    learner_page.on('pageerror', lambda error: errors.append(str(error)))
    learner_page.goto(BASE + '/learn', wait_until='networkidle')
    learner_page.locator('#learner-year').select_option(year['id'])
    learner_page.locator('#learner-project').select_option(project['id'])
    expect(learner_page.locator('#bank option[value="' + banks[0]['id'] + '"]')).to_have_count(1)
    expect(learner_page.locator('#bank option[value="' + banks[1]['id'] + '"]')).to_have_count(0)
    learner_page.screenshot(path=str(out / 'learner-mobile.png'), full_page=True)
    assert not errors, errors
    browser.close()
print('PASS: desktop/mobile assignment, reload persistence, learner visibility, draft privacy')
