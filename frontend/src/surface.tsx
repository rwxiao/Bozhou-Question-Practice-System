/** React/shadcn rendering boundary for the existing command controller. */
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import parse, { attributesToProps, domToReact, Element, type DOMNode, type HTMLReactParserOptions } from 'html-react-parser';
import { useState, type ReactNode, type ComponentProps } from 'react';
import { Network, LayoutDashboard, Library, History, Bookmark, MessageSquare, Settings, Users, LogOut, LockKeyhole, ArrowRight, FileQuestion, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Field, FieldGroup, FieldLabel, FieldSet, FieldLegend } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { NativeSelect } from '@/components/ui/native-select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Table, TableHeader, TableBody, TableRow, TableCell, TableHead } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from '@/components/ui/empty';
import { cn } from '@/lib/utils';

const root = createRoot(document.getElementById('app')!);
const messageRoot = createRoot(document.getElementById('message')!);
const modalHost = document.createElement('div');
document.body.append(modalHost);
const modalRoot = createRoot(modalHost);
let modalHTML = '', modalOpen = false, modalMessage: ReactNode = null;
const icons: Record<string, typeof Network> = {home:LayoutDashboard,banks:Library,history:History,mistakes:Bookmark,reports:MessageSquare,admin:Settings,users:Users};
const children = (node: Element) => domToReact(node.children as DOMNode[], options);
function has(node: Element, name: string) { return (node.attribs.class || '').split(' ').includes(name); }
function text(node: DOMNode): string { return node.type === 'text' ? node.data : node instanceof Element ? node.children.map(n=>text(n as DOMNode)).join('') : ''; }
function ancestor(node: Element, name: string): Element | null { let p=node.parent; while(p){if(p instanceof Element && p.name===name)return p;p=p.parent;}return null; }
function inputId(node: Element) { return node.attribs.id || `${ancestor(node,'form')?.attribs.id || 'control'}-${node.attribs.name || 'value'}`; }

const themeOptions = [{id:'cmcc',name:'移动蓝 · 蓝绿配色'},{id:'teal',name:'青绿 · 清新学习'},{id:'indigo',name:'靛紫 · 专注学习'},{id:'navy',name:'海军蓝 · 沉稳办公'}];
function storedTheme() {try{const theme=localStorage.getItem('bozhou-ui-theme-v2');return themeOptions.some(t=>t.id===theme)?theme!:'cmcc';}catch{return 'cmcc';}}
function applyTheme(theme:string){document.documentElement.dataset.theme=theme;const background:Record<string,string>={cmcc:'#f3f8fc',teal:'#f4f8f7',indigo:'#f5f5fa',navy:'#f5f7fa'};document.querySelector('meta[name=theme-color]')?.setAttribute('content',background[theme]||background.cmcc);}
applyTheme(storedTheme());
function ThemeSelect(){
 const [theme,setTheme]=useState(storedTheme);
 return <div className="theme-picker"><label htmlFor="page-palette">配色</label><NativeSelect id="page-palette" value={theme} onChange={event=>{const next=event.target.value;setTheme(next);applyTheme(next);try{localStorage.setItem('bozhou-ui-theme-v2',next);}catch{/* Theme still applies in memory. */}}}>{themeOptions.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</NativeSelect></div>;
}

function action(node: Element) {
  const props = attributesToProps(node.attribs) as ComponentProps<'button'> & Record<string,string>;
  const primary=has(node,'primary'), active=has(node,'active'), number=!!node.attribs['data-jump'];
  const variant=primary||active||has(node,'current')?'default':ancestor(node,'nav')?'ghost':'outline';
  const actionIcon=node.attribs['data-action']==='logout'?LogOut:node.attribs['data-action']==='password'?LockKeyhole:icons[node.attribs['data-page']];
  const Icon=actionIcon;
  return <Button {...props} className={cn(node.attribs.class, number && 'answer-number')} variant={variant} size={primary?'lg':'default'} type={props.type || (ancestor(node,'form')&&!node.attribs['data-action']?'submit':'button')}>
    {Icon ? <Icon data-icon="inline-start" aria-hidden="true" /> : null}{children(node)}{primary&&node.attribs['data-action']==='submit'?<ArrowRight data-icon="inline-end" aria-hidden="true"/>:null}
  </Button>;
}

function questionBody(nodes: DOMNode[]) {
  const opts=nodes.filter(n=>n instanceof Element && n.attribs['data-option']) as Element[];
  if(!opts.length)return domToReact(nodes,options);
  let emitted=false;
  return nodes.map((n,i)=>{
    if(n instanceof Element && n.attribs['data-option']){
      if(emitted)return null;emitted=true;
      return <FieldSet key="answers"><FieldLegend variant="label">选择答案</FieldLegend><ToggleGroup type="multiple" value={opts.filter(o=>o.attribs['aria-pressed']==='true').map(o=>o.attribs['data-option'])} variant="answer" size="answer" spacing={3} className="answer-options" aria-label="答案选项">
        {opts.map(o=><ToggleGroupItem key={o.attribs['data-option']} value={o.attribs['data-option']} data-option={o.attribs['data-option']} disabled={'disabled' in o.attribs} data-result={has(o,'correct')?'correct':has(o,'wrong')?'wrong':undefined}>{children(o)}</ToggleGroupItem>)}
      </ToggleGroup></FieldSet>;
    }
    return <span className="contents" key={i}>{domToReact([n],options)}</span>;
  });
}

function panel(node: Element) {
  const nodes=node.children as DOMNode[];
  const title=nodes.find(n=>n instanceof Element&&['h1','h2','h3'].includes(n.name)) as Element|undefined;
  const footer=nodes.find(n=>n instanceof Element&&has(n,'actions')) as Element|undefined;
  const rest=nodes.filter(n=>n!==title&&n!==footer);
  const content=has(node,'question')?questionBody(rest):domToReact(rest,options);
  return <Card className={cn(node.attribs.class)}>
    {title?<CardHeader><CardTitle><h2>{children(title)}</h2></CardTitle>{has(node,'question')?<CardDescription>提交后查看正确答案与解析</CardDescription>:text(title)==='继续练习'?<CardDescription>进度自动保存，手机与电脑接着刷。</CardDescription>:null}</CardHeader>:null}
    <CardContent className="panel-content">{content}</CardContent>
    {footer?<><Separator/><CardFooter>{children(footer)}</CardFooter></>:null}
  </Card>;
}

const options: HTMLReactParserOptions = {replace(node){
  if(!(node instanceof Element))return;
  const props=attributesToProps(node.attribs);
  if(node.name==='header'){
    const nav=node.children.find(n=>n instanceof Element&&n.name==='nav') as Element;
    const navbuttons=nav.children.filter(n=>n instanceof Element&&n.name==='button') as Element[];
    const pages=navbuttons.filter(n=>n.attribs['data-page']);
    const account=navbuttons.filter(n=>!n.attribs['data-page']);
    return <header className="site-header"><a className="skip-link" href="#main-content">跳转到主要内容</a><div className="header-top"><div className="department-brand"><div className="brand-mark"><Network aria-hidden="true"/></div><div><strong translate="no">亳州网络部在线刷题</strong><p>学习工作台</p></div></div><div className="account-nav"><ThemeSelect/>{account.map((n,i)=><span key={i}>{action(n)}</span>)}</div></div><nav className="main-nav" aria-label="主导航">{pages.map((n,i)=><span key={i}>{action(n)}</span>)}</nav></header>;
  }
  if(node.name==='main'&&has(node,'auth')){
    const title=node.children.find(n=>n instanceof Element&&n.name==='h1') as Element;
    return <main id="main-content" tabIndex={-1} className="auth-layout"><section className="auth-intro"><Network aria-hidden="true"/><h1>亳州网络部<br/>在线刷题</h1><p>题库集中管理，学习进度随时接续。</p><div className="auth-features"><span><Library aria-hidden="true"/>统一题库</span><span><History aria-hidden="true"/>同步进度</span><span><Bookmark aria-hidden="true"/>错题复习</span></div></section><Card className="auth-card"><CardHeader><CardTitle><h2>{text(title).includes('登录')?'登录学习平台':text(title)}</h2></CardTitle><CardDescription>使用个人账号登录，继续你的学习计划。</CardDescription></CardHeader><CardContent className="panel-content">{domToReact((node.children as DOMNode[]).filter(n=>n!==title),options)}</CardContent></Card></main>;
  }
  if(node.name==='main'){const dashboard=node.children.some(n=>n instanceof Element&&has(n,'stats'));return <main id="main-content" tabIndex={-1} className={cn(dashboard&&'dashboard-layout')}>{children(node)}</main>;}
  if(node.name==='form'){
    const elements=node.children as DOMNode[];
    const title=elements.find(n=>n instanceof Element&&n.name==='h2') as Element|undefined;
    const content=<form {...props}><FieldGroup>{domToReact(elements.filter(n=>n!==title),options)}</FieldGroup></form>;
    if(has(node,'panel'))return <Card className="practice-config"><CardHeader><CardTitle>{title?children(title):'练习设置'}</CardTitle><CardDescription>选择题库与范围，按自己的节奏练习。</CardDescription></CardHeader><CardContent>{content}</CardContent></Card>;
    return content;
  }
  if(has(node,'panel'))return panel(node);
  if(node.name==='button')return action(node);
  if(node.name==='input'){
    if(node.attribs.type==='checkbox')return <Checkbox name={node.attribs.name} id={inputId(node)} defaultChecked={'checked' in node.attribs} />;
    return <Input {...props} spellCheck={node.attribs.name==='username'?false:undefined} id={inputId(node)} />;
  }
  if(node.name==='textarea')return <Textarea {...props} id={inputId(node)} defaultValue={text(node)} />;
  if(node.name==='select'){
    const opts=node.children.filter(n=>n instanceof Element&&n.name==='option') as Element[];
    const selected=opts.find(o=>'selected' in o.attribs)||opts[0];
    return <NativeSelect key={opts.map(o=>o.attribs.value??text(o)).join("|")} {...props} id={inputId(node)} defaultValue={selected?.attribs.value??(selected?text(selected):'')}>{opts.map((o,i)=><option key={i} value={o.attribs.value??text(o)}>{text(o)}</option>)}</NativeSelect>;
  }
  if(node.name==='label'){
    const control=node.children.find(n=>n instanceof Element&&['input','textarea','select'].includes(n.name)) as Element|undefined;
    if(!control)return <Field><FieldLabel asChild><label>{children(node)}</label></FieldLabel></Field>;
    return <Field><FieldLabel htmlFor={inputId(control)}>{domToReact((node.children as DOMNode[]).filter(n=>n!==control),options)}</FieldLabel>{domToReact([control],options)}</Field>;
  }
  if(has(node,'stats'))return <div className="stats">{node.children.filter(n=>n instanceof Element).map((n,i)=><Card key={i} className="stat-card"><CardContent>{domToReact((n as Element).children as DOMNode[],options)}</CardContent></Card>)}</div>;
  if(has(node,'status'))return <Badge variant="secondary">{children(node)}</Badge>;
  if(has(node,'feedback')||has(node,'ended'))return <Alert><CheckCircle2 aria-hidden="true"/><AlertTitle>{has(node,'ended')?'练习结果':'作答反馈'}</AlertTitle><AlertDescription>{children(node)}</AlertDescription></Alert>;
  if(has(node,'pending')||has(node,'error'))return <Alert variant={has(node,'error')?'destructive':'default'}><AlertTitle>需要处理</AlertTitle><AlertDescription>{children(node)}</AlertDescription></Alert>;
  if(node.name==='progress')return <Progress value={Number(node.attribs.value)/Number(node.attribs.max)*100} aria-label="本场练习进度"/>;
  if(node.name==='hr')return <Separator/>;
  if(node.name==='table'){const rows=node.children.filter(n=>n instanceof Element&&n.name==='tr') as Element[];return rows.length?<Table><TableHeader>{domToReact([rows[0]],options)}</TableHeader><TableBody>{domToReact(rows.slice(1),options)}</TableBody></Table>:<Table>{children(node)}</Table>;}
  if(node.name==='thead')return <TableHeader>{children(node)}</TableHeader>;
  if(node.name==='tbody')return <TableBody>{children(node)}</TableBody>;
  if(node.name==='tr')return <TableRow>{children(node)}</TableRow>;
  if(node.name==='th')return <TableHead>{children(node)}</TableHead>;
  if(node.name==='td')return <TableCell>{children(node)}</TableCell>;
  if(node.name==='p'&&/^(暂无|尚无|没有错题|先新建)/.test(text(node)))return <Empty><EmptyHeader><FileQuestion aria-hidden="true"/><EmptyTitle>暂无内容</EmptyTitle><EmptyDescription>{children(node)}</EmptyDescription></EmptyHeader></Empty>;
}};

function paintModal(){
  const nodes=new DOMParser().parseFromString(modalHTML,'text/html');
  const title=nodes.querySelector('h2');const titleText=title?.textContent||'操作确认';title?.remove();
  const content=nodes.body.innerHTML;
  flushSync(()=>modalRoot.render(<Dialog open={modalOpen} onOpenChange={open=>{modalOpen=open;paintModal();}}><DialogContent id="dialog-content" className="modal-content"><DialogHeader><DialogTitle>{titleText}</DialogTitle><DialogDescription>请检查填写内容后确认。</DialogDescription></DialogHeader>{modalMessage}{parse(content,options)}</DialogContent></Dialog>));
}
export const appSurface={set innerHTML(html:string){flushSync(()=>root.render(parse(html,options)));}};
export const dialogSurface={
  set innerHTML(html:string){modalHTML=html;modalMessage=null;},
  get open(){return modalOpen;},
  showModal(){modalOpen=true;paintModal();},
  close(){modalOpen=false;paintModal();}
};
export function notify(message:string,error=false){
  const content=message?<Alert variant={error?'destructive':'default'}><AlertDescription>{message}</AlertDescription></Alert>:null;
  flushSync(()=>messageRoot.render(content));
  if(modalOpen){modalMessage=content;paintModal();}
}
