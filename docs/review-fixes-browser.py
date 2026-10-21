"""Run against an isolated test server; verify review fixes and form dispatch."""
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8778'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/learn', wait_until='networkidle')
    username = 'review_' + uuid4().hex[:8]
    page.get_by_role('button', name='没有账号，注册', exact=True).click()
    page.locator('input[name=username]').fill(username)
    page.locator('input[name=name]').fill('Review learner')
    page.locator('input[name=password]').fill('Learn-test-12345')
    page.get_by_role('button', name='注册', exact=True).click()
    expect(page.get_by_role('button', name='登录', exact=True)).to_be_visible()
    page.locator('input[name=username]').fill(username)
    page.locator('input[name=password]').fill('Learn-test-12345')
    page.get_by_role('button', name='登录', exact=True).click()
    expect(page.locator('#learner-year')).to_be_visible()

    admin = browser.new_page()
    admin.goto(BASE + '/admin', wait_until='networkidle')
    admin.locator('input[name=username]').fill('admin')
    admin.locator('input[name=password]').fill('Admin-test-12345')
    admin.get_by_role('button', name='登录', exact=True).click()
    admin.get_by_role('button', name='新建年份', exact=True).click()
    admin.locator('input[name=name]').fill('2026')
    admin.get_by_role('button', name='确认', exact=True).click()
    admin.get_by_role('button', name='新建项目', exact=True).click()
    admin.locator('input[name=name]').fill('Review project')
    admin.get_by_role('button', name='确认', exact=True).click()
    admin.get_by_role('button', name='新建题库并上传', exact=True).click()
    admin.locator('input[name=title]').fill('Review bank')
    # The current project is selected automatically; file selection submits.
    template = admin.request.get(BASE + '/api/template.csv').body()
    admin.locator('input[name=file]').set_input_files({'name': 'bank.csv', 'mimeType': 'text/csv', 'buffer': template})
    admin.get_by_role('button', name='确认导入并生效', exact=True).click()
    expect(admin.get_by_text('Review bank', exact=True)).to_be_visible()
    bank = next(b for b in admin.request.get(BASE + '/api/banks').json() if b['title'] == 'Review bank' and b['status'] == 'published')
    qid = bank['questions'][0]['id']
    assert page.request.post(BASE + '/api/favorite', data={'question_id': qid, 'value': True}).ok
    admin.on('dialog', lambda dialog: dialog.accept())
    admin.get_by_role('button', name='归档题库', exact=True).click()
    expect(admin.get_by_text('已归档', exact=True)).to_be_visible()
    for width in [1440, 390]:
        page.set_viewport_size({'width': width, 'height': 900})
        page.goto(BASE + '/learn#mistakes', wait_until='networkidle')
        page.reload(wait_until='networkidle')
        page.get_by_text('回看题目', exact=True).click()
        expect(page.locator('details').filter(has_text=bank['questions'][0]['stem'])).to_be_visible()
        assert page.locator('button[data-open]').count() == 0
        assert page.locator('details').inner_text().find('答案：') >= 0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
    print('PASS: registration, login, directory/import forms, archive and desktop/mobile favorite review')
