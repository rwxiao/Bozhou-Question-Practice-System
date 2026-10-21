const fs=require('node:fs');
const assert=require('node:assert/strict');
const {chromium}=require('E:/Project/person_Project/network-workbench-server-0.2.0/node_modules/playwright-core');
const origin='https://quiz.onwarddesk.asia';
const accounts=JSON.parse(fs.readFileSync('E:/Project/刷题/data/local-access.json','utf8'));
async function login(context,credentials,role){
  const page=await context.newPage();
  await page.goto(origin+(role==='admin'?'/admin':'/learn'),{waitUntil:'networkidle'});
  await page.locator('input[name="username"]').fill(credentials.username);
  await page.locator('input[name="password"]').fill(credentials.password);
  await page.locator('form#auth button').click();
  await page.locator('header.site-header').waitFor();
  const response=await context.request.get(origin+'/api/me');
  assert.equal(response.status(),200);
  assert.equal((await response.json()).role,role);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  return page;
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--no-proxy-server','--disable-quic']});
  try{
    const adminContext=await browser.newContext({viewport:{width:1440,height:1000}});
    const admin=await login(adminContext,accounts,'admin');
    const summary=await adminContext.request.get(origin+'/api/admin/summary');
    assert.equal(summary.status(),200);
    await admin.screenshot({path:'E:/Project/刷题/.scratch/deploy/live-admin.png',fullPage:true});
    const a=await browser.newContext({viewport:{width:1440,height:1000}});
    const b=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const desktop=await login(a,accounts.learner,'user');
    const mobile=await login(b,accounts.learner,'user');
    const contract=await a.request.get(origin+'/openapi.json');
    assert.equal(contract.status(),200);
    assert.ok((await contract.json()).paths['/api/sessions/{sid}/review']);
    assert.equal(await desktop.locator('[name="review_mode"]').count(),1);
    for(const route of ['/api/banks','/api/sessions','/api/learning']){
      const first=await a.request.get(origin+route),second=await b.request.get(origin+route);
      assert.equal(first.status(),200);assert.equal(second.status(),200);
      assert.deepEqual(await first.json(),await second.json());
    }
    await desktop.reload({waitUntil:'networkidle'});
    await desktop.locator('header.site-header').waitFor();
    assert.equal((await a.request.get(origin+'/api/admin/summary')).status(),403);
    await mobile.screenshot({path:'E:/Project/刷题/.scratch/deploy/live-mobile.png',fullPage:true});
    const hasSession=await desktop.locator('[data-open]').count();
    if(hasSession){
      await desktop.locator('[data-open]').first().click();
      await desktop.locator('.question-stem').waitFor();
      await mobile.locator('[data-open]').first().click();
      await mobile.locator('.question-stem').waitFor();
      assert.equal(await desktop.locator('.question-stem').innerText(),await mobile.locator('.question-stem').innerText());
      assert.equal(await mobile.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
      await desktop.screenshot({path:'E:/Project/刷题/.scratch/deploy/live-practice-desktop.png',fullPage:true});
      await mobile.screenshot({path:'E:/Project/刷题/.scratch/deploy/live-practice-mobile.png',fullPage:true});
    }
    const cookies=await a.cookies(origin),session=cookies.find(c=>c.name==='session');
    assert.ok(session&&session.secure&&session.httpOnly);
    for(const ctx of [adminContext,a,b]){
      const out=await ctx.request.post(origin+'/api/logout',{headers:{Origin:origin}});
      assert.equal(out.status(),200);
    }
    console.log(JSON.stringify({https:true,adminLogin:true,learnerLogin:true,twoBrowserContextsSameData:true,refreshSession:true,roleIsolation:true,secureHttpOnlyCookie:true,mobileOverflow:false,deferredReviewContract:true,practicePage:hasSession?'passed':'noExistingSession'}));
  }finally{await browser.close();}
})().catch(()=>{console.error('Live verification failed; inspect page and server logs without printing credentials.');process.exitCode=1;});
