import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
const html=await readFile(new URL('../../index.html',import.meta.url),'utf8');
export const flush=async()=>{for(let i=0;i<30;i++)await new Promise(setImmediate);};
let serial=0;
export async function setup({delayNext=false,preference=null,phrases=[]}={}){
 const dom=new JSDOM(html,{url:'https://reader.test/#2002-a',pretendToBeVisual:true});
 const {window}=dom;
 window.localStorage.setItem('kaoyan-inline-phrase-highlights-v2',JSON.stringify(phrases));
 for(const key of ['window','document','Node','Option','location','history','requestAnimationFrame','cancelAnimationFrame'])globalThis[key]=window[key];
 window.HTMLElement.prototype.scrollIntoView=()=>{};
 window.requestIdleCallback=()=>0;
 if(preference!==null)window.localStorage.setItem('kaoyan-continuous-playback-v1',String(preference));
 let remoteEntries=[];
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
  else if(String(url).includes('supabase'))body={entries:remoteEntries};
  else for(const entry of entries){
   if(url===entry.content){
    if(entry.title==='b')await nextGate;
    body={article_id:entry.id,article:{year:entry.year,title:entry.title},sentences:[{id:'s01',en:'Hello world.',zh:'你好。',vocab:[],segments:[{id:'s01-01',actor_id:'01',emotion:'neutral',intensity:1}]}]};
   }
   if(url===entry.manifest)body={segments:{'s01-01':{path:`./${entry.title}.mp3`,duration_seconds:1}}};
  }
  return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
 };
 await import(new URL(`../../app.js?dom-test=${++serial}`,import.meta.url));await flush();
 const $=selector=>window.document.querySelector(selector);
 return {window,$,started,
  remote:async entries=>{remoteEntries=entries;window.dispatchEvent(new window.Event('online'));await flush();},finish:async()=>{active.finish();await flush();},
  start:async()=>{$('#play-toggle').click();await flush();},
  release:async()=>{releaseNext?.();await flush();},
  close:()=>{window.dispatchEvent(new window.Event('beforeunload'));window.close();}
 };
}

