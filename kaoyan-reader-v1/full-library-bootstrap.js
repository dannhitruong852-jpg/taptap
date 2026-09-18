import {createAudioCache} from './audio-cache.js';
import {createArticleBundleStore} from './article-bundle-store.js';
import {createStaticResourceCache} from './static-resource-cache.js?v=phrase-study-20260918-v2';
import {createFullLibraryCacheCoordinator} from './full-library-cache.js';

function ensureStatusElement(){
  let node=document.querySelector('#offline-cache-status');
  if(node)return node;
  node=document.createElement('p');
  node.id='offline-cache-status';
  node.className='content-status';
  node.setAttribute('aria-live','polite');
  node.style.opacity='.68';
  node.style.fontSize='.78rem';
  node.textContent='离线缓存准备中';
  const anchor=document.querySelector('.catalog-controls');
  if(anchor)anchor.insertAdjacentElement('afterend',node);
  else{
    const hero=document.querySelector('.hero');
    if(hero)hero.appendChild(node);
    else document.body.appendChild(node);
  }
  return node;
}

function whenReaderReady(){
  const list=document.querySelector('#sentence-list');
  if(list?.children?.length)return Promise.resolve();
  return new Promise(resolve=>{
    const observer=new MutationObserver(()=>{
      if(list?.children?.length){observer.disconnect();resolve();}
    });
    if(list)observer.observe(list,{childList:true});
    else window.setTimeout(()=>resolve(),1200);
  });
}

function renderProgress(node,state){
  if(state.status==='complete'){
    node.textContent=`离线缓存完成 · ${state.articlesDone}/${state.articlesTotal} 篇 · 音频 ${state.audioDone}/${state.audioTotal}`;
    return;
  }
  if(state.status==='stopped'){
    node.textContent='离线缓存暂停 · 下次打开自动继续';
    return;
  }
  if(state.audioTotal>0){
    node.textContent=`离线缓存音频 ${state.audioDone}/${state.audioTotal} · 文章 ${state.articlesDone}/${state.articlesTotal}`;
    return;
  }
  node.textContent=`离线缓存文章 ${state.articlesDone}/${state.articlesTotal}`;
}

async function startFullLibraryCache(){
  await whenReaderReady();
  const status=ensureStatusElement();
  try{
    const response=await fetch('./content/catalog.json',{cache:'no-cache'});
    if(!response.ok)throw new Error('catalog-load-failed');
    const catalog=await response.json();
    const probe=document.createElement('audio');
    const supportsOpus=Boolean(probe.canPlayType('audio/ogg; codecs="opus"'));
    const resourceCache=createStaticResourceCache();
    const articleBundleStore=createArticleBundleStore({resourceCache});
    const audioCache=createAudioCache();
    const coordinator=createFullLibraryCacheCoordinator({
      catalog,
      articleBundleStore,
      audioCache,
      supportsOpus,
      articleConcurrency:2,
      audioConcurrency:4,
      onProgress:state=>renderProgress(status,state)
    });
    window.__kaoyanFullLibraryCache=coordinator;
    window.addEventListener('beforeunload',()=>coordinator.stop(),{once:true});
    await coordinator.start();
  }catch{
    status.textContent='离线缓存暂不可用 · 正常阅读不受影响';
  }
}

void startFullLibraryCache();
