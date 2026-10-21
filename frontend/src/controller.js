import { esc } from './escape-html';
import { usersView } from './users-view';
import { adminNavigation, adminOverview, adminView, projectOptions } from './admin-view';
import { learnerNavigation, learnerView } from './learner-view';
import { appSurface, dialogSurface, notify } from './surface';
const app = appSurface, dialog = dialogSurface;
let me = null, banks = [], sessions = [], learning = null, session = null, preview = null;
let actionBusy = false;
let sessionClock = null, timerRefreshing = false, lastTimerRefresh = 0;
let timedPractice = false, practiceMinutes = '30';
let adminStats = null, directories = {years: [], projects: []}, adminDirectory = 'all', showHiddenProjects = false;
let loginRole = location.pathname==='/admin'?'admin':'user';
const defaultPage = () => me?.role==='admin'?'admin':'home';
const rolePages = () => me?.role==='admin'?adminNavigation.map(([id])=>id):[...learnerNavigation.map(([id])=>id),'banks','history','mistakes','reports','practice'];
function roleEntry(){const path=me.role==='admin'?'/admin':'/learn';if(location.pathname!==path)history.replaceState(null,'',path);}

let selectedYear = '', selectedProject = '', selectedCategory = '', selectedMode = '顺序练习', selectionNotice = '';
let selectionOwner = '';
let page = 'home', selectedBank = '', sync = '已同步', busy = false, registerMode = false;

const msg = notify;
async function api(path, method='GET', data=null) {
  const options = {method, credentials:'same-origin', headers:{}};
  if(data instanceof FormData) options.body=data;
  else if(data!==null){options.body=JSON.stringify(data);options.headers['Content-Type']='application/json';}
  let response;
  try {response=await fetch('/api'+path,options);}catch{throw new Error('网络连接失败，选择已在本机保留；联网后重试');}
  const result=await response.json();
  const clockSession=result.session||result;
  if(clockSession.deadline!=null&&clockSession.server_now!=null)sessionClock={id:clockSession.id,remaining:(clockSession.deadline-clockSession.server_now)*1000,received:performance.now()};
  if(!response.ok&&result.session&&session&&result.session.id===session.id){session=result.session;clearLocal();sync='练习已结束';render();}
  if(!response.ok){const error=new Error(typeof result.detail==='string'?result.detail:'请求无效，请检查输入');error.status=response.status;throw error;}
  return result;
}
function draftKey(){return `practice-draft:${me.id}:${session.id}`;}
function localDraft(){try{return JSON.parse(localStorage.getItem(draftKey())||'null');}catch{return null;}}
function saveLocal(d){try{localStorage.setItem(draftKey(),JSON.stringify(d));}catch{msg('本机无法暂存，请保持页面打开',true);}}
function clearLocal(){localStorage.removeItem(draftKey());}
function clearUserDrafts(){for(const key of Object.keys(localStorage))if(key.startsWith(`practice-draft:${me.id}:`))localStorage.removeItem(key);}
function header(){return `<header data-role="${me.role}"><div class="brand">亳州网络部在线刷题 <span class="muted" style="font-size:12px">部门学习平台</span></div><nav class="nav">${(me.role==='admin'?adminNavigation:learnerNavigation).map(([id,title])=>`<button data-page="${id}" class="${page===id?'active':''}">${title}</button>`).join('')}<button data-action="password">修改密码</button><button data-action="logout">退出 ${esc(me.nickname)}</button></nav></header>`;}
function auth(){app.innerHTML=`<main class="auth panel"><h1>${me?'修改临时密码':registerMode?'创建普通人员账号':loginRole==='admin'?'管理员登录':'普通用户登录'}</h1>${me?'<p class="muted">管理员已重置密码，请修改后继续使用。</p>':''}${!me?`<div class="login-roles" data-selected-role="${loginRole}"><button data-login-role="user">普通用户</button><button data-login-role="admin">管理员</button></div>`:''}<form class="form" id="auth">${!me?`<input type="hidden" name="role" value="${loginRole}">`:''}${me?'<label>临时密码<input name="old" type="password" autocomplete="current-password" required></label>':'<label>用户名<input name="username" pattern="[A-Za-z0-9_]{3,32}" autocomplete="username" required placeholder="3–32 位字母、数字或下划线"></label>'}${registerMode?'<label>姓名（必填）<input name="name" autocomplete="name" maxlength="50" required></label>':''}<label>${me?'新密码':'密码'}<input name="password" type="password" autocomplete="${registerMode||me?'new-password':'current-password'}" minlength="10" maxlength="128" required></label><button class="primary">${me?'修改并继续':registerMode?'注册':'登录'}</button></form>${!me&&loginRole==='user'?`<p class="muted">忘记密码请联系管理员。</p><button data-action="toggleAuth">${registerMode?'已有账号，去登录':'没有账号，注册'}</button>`:''}</main>`;}
async function load(){if(me.role==='admin'){[banks,adminStats,directories]=await Promise.all([api('/banks'),api('/admin/summary'),api('/directories')]);if(!['all','unassigned',...directories.years.map(y=>'year:'+y.id),...directories.projects.map(p=>p.id)].includes(adminDirectory))adminDirectory='all';return;}[banks,sessions,learning,directories]=await Promise.all([api('/banks'),api('/sessions'),api('/learning'),api('/learning/directories')]);restoreSelection();}
function stats(){return `<div class="stats"><div><strong>${learning.total}</strong><span class="muted">累计作答</span></div><div><strong>${learning.total?Math.round(learning.correct/learning.total*100)+'%':'—'}</strong><span class="muted">正确率</span></div><div><strong>${learning.coverage}/${learning.available}</strong><span class="muted">题库覆盖</span></div><div><strong>${Object.values(learning.mistakes).filter(x=>!x.mastered).length}</strong><span class="muted">待复习错题</span></div></div>`;}
function projectLabel(project){return project?`${esc(project.year_name)} / ${esc(project.name)}`:'未分配项目';}
function sessionRows(rows){return rows.length?rows.map(s=>`<div class="session-row"><div><strong>${esc(s.title)}</strong><p class="muted">${projectLabel(s.project)} · ${esc(s.mode)} · 已答 ${s.answered}/${s.count} · 正确 ${s.correct} · ${s.ended?'已结束':'进行中'}</p></div><button data-open="${s.id}">${s.ended?'查看记录':'继续练习'}</button></div>`).join(''):'<p class="muted">尚无练习记录，选择题库开始。</p>';}
function selectionKey(){return `practice-selection:${me.id}`;}
function saveSelection(){try{localStorage.setItem(selectionKey(),JSON.stringify({year:selectedYear,project:selectedProject,bank:selectedBank,category:selectedCategory,mode:selectedMode}));}catch{msg('本机无法记住选择，请保持页面打开',true);}}
function availableYears(){return [...directories.years.filter(y=>directories.projects.some(p=>p.year_id===y.id&&(showHiddenProjects||!p.hidden))),...(banks.some(b=>!b.project_id)?[{id:'legacy',name:'未分配年份'}]:[])];}
function availableProjects(){return selectedYear==='legacy'?[{id:'legacy',name:'未分配项目'}]:directories.projects.filter(p=>p.year_id===selectedYear&&(showHiddenProjects||!p.hidden));}
function availableBanks(){return banks.filter(b=>b.status==='published'&&(selectedProject==='legacy'?!b.project_id:b.project_id===selectedProject));}
function restoreSelection(){
  if(selectionOwner!==me.id){
    selectionOwner=me.id;let saved={};try{saved=JSON.parse(localStorage.getItem(selectionKey())||'{}')||{};}catch{}
    selectedYear=saved.year||'';selectedProject=saved.project||'';selectedBank=saved.bank||'';selectedCategory=saved.category||'';
    selectedMode=['顺序练习','随机练习','错题练习','收藏练习'].includes(saved.mode)?saved.mode:'顺序练习';selectionNotice='';
  }
  let invalid=false;
  if(selectedYear&&!availableYears().some(y=>y.id===selectedYear)){selectedYear='';selectedProject='';selectedBank='';invalid=true;}
  if(selectedProject&&!availableProjects().some(p=>p.id===selectedProject)){selectedProject='';selectedBank='';invalid=true;}
  if(selectedBank&&!availableBanks().some(b=>b.id===selectedBank)){selectedBank='';invalid=true;}
  if(selectedCategory&&!(banks.find(b=>b.id===selectedBank)?.categories||[]).includes(selectedCategory)){selectedCategory='';invalid=true;}
  if(invalid){selectionNotice='上次选择已失效，请重新选择题库或知识分类。';saveSelection();}
}
function config(){
  const bank=banks.find(b=>b.id===selectedBank),categories=bank?.categories||[];
  const options=(rows,value)=>rows.map(row=>`<option value="${esc(row.id)}" ${row.id===value?'selected':''}>${esc((row.name||row.title)+(row.hidden?'（已隐藏）':''))}</option>`).join('');
  return `<form id="start" class="panel form"><h2>开始练习</h2><button type="button" data-action="toggleHiddenProjects" aria-pressed="${showHiddenProjects}">${showHiddenProjects?'收起已隐藏项目':'显示已隐藏项目'}</button>${selectionNotice?`<p role="status">${esc(selectionNotice)}</p>`:''}
    <div class="row learner-directory"><label>年份<select id="learner-year" required><option value="">请选择年份</option>${options(availableYears(),selectedYear)}</select></label>
    <label>备考项目<select id="learner-project" ${selectedYear?'':'disabled'} required><option value="">请选择备考项目</option>${options(availableProjects(),selectedProject)}</select></label>
    <label>题库<select name="bank_id" id="bank" ${selectedProject?'':'disabled'} required><option value="">请选择题库</option>${options(availableBanks(),selectedBank)}</select></label></div>
    ${!banks.length?'<p class="muted">暂无已发布题库，请等待管理员发布。</p>':''}
    ${bank?`<p class="muted">${esc(bank.title)} · ${bank.count} 题${bank.count?'':'，暂无可练习题目，请选择其他题库。'}</p>`:''}
    <div class="row">${categories.length?`<label>知识分类<select name="category" id="learner-category"><option value="">全部知识分类</option>${categories.map(c=>`<option value="${esc(c)}" ${c===selectedCategory?'selected':''}>${esc(c)}</option>`).join('')}</select></label>`:''}
    <label>练习方式<select name="mode" id="learner-mode">${['顺序练习','随机练习','错题练习','收藏练习'].map(m=>`<option ${m===selectedMode?'selected':''}>${m}</option>`).join('')}</select></label>
    <label>核对答案<select name="review_mode"><option value="immediate">每题提交后立即核对</option><option value="deferred">全部答完统一核对</option></select></label>
    <label>限时设置<select id="timed-practice"><option value="off" ${timedPractice?'':'selected'}>不限时</option><option value="on" ${timedPractice?'selected':''}>限时练习</option></select></label>
    <label>练习分钟数<input id="practice-minutes" name="duration_minutes" type="number" min="1" max="1440" step="1" value="${esc(practiceMinutes)}" aria-describedby="duration-help" ${timedPractice?'required':'disabled'}></label>
    <p id="duration-help" class="muted">限时可填 1–1440 整数分钟。离开仍计时；到时结束，未提交题目算未答。</p>
    <label>题量<select name="amount">${['10','20','50','全部'].map(a=>`<option ${a==='20'?'selected':''}>${a}</option>`).join('')}</select></label></div>
    <label><span><input style="width:auto" type="checkbox" name="restart"> 顺序练习从头开始</span></label>
    <p id="start-error" role="alert"></p><button class="primary" ${bank?.count?'':'disabled'}>开始练习</button></form>`;
}
function practice(){
  const q=session.questions[session.index],a=session.answers[String(session.index)],pending=session.ended?null:localDraft();
  const chosen=pending?.index===session.index?pending.selected:a?.selected||session.drafts[String(session.index)]||[];
  const deferred=session.review_mode==='deferred';
  const selectedCount=Object.values(session.drafts).filter(x=>x.length).length;
  const answered=Object.keys(session.answers).length,correct=Object.values(session.answers).filter(x=>x.correct).length,total=session.questions.length;
  return `<div class="practice-summary"><div class="topbar-row"><div class="practice-title">亳州网络部在线刷题<span class="sub">共 <b>${total}</b> 题</span></div><div class="practice-metrics">${session.deadline!=null?`<span role="timer" aria-label="练习剩余时间" id="practice-countdown">${countdownText()}</span>`:''}<span>${deferred&&!session.ended?'已选':'进度'} <b>${deferred&&!session.ended?selectedCount:answered}/${total}</b></span><span>答对 <b>${correct}/${answered}</b></span><span>正确率 <b>${answered?Math.round(correct/answered*100)+'%':'--'}</b></span><span class="sync-label">${esc(sync)} · ${deferred?'统一核对':'立即核对'}</span></div></div><progress value="${deferred&&!session.ended?selectedCount:answered}" max="${total}"></progress></div>
  ${pending?`<div class="pending">本机有未同步选择。${esc(pending.selected.join('、')||'未选')}<div class="row"><button data-action="retry">重试保存</button><button data-action="refreshSession">读取服务器最新进度</button><button data-action="discard">放弃本机选择</button></div></div>`:''}
  <div class="practice-grid"><section class="question panel" data-question-type="${esc(q.type)}">
  ${session.ended?`<div class="ended"><h2>本次练习已结束</h2><p>已答 ${answered}/${total} 题，正确 ${correct} 题，未答 ${total-answered} 题。未提交题目不计分。</p></div>`:''}
  <div class="question-meta"><div><span class="question-type" data-type="${esc(q.type)}">${esc(q.type)}</span><span class="muted">第 ${session.index+1} 题 / ${total}</span></div><button data-action="favorite">${learning.favorites.includes(q.id)?'★ 已收藏':'☆ 收藏题目'}</button></div>
  <p class="question-category muted">${esc(session.title)} · ${esc(q.category||'未分类')}</p><h2 class="question-stem">${esc(q.stem)}</h2>
  ${Object.entries(q.options).map(([key,text])=>`<button class="option ${chosen.includes(key)?'selected':''} ${a&&q.answer.includes(key)?'correct':''} ${a&&chosen.includes(key)&&!q.answer.includes(key)?'wrong':''}" data-option="${key}" aria-pressed="${chosen.includes(key)}" ${a||session.ended||busy?'disabled':''}><span class="letter">${key}</span><span class="option-text">${esc(text)}</span></button>`).join('')}
  ${a?`<div class="feedback ${a.correct?'feedback-correct':'feedback-wrong'}"><strong>${a.correct?'回答正确':'回答错误，已加入错题'}</strong><p>正确答案：${esc(q.answer.join('、'))}</p><div class="answer-explanation"><strong>答案解析</strong><p>${esc(q.explanation||'暂无解析')}</p></div><button data-action="report">反馈题目问题</button></div>`:''}
  <div class="actions"><button data-jump="${session.index-1}" ${session.index===0||busy||pending?'disabled':''}>上一题</button>${!session.ended?`<button class="primary" data-action="${deferred?(session.index===total-1?'reviewAll':'next'):(a?'next':'submit')}" ${busy||pending||(!a&&!chosen.length)?'disabled':''}>${deferred?(session.index===total-1?'统一核对答案':'保存并下一题'):(a?(session.index===total-1?'结束并查看结果':'下一题'):'提交答案')}</button>`:`<button class="primary" data-jump="${session.index+1}" ${session.index===total-1?'disabled':''}>下一题</button>`}</div></section>
  <aside class="panel answer-card"><h3>题卡导航（点击跳转）</h3><details class="practice-menu"><summary>练习设置与功能</summary><nav>${!session.ended?`<button class="finish-menu" data-action="finish" ${busy||pending?'disabled':''}>结束练习</button>`:''}<button data-page="home">顺序 / 随机 / 收藏练习</button><button data-page="mistakes">错题与收藏</button><button data-page="history">练习历史</button><button data-action="password">修改密码</button><button data-action="logout">退出账号</button></nav></details><div class="numbers">${session.questions.map((_,i)=>{const answer=session.answers[i],selected=deferred&&!answer&&!!session.drafts[String(i)]?.length;return `<button data-jump="${i}" class="${i===session.index?'current':''} ${answer?(answer.correct?'number-correct':'number-wrong'):selected?'number-selected':''}" ${busy||pending?'disabled':''} ${i===session.index?'aria-current="step"':''} aria-label="第${i+1}题，${answer?(answer.correct?'答对':'答错'):selected?'已选择，待核对':'未答'}">${i+1}${answer?`<span aria-hidden="true">${answer.correct?'✓':'×'}</span>`:''}</button>`;}).join('')}</div><div class="answer-legend"><span>○ 未答</span><span class="legend-correct">✓ 答对</span><span class="legend-wrong">× 答错</span>${deferred?'<span>蓝底为已选待核对</span>':''}<span>描边为当前题</span></div></aside></div>`;
}



function render(){if(!me||me.must_change){auth();return;}roleEntry();if(!rolePages().includes(page))page=defaultPage();if(me.role!=='admin'){learnerView({me,page,banks:banks.filter(b=>showHiddenProjects||!directories.projects.some(p=>p.hidden&&p.id===b.project_id)),sessions,learning,session,app,header,auth,practice,stats,sessionRows,config});return;}const content=page==='overview'?adminOverview(adminStats):page==='admin'?adminView(banks,directories,adminDirectory,showHiddenProjects):'<p>正在加载…</p>';app.innerHTML=header()+`<main>${content}</main>`;}

function modal(content){dialog.innerHTML=content;dialog.showModal();}
function formModal(title,fields,id){modal(`<h2>${title}</h2><form class="form" id="${id}">${fields}<div class="dialog-actions"><button class="primary">确认</button><button type="button" data-action="close">取消</button></div></form>`);}
async function openSession(id){session=await api('/sessions/'+id);if(session.ended)clearLocal();sync='已同步';msg('');page='practice';history.replaceState(null,'','#practice');render();}
async function writeDraft(d){saveLocal(d);busy=true;sync='正在同步';render();try{session=await api('/sessions/'+session.id,'PATCH',d);clearLocal();sync='已同步';msg('');}catch(e){sync=e.status===409?'进度冲突':'未同步';msg(e.message,true);}finally{busy=false;render();}}
async function displayAdminList(kind){const rows=await api('/'+kind);if(kind==='users'){app.innerHTML=header()+`<main>${usersView(rows)}</main>`;return;}app.innerHTML=header()+`<main><h1>纠错反馈</h1><section class="panel">${rows.map(r=>`<div class="session-row"><div><strong>${esc(r.type)}</strong><p>${esc(r.question.stem)}</p><p>${esc(r.text)}</p><span>${esc(r.status)}</span></div>${me.role==='admin'?`<div class="row"><button data-resolve="${r.id}" data-status="已处理">标记已处理</button><button data-resolve="${r.id}" data-status="不采纳">不采纳</button></div>`:''}</div>`).join('')||'<p>暂无记录。</p>'}</section></main>`;}
async function navigate(p){page=rolePages().includes(p)?p:defaultPage();location.hash=page;await load();render();if(['users','reports'].includes(page))await displayAdminList(page);}
function batchInputs(bid){return Array.from(document.querySelectorAll('input[data-select-question]')).filter(input=>input.dataset.selectQuestion===bid&&!input.disabled);}
function selectionCount(bid){const inputs=batchInputs(bid),count=inputs.filter(input=>input.checked).length;const label=Array.from(document.querySelectorAll('[data-selection-count]')).find(e=>e.dataset.selectionCount===bid);if(label)label.textContent=`已选 ${count} 题`;const all=Array.from(document.querySelectorAll('[data-select-all]')).find(e=>e.dataset.selectAll===bid);if(all){all.checked=!!inputs.length&&count===inputs.length;all.indeterminate=count>0&&count<inputs.length;}}
document.addEventListener('change',event=>{const target=event.target;if(target.dataset.selectAll){batchInputs(target.dataset.selectAll).forEach(input=>input.checked=target.checked);selectionCount(target.dataset.selectAll);}else if(target.dataset.selectQuestion)selectionCount(target.dataset.selectQuestion);});
document.addEventListener('change',e=>{if(e.target.id==='admin-directory'){adminDirectory=e.target.value;render();}});
document.addEventListener('change',e=>{
  const id=e.target.id,value=e.target.value;
  if(id==='timed-practice'){timedPractice=value==='on';const input=document.querySelector('#practice-minutes');input.disabled=!timedPractice;input.required=timedPractice;return;}
  if(id==='practice-minutes'){practiceMinutes=value;return;}
  if(!['learner-year','learner-project','bank','learner-category','learner-mode'].includes(id))return;
  selectionNotice='';msg('');
  const startError=document.querySelector('#start-error');if(startError)startError.textContent='';
  if(id==='learner-year'){selectedYear=value;selectedProject='';selectedBank='';selectedCategory='';}
  if(id==='learner-project'){selectedProject=value;selectedBank='';selectedCategory='';}
  if(id==='bank'){selectedBank=value;selectedCategory='';}
  if(id==='learner-category')selectedCategory=value;
  if(id==='learner-mode')selectedMode=value;
  saveSelection();if(['learner-year','learner-project','bank'].includes(id))render();
});
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b||b.disabled||actionBusy)return;actionBusy=true;try{if(b.dataset.action==='toggleHiddenProjects'){showHiddenProjects=!showHiddenProjects;if(me.role==='admin'){if(!showHiddenProjects&&directories.projects.some(p=>p.id===adminDirectory&&p.hidden))adminDirectory='all';}else restoreSelection();render();return;}if(b.dataset.hideProject){const project=directories.projects.find(p=>p.id===b.dataset.hideProject);await api('/projects/'+project.id,'PATCH',{hidden:!project.hidden});if(!project.hidden&&!showHiddenProjects)adminDirectory='all';await navigate('admin');msg(project.hidden?'项目已恢复显示':'项目已隐藏；显示已隐藏项目可再次找到，题库与学习记录保留');return;}if(b.dataset.archiveBank){if(!confirm('归档后不能发起新练习；已有练习可继续，历史、错题和收藏保留。确认归档？'))return;const bank=banks.find(x=>x.id===b.dataset.archiveBank);await api('/banks/'+bank.id,'PATCH',{revision:bank.revision,status:'archived'});await navigate('admin');msg('题库已归档，历史记录保留');return;}if(b.dataset.directory){adminDirectory=b.dataset.directory;render();return;}if(b.dataset.renameDirectory){const [kind,id]=b.dataset.renameDirectory.split(':'),item=directories[kind].find(x=>x.id===id);formModal('修改目录名称',`<label>名称<input name="name" value="${esc(item.name)}" maxlength="100" required></label>`,'directoryRename:'+kind+':'+id);return;}if(b.dataset.deleteDirectory){const [kind,id]=b.dataset.deleteDirectory.split(':');if(!confirm('仅可删除完全空的目录。有项目或题库（包括归档题库）时会拒绝删除。继续吗？'))return;await api('/'+kind+'/'+id,'DELETE');await navigate('admin');msg('空目录已删除');return;}if(b.dataset.moveBank){const bank=banks.find(x=>x.id===b.dataset.moveBank);formModal('移动题库',`<p>移动后题目、练习和个人记录保留。</p><label>目标年份与项目<select name="project_id" required><option value="">请选择项目</option>${projectOptions(directories,bank.project_id)}</select></label><input type="hidden" name="revision" value="${bank.revision}">`,'moveBank:'+bank.id);return;}if(b.dataset.deleteSelected||b.dataset.deleteAll){const bid=b.dataset.deleteSelected||b.dataset.deleteAll,bank=banks.find(x=>x.id===bid),all=!!b.dataset.deleteAll;const ids=batchInputs(bid).filter(i=>i.checked).map(i=>i.dataset.qid);const count=all?(bank.draft||bank.questions).filter(q=>!q.archived).length:ids.length;if(!count){msg('请先勾选要删除的题目',true);return;}formModal(all?'删除全部题目':'删除所选题目',`<p>将删除「${esc(bank.title)}」中的 ${count} 道题。</p><p>保存为归档草稿，确认发布后生效；历史作答和已开始的练习保留。</p><input type="hidden" name="revision" value="${bank.revision}"><input type="hidden" name="all" value="${all}"><input type="hidden" name="ids" value="${esc(JSON.stringify(ids))}">`,'batchDelete:'+bid);return;}if(b.dataset.loginRole){loginRole=b.dataset.loginRole;registerMode=false;history.replaceState(null,'',loginRole==='admin'?'/admin':'/learn');msg('');auth();return;}if(b.dataset.page){await navigate(b.dataset.page);return;}if(b.dataset.studyMode){selectedMode=b.dataset.studyMode;saveSelection();await navigate('home');return;}if(b.dataset.open){await openSession(b.dataset.open);return;}if(b.dataset.selectBank){selectedBank=b.dataset.selectBank;const bank=banks.find(x=>x.id===selectedBank);selectedProject=bank.project_id||'legacy';selectedYear=directories.projects.find(p=>p.id===selectedProject)?.year_id||'legacy';selectedCategory='';saveSelection();page='home';render();return;}if(b.dataset.option){const i=session.index,q=session.questions[i],chosen=session.drafts[String(i)]||[];const selected=q.type==='多选'?(chosen.includes(b.dataset.option)?chosen.filter(x=>x!==b.dataset.option):[...chosen,b.dataset.option]):[b.dataset.option];await writeDraft({revision:session.revision,index:i,selected});return;}if(b.dataset.jump!==undefined){const i=Number(b.dataset.jump);if(session.ended){session.index=i;render();}else await writeDraft({revision:session.revision,index:i,selected:session.drafts[String(i)]||[]});return;}if(b.dataset.mastered){await api('/mastered','POST',{question_id:b.dataset.mastered,value:!learning.mistakes[b.dataset.mastered].mastered});await navigate('mistakes');return;}if(b.dataset.import){openImport(b.dataset.import);return;}if(b.dataset.publish){const bank=banks.find(x=>x.id===b.dataset.publish);await api('/banks/'+bank.id+'/publish','POST',{revision:bank.revision});await navigate('admin');msg('已发布');return;}if(b.dataset.offline){if(!confirm('下架后不能开始新练习，已有记录保留。继续吗？'))return;const bank=banks.find(x=>x.id===b.dataset.offline);await api('/banks/'+bank.id,'PATCH',{revision:bank.revision,status:'offline'});await navigate('admin');return;}if(b.dataset.rename){const bank=banks.find(x=>x.id===b.dataset.rename);formModal('修改题库名称',`<label>名称<input name="title" value="${esc(bank.title)}" maxlength="100" required></label>`,'rename:'+bank.id);return;}if(b.dataset.archive){const bank=banks.find(x=>x.id===b.dataset.archive);await api('/banks/'+bank.id+'/archive','POST',{revision:bank.revision,question_id:b.dataset.qid});await navigate('admin');msg('已保存归档草稿，发布后生效');return;}if(b.dataset.edit){const bank=banks.find(x=>x.id===b.dataset.edit),q=(bank.draft||bank.questions).find(x=>x.code===b.dataset.code);const fields=[['编号',q.code],['题型',q.type],['题干',q.stem],...['A','B','C','D','E'].map(k=>[k,q.type==='判断'?'':q.options[k]||'']),['答案',q.type==='判断'?(q.answer[0]==='A'?'正确':'错误'):q.answer.join('|')],['解析',q.explanation],['分类',q.category],['标签',q.tags.join('|')]];formModal('编辑题目（保存为草稿）',fields.map(([k,v])=>`<label>${k}<textarea name="${k}" ${k==='编号'?'readonly':''}>${esc(v)}</textarea></label>`).join(''),'edit:'+bank.id);return;}if(b.dataset.deleteUser){formModal('彻底删除账号',`<p>确认彻底删除账号「${esc(b.dataset.username)}」？此操作无法撤销。</p><p>将删除账号、全部登录凭证、个人练习与历史、错题和收藏，所有设备的旧登录立即失效。</p><p>公共题库和其他用户的账号、记录不受影响。题目纠错保留并移除提交者关联，操作审计保留。</p><p>仅需禁止访问并保留学习记录时，请取消并使用停用账号。</p><label><input type="checkbox" name="confirm" required>我已了解影响，确认永久删除</label>`,'deleteUser:'+b.dataset.deleteUser);return;}if(b.dataset.disableUser){formModal('停用账号',`<p>确认停用 ${esc(b.dataset.username)}？所有设备将退出登录，个人练习、历史、错题和收藏继续保留。</p>`,'disableUser:'+b.dataset.disableUser);return;}if(b.dataset.reset){formModal('管理员重置密码','<p>请先站外确认身份。重置会退出所有设备，下次登录必须改密。</p><label>临时密码<input name="password" type="password" minlength="10" maxlength="128" required></label>','reset:'+b.dataset.reset);return;}if(b.dataset.resolve){await api('/reports/'+b.dataset.resolve,'PATCH',{status:b.dataset.status});await displayAdminList('reports');return;}switch(b.dataset.action){case'toggleAuth':registerMode=!registerMode;auth();break;case'close':dialog.close();break;case'logout':clearUserDrafts();await api('/logout','POST');me=null;session=null;selectionOwner='';auth();break;case'password':formModal('修改密码','<label>原密码<input name="old" type="password" required></label><label>新密码<input name="password" type="password" minlength="10" maxlength="128" required></label>','password');break;case'newYear':formModal('新建年份','<label>年份名称<input name="name" maxlength="100" placeholder="例如 2026" required></label>','newYear');break;case'newProject':formModal('新建备考项目',`<label>所属年份<select name="year_id" required>${directories.years.map(y=>`<option value="${y.id}" ${adminDirectory==='year:'+y.id?'selected':''}>${esc(y.name)}</option>`).join('')}</select></label><label>项目名称<input name="name" maxlength="100" required></label>`,'newProject');break;case'newBank':formModal('新建题库并上传',`<label>名称<input name="title" maxlength="100" required></label><label>所属年份与项目<select name="project_id" required><option value="">请选择项目</option>${projectOptions(directories,adminDirectory)}</select></label><label>CSV / XLSX 文件<input name="file" type="file" accept=".csv,.xlsx" required></label><p class="muted">选择文件后自动检查并预览。分类可留空。</p>${directories.projects.length?'':'<p>请先新建年份和备考项目。</p>'}`,'newBank');break;case'favorite':{const q=session.questions[session.index];await api('/favorite','POST',{question_id:q.id,value:!learning.favorites.includes(q.id)});learning=await api('/learning');render();break;}case'reviewAll':session=await api('/sessions/'+session.id+'/review','POST',{revision:session.revision});learning=await api('/learning');render();break;case'submit':session=await api('/sessions/'+session.id+'/answer','POST',{revision:session.revision,index:session.index,selected:session.drafts[String(session.index)]||[]});learning=await api('/learning');render();break;case'next':if(session.index===session.questions.length-1){session=await api('/sessions/'+session.id+'/finish','POST',{revision:session.revision});render();}else await writeDraft({revision:session.revision,index:session.index+1,selected:session.drafts[String(session.index+1)]||[]});break;case'finish':if(confirm(session.review_mode==='deferred'?'结束并放弃本次核对？已选择但未统一核对的题目不计分。':'结束本次练习？未提交题目不计分。')){session=await api('/sessions/'+session.id+'/finish','POST',{revision:session.revision});render();}break;case'retry':{const d=localDraft();if(d){if(d.revision!==session.revision){if(!confirm('已读取较新服务器状态。确定以本机选择修改对应题目？'))break;d.revision=session.revision;}await writeDraft(d);}break;}case'refreshSession':session=await api('/sessions/'+session.id);sync='服务器状态已读取，本机选择仍保留';render();msg('请比较本机选择与服务器进度；可放弃本机选择，或确认后保存。');break;case'discard':clearLocal();session=await api('/sessions/'+session.id);sync='已同步';msg('');render();break;case'report':formModal('反馈题目问题','<label>问题类型<select name="type"><option>答案有误</option><option>解析有误</option><option>题干有误</option><option>选项有误</option></select></label><label>说明<textarea name="text" maxlength="2000" required></textarea></label>','report');break;case'publishImport':case'commitImport':{const publish=b.dataset.action==='publishImport';await api('/imports/'+preview.id+'/commit','POST',{publish});dialog.close();await navigate('admin');msg(publish?'题库已导入并生效':'草稿已保存，确认发布后用户可见');break;}}}catch(error){msg(error.message,true);}finally{actionBusy=false;}});
function openImport(bid){preview=null;formModal('更新题库',`<p>更新「${esc(banks.find(x=>x.id===bid).title)}」：按编号新增或修改，缺失旧题保留。</p>${banks.find(x=>x.id===bid).draft?'<p class="muted">此题库有未发布草稿；本次将与草稿合并，直接生效会一并发布已有草稿。</p>':''}<label>CSV / XLSX 文件<input name="file" type="file" accept=".csv,.xlsx" required></label>`,'import:'+bid);}
function csvCell(text){return '"'+String(text||'').replaceAll('"','""')+'"';}
function showPreview(p){preview=p;modal(`<h2>导入预览</h2>${p.errors.length?`<div class="error">${p.errors.map(e=>`<p>第 ${e.row} 行 · ${esc(e.field)}：${esc(e.message)}</p>`).join('')}</div>`:`<p>校验通过：文件共 ${p.questions.length} 题，新增 ${p.added} 题，修改 ${p.updated} 题。</p><div class="scroll"><table class="table"><tr><th>编号</th><th>题型</th><th>题干</th><th>答案</th></tr>${p.questions.slice(0,10).map(q=>`<tr><td>${esc(q.code)}</td><td>${esc(q.type)}</td><td>${esc(q.stem)}</td><td>${esc(q.answer.join('|'))}</td></tr>`).join('')}</table></div><p class="muted">预览前10题。全部校验通过，缺少的旧题保留。</p><div class="row"><button class="primary" data-action="publishImport">确认导入并生效</button><button data-action="commitImport">保存草稿</button></div>`}<button data-action="close">关闭</button>`);}
async function handleAccountForm(form, body) {
  if (form.id==='auth') {
    if(me){await api('/password','POST',body);clearUserDrafts();me=await api('/me');}else if(registerMode){await api('/register','POST',body);registerMode=false;auth();msg('注册成功，请登录');return;}else {me=await api('/login','POST',body);showHiddenProjects=false;}await load();page=defaultPage();render();
  }
  else if (form.id==='password') {
    await api('/password','POST',body);clearUserDrafts();dialog.close();me=await api('/me');await navigate(defaultPage());
  }
  else if (form.id.startsWith('deleteUser:')) {
    await api('/users/'+form.id.split(':')[1],'DELETE',{confirm:body.confirm==='on'});dialog.close();await navigate('users');msg('账号及个人学习记录已彻底删除');
  }
  else if (form.id.startsWith('disableUser:')) {
    await api('/users/'+form.id.split(':')[1]+'/disable','POST');dialog.close();await navigate('users');msg('账号已停用，个人学习记录保留');
  }
  else if (form.id.startsWith('reset:')) {
    await api('/users/'+form.id.split(':')[1]+'/reset','POST',body);dialog.close();msg('密码已重置；请通过可信方式告知本人');
  }
}

async function handlePracticeForm(form, body) {
  if (form.id==='start') {
    body.restart=!!body.restart;if(timedPractice){body.duration_minutes=Number(body.duration_minutes);if(!Number.isInteger(body.duration_minutes)||body.duration_minutes<1||body.duration_minutes>1440)throw new Error('练习时长需为 1–1440 的整数分钟');}else delete body.duration_minutes;saveSelection();session=await api('/sessions','POST',body);page='practice';history.replaceState(null,'','#practice');sync='已同步';render();
  }
  else if (form.id==='report') {
    await api('/reports','POST',{...body,session_id:session.id,index:session.index});dialog.close();msg('反馈已提交');
  }
}

async function handleDirectoryForm(form, body) {
  if (form.id==='newYear'||form.id==='newProject') {
    const kind=form.id==='newYear'?'years':'projects';const item=await api('/'+kind,'POST',body);adminDirectory=kind==='years'?'year:'+item.id:item.id;dialog.close();await navigate('admin');
  }
  else if (form.id.startsWith('directoryRename:')) {
    const [,kind,id]=form.id.split(':');await api('/'+kind+'/'+id,'PATCH',body);dialog.close();await navigate('admin');
  }
  else if (form.id.startsWith('moveBank:')) {
    await api('/banks/'+form.id.split(':')[1],'PATCH',{project_id:body.project_id,revision:Number(body.revision)});adminDirectory=body.project_id;dialog.close();await navigate('admin');msg('题库已移动，学习记录保留');
  }
}

async function handleImportForm(form, body) {
  if (form.id.startsWith('batchDelete:')) {
    const result=await api('/banks/'+form.id.split(':')[1]+'/archive-batch','POST',{revision:Number(body.revision),...(body.all==='true'?{all:true}:{question_ids:JSON.parse(body.ids)})});dialog.close();await navigate('admin');msg(`已删除 ${result.archived} 题并保存为草稿，请确认发布后生效`);
  }
  else if (form.id==='newBank') {
    const upload=new FormData(form),bank=await api('/banks','POST',{title:body.title,project_id:body.project_id});adminDirectory=body.project_id;banks.push(bank);render();openImport(bank.id);const p=await api('/banks/'+bank.id+'/preview','POST',upload);dialog.close();showPreview(p);
  }
  else if (form.id.startsWith('import:')) {
    const p=await api('/banks/'+form.id.split(':')[1]+'/preview','POST',new FormData(form));dialog.close();showPreview(p);
  }
  else if (form.id.startsWith('edit:')) {
    const header=['编号','题型','题干','A','B','C','D','E','答案','解析','分类','标签'];const text=header.join(',')+'\n'+header.map(k=>csvCell(body[k])).join(',');const f=new FormData();f.append('file',new Blob(['\uFEFF'+text],{type:'text/csv'}),'edit.csv');const p=await api('/banks/'+form.id.split(':')[1]+'/preview','POST',f);dialog.close();showPreview(p);
  }
  else if (form.id.startsWith('rename:')) {
    const bank=banks.find(b=>b.id===form.id.split(':')[1]);await api('/banks/'+bank.id,'PATCH',{...body,revision:bank.revision});dialog.close();await navigate('admin');
  }
}

const formHandlers = [
  { accepts: form => (form.id==='auth') || (form.id==='password') || (form.id.startsWith('deleteUser:')) || (form.id.startsWith('disableUser:')) || (form.id.startsWith('reset:')), submit: handleAccountForm },
  { accepts: form => (form.id==='start') || (form.id==='report'), submit: handlePracticeForm },
  { accepts: form => (form.id==='newYear'||form.id==='newProject') || (form.id.startsWith('directoryRename:')) || (form.id.startsWith('moveBank:')), submit: handleDirectoryForm },
  { accepts: form => (form.id.startsWith('batchDelete:')) || (form.id==='newBank') || (form.id.startsWith('import:')) || (form.id.startsWith('edit:')) || (form.id.startsWith('rename:')), submit: handleImportForm }
];
document.addEventListener('submit', async e => {
  e.preventDefault();
  const form=e.target, body=Object.fromEntries(new FormData(form));
  const button=e.submitter||form.querySelector('button[type="submit"],button:not([type])');
  button.disabled=true;
  try {
    const handler=formHandlers.find(handler=>handler.accepts(form));
    if(handler)await handler.submit(form,body);
  } catch(error) {
    msg(error.message,true);
    if(form.id==='start')form.querySelector('#start-error').textContent=error.message;
  } finally {
    button.disabled=false;
  }
});
window.addEventListener('online',()=>{if(page==='practice'){sync='网络已恢复，请重试未同步操作';render();}});
window.addEventListener('offline',()=>{if(page==='practice'){sync='离线，未同步';render();}});
async function boot(){try{me=await api('/me');if(me.must_change){auth();return;}await load();page=defaultPage();const requested=location.hash.slice(1);if(rolePages().includes(requested)&&requested!=='practice')page=requested;render();if(['users','reports'].includes(page))await displayAdminList(page);}catch{me=null;auth();}}
boot();

document.addEventListener('change',e=>{if(e.target.matches('input[type="file"][name="file"]')&&e.target.files.length){e.target.form.requestSubmit();}});


function countdownText(){
  if(session.ended)return '练习已结束';
  const seconds=Math.max(0,Math.ceil((sessionClock?.id===session.id?sessionClock.remaining-(performance.now()-sessionClock.received):0)/1000));
  return `剩余 ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
}
async function updatePracticeTimer(force=false){
  if(!me||page!=='practice'||!session||session.ended||session.deadline==null)return;
  const label=document.querySelector('#practice-countdown');if(label)label.textContent=countdownText();
  if(timerRefreshing||actionBusy||busy||(!force&&performance.now()-lastTimerRefresh<3000))return;
  timerRefreshing=true;lastTimerRefresh=performance.now();const id=session.id;
  try{
    const latest=await api('/sessions/'+id);
    if(page!=='practice'||session?.id!==id||latest.revision<session.revision||actionBusy||busy)return;
    if(latest.ended){session=latest;clearLocal();sync='练习已结束';learning=await api('/learning');render();}
    else if(latest.revision>session.revision){session=latest;render();}
  }catch(error){if(label)label.textContent=countdownText()+'（连接后确认结果）';}
  finally{timerRefreshing=false;}
}
setInterval(()=>updatePracticeTimer(),250);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)updatePracticeTimer(true);});
window.addEventListener('online',()=>updatePracticeTimer(true));
