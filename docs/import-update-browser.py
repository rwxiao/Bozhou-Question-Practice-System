"""Run with an isolated server on port 8768 and test administrator credentials."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8768'
OUT = Path('docs/screenshots/import-update')
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    api = p.request.new_context(base_url=BASE)
    assert api.post('/api/login', data={'username': 'admin', 'password': 'Admin-test-12345'}).ok
    year = api.post('/api/years', data={'name': '2026'}).json()
    project = api.post('/api/projects', data={'name': '导入验收', 'year_id': year['id']}).json()
    csv = api.get('/api/template.csv').body()
    xlsx = api.get('/api/template.xlsx').body()
    browser = p.chromium.launch(headless=True, channel='msedge')
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/admin', wait_until='networkidle')
    page.get_by_label('用户名', exact=True).fill('admin')
    page.get_by_label('密码', exact=True).fill('Admin-test-12345')
    page.get_by_role('button', name='登录', exact=True).click()
    page.locator('[data-page="admin"]').click()
    page.locator(f'[data-directory="{project["id"]}"]').click()
    page.get_by_role('button', name='新建题库并上传', exact=True).click()
    title = '浏览器题库' + uuid4().hex[:6]
    page.get_by_label('名称', exact=True).fill(title)
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'bank.csv', 'mimeType': 'text/csv', 'buffer': csv})
    expect(page.get_by_role('heading', name='导入预览', exact=True)).to_be_visible()
    expect(page.locator('#dialog-content')).to_contain_text('文件共 3 题，新增 3 题，修改 0 题')
    page.screenshot(path=str(OUT / 'desktop-preview.png'), full_page=True)
    page.get_by_role('button', name='确认导入并生效', exact=True).click()
    expect(page.locator('#message')).to_contain_text('题库已导入并生效')
    bank = next(b for b in api.get('/api/banks').json() if b['title'] == title)
    page.locator(f'[data-import="{bank["id"]}"]').click()
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'update.xlsx', 'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'buffer': xlsx})
    expect(page.locator('#dialog-content')).to_contain_text('新增 0 题，修改 3 题')
    page.get_by_role('button', name='保存草稿', exact=True).click()
    expect(page.locator('#message')).to_contain_text('草稿已保存')
    saved = next(b for b in api.get('/api/banks').json() if b['id'] == bank['id'])
    assert saved['draft'] is not None and saved['status'] == 'published'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#admin-directory').select_option(project['id'])
    page.locator(f'[data-publish="{bank["id"]}"]').click()
    expect(page.locator('#message')).to_contain_text('已发布')
    page.locator(f'[data-import="{bank["id"]}"]').click()
    invalid = csv.decode('utf-8-sig').replace('Q2,', 'Q1,').encode('utf-8-sig')
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'bad.csv', 'mimeType': 'text/csv', 'buffer': invalid})
    expect(page.locator('#dialog-content')).to_contain_text('第 3 行 · 编号')
    expect(page.get_by_role('button', name='确认导入并生效', exact=True)).to_have_count(0)
    page.locator('[data-action="close"]').click()
    page.locator(f'[data-import="{bank["id"]}"]').click()
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'mobile.csv', 'mimeType': 'text/csv', 'buffer': csv})
    expect(page.get_by_role('heading', name='导入预览', exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(OUT / 'mobile-preview.png'), full_page=True)
    page.get_by_role('button', name='确认导入并生效', exact=True).click()
    expect(page.locator('#message')).to_contain_text('题库已导入并生效')
    page.get_by_role('button', name='新建题库并上传', exact=True).click()
    recovery = '重试题库' + uuid4().hex[:6]
    page.get_by_label('名称', exact=True).fill(recovery)
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'bad.csv', 'mimeType': 'text/csv', 'buffer': b'invalid header'})
    expect(page.locator('#dialog-content')).to_contain_text('表头必须与模板完全一致')
    expect(page.get_by_role('heading', name='更新题库', exact=True)).to_be_visible()
    page.get_by_label('CSV / XLSX 文件', exact=True).set_input_files({'name': 'retry.csv', 'mimeType': 'text/csv', 'buffer': csv})
    expect(page.get_by_role('heading', name='导入预览', exact=True)).to_be_visible()
    page.get_by_role('button', name='保存草稿', exact=True).click()
    expect(page.locator('#message')).to_contain_text('草稿已保存')
    assert len([b for b in api.get('/api/banks').json() if b['title'] == recovery]) == 1
    assert not errors, errors
    browser.close()
    print('PASS: desktop CSV create/direct publish, Excel update/draft, mobile publish, row error, mobile direct import; no page errors or horizontal overflow')
