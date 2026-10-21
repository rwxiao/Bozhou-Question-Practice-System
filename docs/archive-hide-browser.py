"""Browser acceptance against an isolated server at 127.0.0.1:8769."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8769'
SAMPLE = '编号,题型,题干,A,B,C,D,答案,解析,分类,标签\nQ1,单选,一加一？,一,二,三,,B,加法,基础,数学\nQ2,单选,安全问题？,一,二,三,,B,安全解析,安全,安全\n'
out = Path('docs/screenshots/archive-hide')
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    admin = p.request.new_context(base_url=BASE)
    assert admin.post('/api/login', data={'username': 'admin', 'password': 'Admin-test-12345'}).ok

    def post(client, path, body):
        response = client.post('/api' + path, data=body)
        assert response.ok, response.text()
        return response.json()

    suffix = uuid4().hex[:8]
    year = post(admin, '/years', {'name': '2026-' + suffix})
    project = post(admin, '/projects', {'name': '技能比赛-' + suffix, 'year_id': year['id']})
    banks = []
    for title in ['结束题库-' + suffix, '仍可练习-' + suffix]:
        bank = post(admin, '/banks', {'title': title, 'project_id': project['id']})
        preview = admin.post('/api/banks/' + bank['id'] + '/preview', multipart={'file': {'name': 'bank.csv', 'mimeType': 'text/csv', 'buffer': SAMPLE.encode('utf-8-sig')}})
        assert preview.ok
        post(admin, '/imports/' + preview.json()['id'] + '/commit', {'publish': True})
        banks.append(bank)
    username = 'archive_' + suffix
    user = p.request.new_context(base_url=BASE)
    post(user, '/register', {'username': username, 'name': username, 'password': 'Learn-test-12345'})
    post(user, '/login', {'username': username, 'name': username, 'password': 'Learn-test-12345'})
    session = post(user, '/sessions', {'bank_id': banks[0]['id']})
    post(user, '/favorite', {'question_id': session['questions'][0]['id'], 'value': True})
    post(user, '/sessions/' + session['id'] + '/answer', {'revision': 0, 'index': 0, 'selected': ['A']})

    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def login(role, name, password, navigate=True):
        if navigate:
            page.goto(BASE + '/' + role, wait_until='networkidle')
        page.get_by_label('用户名', exact=True).fill(name)
        page.get_by_label('密码', exact=True).fill(password)
        page.get_by_role('button', name='登录', exact=True).click()

    login('admin', 'admin', 'Admin-test-12345')
    page.get_by_role('button', name='题库管理', exact=True).click()
    page.locator(f'button[data-directory="{project["id"]}"]').click()
    page.on('dialog', lambda dialog: dialog.accept())
    page.locator(f'button[data-archive-bank="{banks[0]["id"]}"]').click()
    expect(page.locator(f'button[data-archive-bank="{banks[0]["id"]}"]')).to_be_disabled()
    expect(page.get_by_text('已归档', exact=True)).to_be_visible()
    page.get_by_role('button', name='隐藏项目', exact=True).click()
    expect(page.locator(f'button[data-directory="{project["id"]}"]')).to_have_count(0)
    page.locator('[data-action="toggleHiddenProjects"]').click()
    page.locator(f'button[data-directory="{project["id"]}"]').click()
    expect(page.get_by_role('button', name='取消隐藏项目', exact=True)).to_be_visible()
    page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'admin-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    expect(page.locator('#admin-directory')).to_have_value(project['id'])
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'admin-mobile.png'), full_page=True)
    page.get_by_role('button', name='退出 ', exact=False).click()

    login('learn', username, 'Learn-test-12345')
    expect(page.locator('#learner-project option[value="' + project['id'] + '"]')).to_have_count(0)
    page.locator('[data-action="toggleHiddenProjects"]').click()
    page.locator('#learner-year').select_option(year['id'])
    page.locator('#learner-project').select_option(project['id'])
    expect(page.locator('#bank option[value="' + banks[0]['id'] + '"]')).to_have_count(0)
    expect(page.locator('#bank option[value="' + banks[1]['id'] + '"]')).to_have_count(1)
    page.get_by_role('button', name='继续练习', exact=True).first.click()
    expect(page.get_by_role('heading', name='一加一？', exact=True)).to_be_visible()
    page.locator('button[data-jump="1"]').click()
    page.locator('button[data-option="B"]').click()
    page.locator('button[data-action="submit"]').click()
    expect(page.get_by_text('回答正确', exact=True)).to_be_visible()
    page.locator('.practice-menu summary').click()
    page.locator('button[data-action="finish"]').click()
    expect(page.get_by_role('heading', name='本次练习已结束', exact=True)).to_be_visible()
    page.locator('button[data-page="home"]').click()
    page.get_by_role('button', name='我的学习', exact=True).click()
    expect(page.get_by_role('heading', name='我的学习', exact=True)).to_be_visible()
    page.get_by_role('button', name='查看全部历史', exact=True).click()
    expect(page.get_by_text('2026-' + suffix + ' / 技能比赛-' + suffix, exact=False)).to_be_visible()
    page.get_by_role('button', name='我的学习', exact=True).click()
    expect(page.get_by_role('heading', name='我的学习', exact=True)).to_be_visible()
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name='查看错题与收藏', exact=True).click()
    expect(page.get_by_role('heading', name='收藏', exact=True)).to_be_visible()
    for details in page.locator('details').all():
        details.locator('summary').click()
    expect(page.get_by_text('答案：B', exact=True)).to_have_count(2)
    expect(page.get_by_text('解析：加法', exact=True)).to_have_count(2)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'learner-mobile.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    page.screenshot(path=str(out / 'learner-desktop.png'), full_page=True)
    page.get_by_role('button', name='退出 ', exact=False).click()
    login('learn', username, 'Learn-test-12345', navigate=False)
    expect(page.locator('[data-action="toggleHiddenProjects"]')).to_have_text('显示已隐藏项目')
    page.goto(BASE + '/learn#banks', wait_until='networkidle')
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('heading', name='题库', exact=True)).to_be_visible()
    expect(page.get_by_role('heading', name=banks[1]['title'], exact=True)).to_have_count(0)
    page.locator('[data-action="toggleHiddenProjects"]').click()
    expect(page.get_by_role('heading', name=banks[1]['title'], exact=True)).to_be_visible()
    assert not errors, errors
    browser.close()
    print('PASS: archive, hide/find, continue/finish, project history, mistakes/favorites; desktop/mobile')
