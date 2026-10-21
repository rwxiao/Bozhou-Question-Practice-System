"""Run against an isolated test server with admin/Admin-test-12345."""
import os
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

BASE = os.getenv('BROWSER_BASE', 'http://127.0.0.1:8771')
OUT = Path('docs/screenshots/registration-disable')
OUT.mkdir(parents=True, exist_ok=True)


def login(page, username, password):
    page.locator('input[name=username]').fill(username)
    page.locator('input[name=password]').fill(password)
    page.get_by_role('button', name='登录', exact=True).click()


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, channel=os.getenv('BROWSER_CHANNEL') or None)
    errors = []
    learner = browser.new_page(viewport={'width': 390, 'height': 844})
    learner.on('pageerror', lambda error: errors.append(str(error)))
    learner.goto(BASE + '/learn', wait_until='networkidle')
    learner.get_by_role('button', name='没有账号，注册', exact=True).click()
    name = learner.get_by_label('姓名（必填）', exact=True)
    expect(name).to_have_attribute('required', '')
    username = 'browser_' + uuid4().hex[:8]
    learner.locator('input[name=username]').fill(username)
    learner.locator('input[name=password]').fill('Learn-test-12345')
    learner.get_by_role('button', name='注册', exact=True).click()
    expect(name).to_be_visible()
    assert name.evaluate('(input) => input.validity.valueMissing')
    name.fill('浏览器验证人员')
    learner.screenshot(path=str(OUT / 'registration-mobile.png'), full_page=True)
    learner.get_by_role('button', name='注册', exact=True).click()
    expect(learner.get_by_role('button', name='登录', exact=True)).to_be_visible()
    login(learner, username, 'Learn-test-12345')
    expect(learner.locator('header')).to_be_visible()
    assert learner.request.get(BASE + '/api/users').status == 403

    admin = browser.new_page(viewport={'width': 1440, 'height': 1000})
    admin.on('pageerror', lambda error: errors.append(str(error)))
    admin.goto(BASE + '/admin', wait_until='networkidle')
    login(admin, 'admin', 'Admin-test-12345')
    admin.locator('button[data-page=users]').click()
    expect(admin.get_by_role('heading', name='用户管理', exact=True)).to_be_visible()
    account = admin.locator('article[data-user]').filter(has=admin.get_by_role('heading', name=username, exact=True))
    expect(account).to_contain_text('浏览器验证人员')
    expect(account).to_contain_text('注册时间')
    expect(account).not_to_contain_text('未知')
    expect(admin.locator('input[type=password]')).to_have_count(0)
    admin.screenshot(path=str(OUT / 'users-desktop.png'), full_page=True)
    admin.reload(wait_until='networkidle')
    expect(account).to_be_visible()
    admin.set_viewport_size({'width': 390, 'height': 844})
    assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth')
    admin.screenshot(path=str(OUT / 'users-mobile.png'), full_page=True)
    account.get_by_role('button', name='停用账号', exact=True).click()
    expect(admin.get_by_role('dialog')).to_contain_text('个人练习、历史、错题和收藏继续保留')
    admin.get_by_role('button', name='取消', exact=True).click()
    expect(account.get_by_role('button', name='停用账号', exact=True)).to_be_enabled()
    account.get_by_role('button', name='停用账号', exact=True).click()
    admin.get_by_role('button', name='确认', exact=True).click()
    expect(account.get_by_role('button', name='已停用', exact=True)).to_be_disabled()
    assert learner.request.get(BASE + '/api/me').status == 401
    learner.reload(wait_until='networkidle')
    login(learner, username, 'Learn-test-12345')
    expect(learner.get_by_text('账号已停用，请联系管理员', exact=True)).to_be_visible()
    assert not errors, errors
    browser.close()
    print('PASS: registration, required name, users page, reload, mobile, cancel/disable, revoked login; no browser errors')
