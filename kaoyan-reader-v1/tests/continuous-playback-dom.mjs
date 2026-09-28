// Run with npm run test:dom after npm ci. Real app/controllers/players;
// only network responses and the platform Audio device are replaced.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const flush=async()=>{for(let i=0;i<30;i++)await new Promise(setImmediate);};
let serial=0;
async function setup({delayNext=false,preference=null}={}){
 const dom=new JSDOM(html,{url:'https://reader.test/#2002-a',pretendToBeVisual:true});
 const {window}=dom;
 for(const key of ['window','document','Node','Option','location','history','requestAnimationFrame','cancelAnimationFrame'])globalThis[key]=window[key];
 window.HTMLElement.prototype.scrollIntoView=()=>{};
 window.requestIdleCallback=()=>0;
 if(preference!==null)window.localStorage.setItem('kaoyan-continuous-playback-v1',String(preference));
 const started=[];let active=null,releaseNext;
 globalThis.Audio=class {
  constructor(src){this.src=src;this.paused=true;this.duration=1;this.currentTime=0;}
  play(){this.paused=false;active=this;started.push(this.src);return Promise.resolve();}
  pause(){this.paused=true;}
  finish(){this.paused=true;this.onended?.();}
 };
 const entries=['a','b','c'].map((id,i)=>({id:`${i===2?2003:2002}-${id}`,year:i===2?2003:2002,section_type:'reading',title:id,content:`./${id}.json`,manifest:`./${id}-audio.json`}));
 const nextGate=delayNext?new Promise(r=>{releaseNext=r;}):Promise.resolve();
 globalThis.fetch=async url=>{
  let body={};
  if(url==='./content/catalog.json')body={years:[2002,2003],articles:entries,default_article:entries[0].id};
  else if(String(url).includes('supabase'))body={entries:[]};
  else for(const entry of entries){
   if(url===entry.content){
    if(entry.title==='b')await nextGate;
    body={article_id:entry.id,article:{year:entry.year,title:entry.title},sentences:[{id:'s01',en:'Hello world.',zh:'你好。',vocab:[],segments:[{id:'s01-01',actor_id:'01',emotion:'neutral',intensity:1}]}]};
   }
   if(url===entry.manifest)body={segments:{'s01-01':{path:`./${entry.title}.mp3`,duration_seconds:1}}};
  }
  return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
 };
 await import(new URL(`../app.js?dom-test=${++serial}`,import.meta.url));await flush();
 const $=selector=>window.document.querySelector(selector);
 return {window,$,started,finish:async()=>{active.finish();await flush();},
  start:async()=>{$('#play-toggle').click();await flush();},
  release:async()=>{releaseNext?.();await flush();},
  close:()=>{window.dispatchEvent(new window.Event('beforeunload'));window.close();}
 };
}

test('actual page plays next articles across years, follows title/selectors, then stops',async()=>{
 const app=await setup();try{
  app.$('#toggle-continuous').click();await app.start();await app.finish();
  assert.deepEqual(app.started,['./a.mp3','./b.mp3']);
  assert.equal(app.$('#article-title').textContent,'b');assert.equal(app.$('#article-select').value,'2002-b');
  await app.finish();assert.equal(app.$('#year-select').value,'2003');
  await app.finish();assert.deepEqual(app.started,['./a.mp3','./b.mp3','./c.mp3']);
  assert.equal(app.$('#play-toggle').dataset.playing,'false');
 }finally{app.close();}
});
test('switch off stops at current article and the preference is stored',async()=>{
 const app=await setup({preference:true});try{
  assert.equal(app.$('#toggle-continuous').getAttribute('aria-checked'),'true');
  app.$('#toggle-continuous').click();assert.equal(app.window.localStorage.getItem('kaoyan-continuous-playback-v1'),'false');
  await app.start();await app.finish();assert.deepEqual(app.started,['./a.mp3']);
 }finally{app.close();}
});
for(const action of ['pause','disable','next','select'])test(`actual page cancels delayed autoplay on ${action}`,async()=>{
 const app=await setup({delayNext:true,preference:true});try{
  await app.start();await app.finish();
  if(action==='pause')app.$('#play-toggle').click();
  if(action==='disable')app.$('#toggle-continuous').click();
  if(action==='next')app.$('#next').click();
  if(action==='select'){
   app.$('#article-select').value='2002-a';app.$('#article-select').dispatchEvent(new app.window.Event('change'));
  }
  await app.release();assert.deepEqual(app.started,['./a.mp3']);
  assert.equal(app.$('#play-toggle').dataset.playing,'false');
 }finally{app.close();}
});
test('manual pause does not advance and resume continues the current audio',async()=>{
 const app=await setup({preference:true});try{
  await app.start();app.$('#play-toggle').click();await flush();
  assert.equal(app.$('#article-select').value,'2002-a');assert.equal(app.$('#play-toggle').dataset.playing,'false');
  await app.start();assert.deepEqual(app.started,['./a.mp3','./a.mp3']);
 }finally{app.close();}
});
