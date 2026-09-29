import test from 'node:test';
import assert from 'node:assert/strict';
import {setup,flush} from './helpers/reader-dom.js';

const phrase=(articleId,text,createdAt=1)=>({articleId,year:Number(articleId.slice(0,4)),articleTitle:articleId,sentenceId:'s01',enStart:0,enEnd:5,selectedText:text,studyGloss:'释义',sourceSentence:'Hello world.',sourceSentenceZh:'你好。',createdAt,updatedAt:createdAt});
const phrases=[phrase('2002-a','first',1),phrase('2002-b','second',3),phrase('2003-c','third',2)];
const visible=app=>[...app.$('#phrase-book-list').querySelectorAll('.phrase-book-en')].map(el=>el.textContent);
const change=(app,selector,value)=>{app.$(selector).value=value;app.$(selector).dispatchEvent(new app.window.Event('change'));};

test('defaults to current article, with one selector offering current article or whole year',async()=>{
 const app=await setup({phrases});try{
  app.$('#phrase-book-open').click();assert.deepEqual(visible(app),['first']);
  assert.deepEqual([...app.$('#phrase-book-scope').options].map(o=>o.textContent),['本篇','全年']);
  assert.equal(app.$('#phrase-book-year').disabled,true);
 }finally{app.close();}
});
test('whole year groups by catalog article order and keeps source order within each group',async()=>{
 const extra={...phrase('2002-a','newer',4),enStart:6,enEnd:11};
 const app=await setup({phrases:[...phrases,extra]});try{
  app.$('#phrase-book-open').click();change(app,'#phrase-book-scope','year');
  assert.deepEqual(visible(app),['first','newer','second']);
  assert.deepEqual([...app.$('#phrase-book-list').querySelectorAll('h3')].map(el=>el.textContent),['a','b']);
  change(app,'#phrase-book-year','2003');assert.deepEqual(visible(app),['third']);
  change(app,'#phrase-book-scope','article');assert.deepEqual(visible(app),['first','newer']);
  assert.equal(app.$('#phrase-book-year').value,'2002');
 }finally{app.close();}
});
test('an empty article never falls back to other articles in the year',async()=>{
 const app=await setup({phrases:phrases.slice(1)});try{
  app.$('#phrase-book-open').click();assert.deepEqual(visible(app),[]);
  assert.equal(app.$('#phrase-book-empty').hidden,false);
  assert.equal(app.$('#phrase-book-empty').textContent,'本篇还没有标记词群');
 }finally{app.close();}
});
test('manual article change resets whole-year scope and updates an open book',async()=>{
 const app=await setup({phrases});try{
  app.$('#phrase-book-open').click();change(app,'#phrase-book-scope','year');
  change(app,'#article-select','2002-b');await flush();
  assert.equal(app.$('#phrase-book-scope').value,'article');assert.deepEqual(visible(app),['second']);
  change(app,'#year-select','2003');await flush();
  assert.equal(app.$('#phrase-book-year').value,'2003');assert.deepEqual(visible(app),['third']);
 }finally{app.close();}
});
test('continuous playback updates the open book and preserves edits before switching',async()=>{
 const app=await setup({phrases,preference:true});try{
  await app.start();app.$('#phrase-book-open').click();change(app,'#phrase-book-scope','year');
  app.$('#phrase-book-edit').click();const editor=app.$('.phrase-book-zh.is-editing');
  editor.textContent='我的释义';editor.dispatchEvent(new app.window.Event('input'));
  await app.finish();assert.equal(app.$('#phrase-book-scope').value,'article');assert.deepEqual(visible(app),['second']);
  const saved=JSON.parse(app.window.localStorage.getItem('kaoyan-inline-phrase-highlights-v2'));
  assert.equal(saved.find(e=>e.articleId==='2002-a').studyGloss,'我的释义');
  assert.equal(app.$('#phrase-book-edit').getAttribute('aria-pressed'),'false');
 }finally{app.close();}
});
test('remote sync respects current scope and retains unsaved edit text during rerender',async()=>{
 const app=await setup({phrases});try{
  app.$('#phrase-book-open').click();app.$('#phrase-book-edit').click();
  const editor=app.$('.phrase-book-zh.is-editing');editor.textContent='编辑中';editor.dispatchEvent(new app.window.Event('input'));
  await app.remote([{...phrase('2002-b','remote other',9)}, {...phrase('2002-a','remote current',8),enStart:6,enEnd:11}]);
  assert.deepEqual(visible(app),['first','remote current']);
  assert.equal([...app.$('#phrase-book-list').querySelectorAll('.phrase-book-zh')][0].textContent,'编辑中');
 }finally{app.close();}
});
test('editing, blur and deletion in one scope preserve other articles and years',async()=>{
 const app=await setup({phrases});try{
  app.$('#phrase-book-open').click();app.$('#phrase-book-blur').click();
  assert.equal(app.$('.phrase-book-panel').classList.contains('is-blurred'),true);
  app.$('#phrase-book-blur').click();app.$('#phrase-book-edit').click();
  const editor=app.$('.phrase-book-zh.is-editing');editor.textContent='修改后';editor.dispatchEvent(new app.window.Event('input'));
  app.$('#phrase-book-edit').click();assert.equal(app.$('.phrase-book-zh').textContent,'修改后');
  app.$('.phrase-book-row').click();app.$('.phrase-book-delete').click();assert.deepEqual(visible(app),[]);
  change(app,'#phrase-book-scope','year');assert.deepEqual(visible(app),['second']);
  change(app,'#phrase-book-year','2003');assert.deepEqual(visible(app),['third']);
 }finally{app.close();}
});

test('system/browser back closes the phrase book, preserves the current article, and does not exit the reader',async()=>{
 const app=await setup({phrases});try{
  app.$('#phrase-book-open').click();
  assert.equal(app.window.history.state?.__kaoyanUiLayer,'phrase-book');
  change(app,'#article-select','2002-b');await flush();
  assert.equal(app.window.history.state?.__kaoyanUiLayer,'phrase-book');
  const popped=new Promise(resolve=>app.window.addEventListener('popstate',resolve,{once:true}));
  app.window.history.back();await popped;await flush();
  assert.equal(app.$('#phrase-book-backdrop').hidden,true);
  assert.equal(app.$('#article-select').value,'2002-b');
  assert.equal(app.window.location.hash,'#2002-b');
 }finally{app.close();}
});

test('entering and leaving edit mode preserve the phrasebook scroll position',async()=>{
 const extra=Array.from({length:24},(_,index)=>({...phrase('2002-a',`item-${index}`,index+10),enStart:index*6,enEnd:index*6+5}));
 const app=await setup({phrases:extra});const proto=app.window.HTMLElement.prototype;const originalFocus=proto.focus;
 try{
  app.$('#phrase-book-open').click();
  const list=app.$('#phrase-book-list');
  proto.focus=function(...args){
   if(this.classList?.contains('is-editing'))list.scrollTop=0;
   return originalFocus.apply(this,args);
  };
  list.scrollTop=360;
  app.$('#phrase-book-edit').click();
  assert.equal(list.scrollTop,360,'entering edit mode must not jump to the first phrase');
  list.scrollTop=520;
  app.$('#phrase-book-edit').click();
  assert.equal(list.scrollTop,520,'finishing edits must keep the current scroll position');
 }finally{proto.focus=originalFocus;app.close();}
});

test('phrasebook ignores add/edit time and orders phrases by sentence then source offset',async()=>{
 const ordered=[
  {...phrase('2002-a','sentence-two',50),sentenceId:'s02',enStart:0,enEnd:5},
  {...phrase('2002-a','sentence-one-late',40),sentenceId:'s01',enStart:6,enEnd:11},
  {...phrase('2002-a','sentence-one-early',30),sentenceId:'s01',enStart:0,enEnd:5}
 ];
 const app=await setup({phrases:ordered});try{
  app.$('#phrase-book-open').click();
  assert.deepEqual(visible(app),['sentence-one-early','sentence-one-late','sentence-two']);
  app.$('#phrase-book-edit').click();
  const editor=app.$('.phrase-book-zh.is-editing');editor.textContent='改过的释义';editor.dispatchEvent(new app.window.Event('input'));
  app.$('#phrase-book-edit').click();
  assert.deepEqual(visible(app),['sentence-one-early','sentence-one-late','sentence-two']);
 }finally{app.close();}
});

test('opening phrasebook during playback scrolls to the first phrase of the active sentence',async()=>{
 const activePhrases=[
  {...phrase('2002-a','later-in-active',2),sentenceId:'s01',enStart:6,enEnd:11},
  {...phrase('2002-a','first-in-active',1),sentenceId:'s01',enStart:0,enEnd:5}
 ];
 const app=await setup({phrases:activePhrases});const proto=app.window.HTMLElement.prototype;const original=proto.scrollIntoView;let scrolled=null;
 try{
  proto.scrollIntoView=function(){if(this.classList?.contains('phrase-book-item'))scrolled=this;};
  await app.start();
  app.$('#phrase-book-open').click();
  assert.equal(app.$('#phrase-book-scope').value,'article');
  assert.equal(scrolled?.dataset.sentenceId,'s01');
  assert.equal(scrolled?.dataset.phraseKey,'2002-a|s01|0|5');
 }finally{proto.scrollIntoView=original;app.close();}
});
