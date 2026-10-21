"""Isolated browser acceptance: python docs/timed-practice-browser.py.
Requires system Python Playwright + Edge, and project .venv backend dependencies.
The test server alone uses a controllable clock; production has no clock override.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import time
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8776'
SAMPLE = '编号,题型,题干,A,B,C,D,答案,解析,分类,标签\nQ1,单选,一加一？,一,二,三,,B,加法,基础,数学\nQ2,多选,偶数？,二,三,四,,A|C,偶数,基础,数学\n'
OUT = ROOT / 'docs/screenshots/timed-practice'
OUT.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix='timed-practice-') as folder:
    clock = Path(folder) / 'clock'
    clock.write_text('0')
    env = os.environ | {'DATABASE': str(Path(folder) / 'test.db'), 'ADMIN_USERNAME': 'admin', 'ADMIN_PASSWORD': 'Admin-test-12345', 'TEST_CLOCK': str(clock)}
    server_code = "import os,time; from pathlib import Path; from types import SimpleNamespace; import app,uvicorn; real=time.time; app.time=SimpleNamespace(time=lambda:real()+float(Path(os.environ['TEST_CLOCK']).read_text())); uvicorn.run(app.app,host='127.0.0.1',port=8776,log_level='error')"
    backend = ROOT / '.venv/Scripts/python.exe'
    if not backend.exists():
        backend = ROOT / '.venv/bin/python'
    with (Path(folder) / 'server.log').open('w') as log:
        server = subprocess.Popen([str(backend), '-c', server_code], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            with sync_playwright() as p:
                admin = p.request.new_context(base_url=BASE)
                for attempt in range(60):
                    try:
                        if admin.get('/api/me').status == 401:
                            break
                    except Exception:
                        time.sleep(0.2)
                else:
                    raise RuntimeError('isolated backend did not start')
                assert admin.post('/api/login', data={'username': 'admin', 'password': 'Admin-test-12345'}).ok
                def post(path, body):
                    response = admin.post('/api' + path, data=body)
                    assert response.ok, response.text()
                    return response.json()
                year = post('/years', {'name': '2026'})
                project = post('/projects', {'name': '限时练习验收', 'year_id': year['id']})
                bank = post('/banks', {'title': '限时题库', 'project_id': project['id']})
                preview = admin.post('/api/banks/' + bank['id'] + '/preview', multipart={'file': {'name': 'test.csv', 'mimeType': 'text/csv', 'buffer': SAMPLE.encode('utf-8-sig')}}).json()
                post('/imports/' + preview['id'] + '/commit', {'publish': True})
                username = 'timer_' + uuid4().hex[:8]
                assert admin.post('/api/register', data={'username': username, 'name': username, 'password': 'Learn-test-12345'}).ok
                browser = p.chromium.launch(headless=True, channel='msedge')
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(BASE + '/learn', wait_until='networkidle')
                page.get_by_label('用户名', exact=True).fill(username)
                page.get_by_label('密码', exact=True).fill('Wrong-test-12345')
                page.get_by_role('button', name='登录', exact=True).click()
                expect(page.locator('#message')).to_contain_text('用户名或密码错误')
                page.get_by_label('密码', exact=True).fill('Learn-test-12345')
                page.get_by_role('button', name='登录', exact=True).click()
                expect(page.locator('#learner-year')).to_be_visible()
                page.locator('#learner-year').select_option(year['id'])
                page.locator('#learner-project').select_option(project['id'])
                page.locator('#bank').select_option(bank['id'])
                expect(page.get_by_label('练习分钟数', exact=True)).to_be_disabled()
                for mode in ['顺序练习', '随机练习', '错题练习', '收藏练习']:
                    page.locator('#learner-mode').select_option(mode)
                    page.get_by_label('限时设置', exact=True).select_option('on')
                    expect(page.get_by_label('练习分钟数', exact=True)).to_be_enabled()
                    page.get_by_label('限时设置', exact=True).select_option('off')
                page.locator('#learner-mode').select_option('顺序练习')
                page.get_by_label('限时设置', exact=True).select_option('on')
                page.get_by_label('练习分钟数', exact=True).fill('0')
                assert not page.locator('#start').evaluate('(form)=>form.checkValidity()')
                page.get_by_label('练习分钟数', exact=True).fill('2')
                page.evaluate('document.activeElement.blur(); window.scrollTo(0,0)')
                page.screenshot(path=str(OUT / 'desktop-config.png'), full_page=True, animations='disabled')
                with page.expect_response(lambda r: r.url.endswith('/api/sessions') and r.request.method == 'POST') as created:
                    page.get_by_role('button', name='开始练习', exact=True).click()
                session = created.value.json()
                sid, deadline = session['id'], session['deadline']
                expect(page.locator('#practice-countdown')).to_contain_text('剩余 1:')
                before = page.locator('#practice-countdown').inner_text()
                expect(page.locator('#practice-countdown')).not_to_have_text(before, timeout=4000)
                page.locator('[data-option="B"]').click()
                page.get_by_role('button', name='提交答案', exact=True).click()
                expect(page.get_by_text('回答正确', exact=True)).to_be_visible()
                page.locator('[data-jump="1"]').click()
                page.locator('[data-option="A"]').click()
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(OUT / 'mobile-countdown.png'), full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.reload(wait_until='networkidle')
                page.get_by_role('button', name='继续练习', exact=True).first.click()
                expect(page.locator('#practice-countdown')).to_contain_text('剩余 1:')
                assert context.request.get(BASE + '/api/sessions/' + sid).json()['deadline'] == deadline
                # Advance only the isolated server clock. Visible UI must settle automatically.
                clock.write_text('130')
                expect(page.get_by_role('heading', name='本次练习已结束')).to_be_visible(timeout=10000)
                expect(page.get_by_text('已答 1/2 题，正确 1 题，未答 1 题。未提交题目不计分。', exact=True)).to_be_visible()
                assert context.request.get(BASE + '/api/sessions/' + sid).json()['answers'].keys() == {'0'}
                page.screenshot(path=str(OUT / 'mobile-result.png'), full_page=True)
                # A fresh page gets the same ended result, with no browser timer dependency.
                second = context.new_page()
                second.on('pageerror', lambda error: errors.append(str(error)))
                second.goto(BASE + '/learn', wait_until='networkidle')
                second.get_by_role('button', name='我的学习', exact=True).click()
                second.get_by_role('button', name='查看全部历史', exact=True).click()
                expect(second.get_by_role('heading', name='练习历史', exact=True, level=1)).to_be_visible()
                second.wait_for_load_state('networkidle')
                second.get_by_role('button', name='查看记录', exact=True).first.click()
                expect(second.get_by_role('heading', name='本次练习已结束')).to_be_visible()
                assert not errors, errors
                browser.close()
                print('PASS: timed controls, validation, countdown, refresh, mobile layout, automatic result, draft exclusion, return history; no page errors')
        finally:
            server.terminate()
            server.wait(timeout=10)
