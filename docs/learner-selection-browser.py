"""Run against an isolated local server: python docs/learner-selection-browser.py."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8767'
SAMPLE = '编号,题型,题干,A,B,C,D,答案,解析,分类,标签\nQ1,单选,一加一？,一,二,三,,B,加法,AI知识,数学\nQ2,单选,安全问题？,一,二,三,,B,安全解析,安全知识,安全\n'
out = Path('docs/screenshots/learner-selection')
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    admin = p.request.new_context(base_url=BASE)
    assert admin.post('/api/login', data={'username': 'admin', 'password': 'Admin-test-12345'}).ok
    def post(path, body):
        r = admin.post('/api' + path, data=body)
        assert r.ok, r.text()
        return r.json()
    years = [post('/years', {'name': name}) for name in ['2026', '2027']]
    projects = [post('/projects', {'name': name, 'year_id': year['id']}) for name, year in zip(['技能比赛', '年度考试'], years)]
    banks = []
    for name, project, text in [('AI题库', projects[0], SAMPLE), ('无分类题库', projects[0], SAMPLE.replace('AI知识', '').replace('安全知识', '')), ('安全题库', projects[1], SAMPLE)]:
        bank = post('/banks', {'title': name, 'project_id': project['id']})
        r = admin.post('/api/banks/' + bank['id'] + '/preview', multipart={'file': {'name': 'bank.csv', 'mimeType': 'text/csv', 'buffer': text.encode('utf-8-sig')}})
        assert r.ok, r.text()
        post('/imports/' + r.json()['id'] + '/commit', {})
        post('/banks/' + bank['id'] + '/publish', {'revision': 1})
        banks.append(bank)
    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    def navigate(page_id):
        button = page.locator(f'button[data-page="{page_id}"]')
        if not button.count():
            navigate('home')
        if not button.is_visible():
            button.locator('xpath=ancestor::details').locator('summary').click()
        button.click()
        heading = {'home': '继续今天的学习', 'study': '我的学习'}[page_id]
        expect(page.get_by_role('heading', name=heading, exact=True)).to_be_visible()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    username = 'browser_' + uuid4().hex[:8]
    user = p.request.new_context(base_url=BASE)
    assert user.post('/api/register', data={'username': username, 'password': 'Learn-test-12345'}).ok
    page.goto(BASE + '/learn', wait_until='networkidle')
    print('Initial controls:', page.locator('input').evaluate_all('(els)=>els.map(e=>({name:e.name,id:e.id}))'))
    page.get_by_label('用户名', exact=True).fill(username)
    page.get_by_label('密码', exact=True).fill('Learn-test-12345')
    page.get_by_role('button', name='登录', exact=True).click()
    expect(page.locator('#learner-year')).to_be_visible()
    expect(page.locator('#bank')).to_be_disabled()
    page.locator('#learner-year').select_option(years[0]['id'])
    page.locator('#learner-project').select_option(projects[0]['id'])
    page.locator('#bank').select_option(banks[0]['id'])
    page.locator('#learner-category').select_option('AI知识')
    page.locator('#learner-mode').select_option('随机练习')
    page.reload(wait_until='networkidle')
    expect(page.locator('#bank')).to_have_value(banks[0]['id'])
    expect(page.locator('#learner-category')).to_have_value('AI知识')
    expect(page.locator('#learner-mode')).to_have_value('随机练习')
    page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'desktop.png'), full_page=True, animations='disabled')
    page.get_by_role('button', name='开始练习', exact=True).click()
    expect(page.get_by_role('heading', name='一加一？', exact=True)).to_be_visible()
    navigate('home')
    page.get_by_role('button', name='继续练习', exact=True).first.click()
    expect(page.get_by_role('heading', name='一加一？', exact=True)).to_be_visible()
    navigate('study')
    expect(page.get_by_role('heading', name='我的学习', exact=True)).to_be_visible()
    page.get_by_role('button', name='查看全部历史', exact=True).click()
    expect(page.get_by_role('heading', name='练习历史', exact=True)).to_be_visible()
    navigate('study')
    page.get_by_role('button', name='查看错题与收藏', exact=True).click()
    expect(page.get_by_role('heading', name='错题与收藏', exact=True)).to_be_visible()
    page.get_by_role('button', name='选择题库练习收藏', exact=True).click()
    expect(page.locator('#learner-mode')).to_have_value('收藏练习')
    page.get_by_role('button', name='开始练习', exact=True).click()
    expect(page.locator('#start-error')).to_contain_text('没有可练习题目')
    page.locator('#bank').select_option(banks[1]['id'])
    expect(page.locator('#learner-category')).to_have_count(0)
    expect(page.locator('#message')).to_be_empty()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#learner-year').select_option(years[1]['id'])
    expect(page.locator('#learner-project')).to_have_value('')
    expect(page.locator('#bank')).to_have_value('')
    expect(page.locator('#bank')).to_be_disabled()
    page.locator('#learner-project').select_option(projects[1]['id'])
    expect(page.locator('#bank option')).to_have_count(2)
    page.locator('#bank').select_option(banks[2]['id'])
    page.locator('#learner-mode').select_option('顺序练习')
    page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
    page.screenshot(path=str(out / 'mobile.png'), full_page=True, animations='disabled')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_role('button', name='开始练习', exact=True).click()
    expect(page.get_by_role('heading', name='一加一？', exact=True)).to_be_visible()
    navigate('home')
    page.get_by_role('button', name='继续练习', exact=True).first.click()
    expect(page.get_by_role('heading', name='一加一？', exact=True)).to_be_visible()
    # Moving the remembered bank must clear it rather than choosing another bank.
    r = admin.patch('/api/banks/' + banks[2]['id'], data={'revision': 2, 'project_id': projects[0]['id']})
    assert r.ok, r.text()
    navigate('home')
    expect(page.get_by_text('上次选择已失效，请重新选择题库或知识分类。', exact=True)).to_be_visible()
    expect(page.locator('#bank')).to_have_value('')
    page.locator('#learner-year').select_option(years[0]['id'])
    page.locator('#learner-project').select_option(projects[0]['id'])
    page.locator('#bank').select_option(banks[0]['id'])
    page.reload(wait_until='networkidle')
    expect(page.locator('#bank')).to_have_value(banks[0]['id'])
    assert not errors, errors
    print('PASS: desktop/mobile cascade, category, modes, reload memory, invalid memory, start/continue, study/history, empty review range; no page errors')
    browser.close()
    user.dispose()
    admin.dispose()
