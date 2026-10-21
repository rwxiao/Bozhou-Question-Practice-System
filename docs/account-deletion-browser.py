"""Run against an isolated test server, never a production database."""
import os
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

BASE = os.getenv('BROWSER_BASE', 'http://127.0.0.1:8772')
OUT = Path('docs/screenshots/account-deletion')
OUT.mkdir(parents=True, exist_ok=True)


def login(page, username, password):
    page.locator('input[name=username]').fill(username)
    page.locator('input[name=password]').fill(password)
    page.get_by_role('button', name='登录', exact=True).click()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.getenv('BROWSER_CHANNEL') or 'msedge')
    errors = []
    learner = browser.new_page()
    learner.goto(BASE + '/learn', wait_until='networkidle')
    username = 'delete_' + uuid4().hex[:8]
    assert learner.request.post(BASE + '/api/register', data={
        'username': username, 'name': '删除验收用户', 'password': 'Learn-test-12345'
    }).status == 200
    login(learner, username, 'Learn-test-12345')
    expect(learner.locator('header')).to_be_visible()
    uid = learner.request.get(BASE + '/api/me').json()['id']

    admin = browser.new_page(viewport={'width': 1440, 'height': 1000})
    admin.on('pageerror', lambda error: errors.append(str(error)))
    admin.goto(BASE + '/admin', wait_until='networkidle')
    login(admin, 'admin', 'Admin-test-12345')
    admin.locator('button[data-page=users]').click()
    account = admin.locator(f'article[data-user="{uid}"]')
    expect(account.get_by_role('button', name='停用账号', exact=True)).to_be_enabled()
    assert admin.locator('article[data-user]').filter(has=admin.get_by_role('heading', name='admin', exact=True)).locator('[data-delete-user]').count() == 0
    account.get_by_role('button', name='彻底删除账号', exact=True).click()
    dialog = admin.get_by_role('dialog')
    for text in [username, '无法撤销', '个人练习与历史、错题和收藏', '公共题库', '其他用户', '纠错保留', '停用账号']:
        expect(dialog).to_contain_text(text)
    admin.screenshot(path=str(OUT / 'confirmation-desktop.png'), full_page=True)
    admin.get_by_role('button', name='取消', exact=True).click()
    expect(account).to_be_visible()
    assert learner.request.get(BASE + '/api/me').status == 200
    admin.set_viewport_size({'width': 390, 'height': 844})
    account.get_by_role('button', name='彻底删除账号', exact=True).click()
    checkbox = dialog.get_by_role('checkbox')
    admin.get_by_role('button', name='确认', exact=True).click()
    expect(dialog).to_be_visible()
    expect(checkbox).not_to_be_checked()
    assert learner.request.get(BASE + '/api/me').status == 200
    checkbox.check()
    assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth')
    admin.screenshot(path=str(OUT / 'confirmation-mobile.png'), full_page=True)
    admin.get_by_role('button', name='确认', exact=True).click()
    expect(dialog).not_to_be_visible()
    expect(account).to_have_count(0)
    assert learner.request.get(BASE + '/api/me').status == 401
    admin.reload(wait_until='networkidle')
    expect(account).to_have_count(0)
    learner.reload(wait_until='networkidle')
    login(learner, username, 'Learn-test-12345')
    expect(learner.get_by_text('用户名或密码错误', exact=True)).to_be_visible()
    assert not errors, errors
    browser.close()
    print('PASS: desktop/mobile impact, cancel, required confirmation, deletion, reload, revoked login; no browser errors')
