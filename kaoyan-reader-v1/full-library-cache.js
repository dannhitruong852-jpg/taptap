import {buildSentenceQueue} from './playback.js';

function audioItemsForBundle(bundle,supportsOpus){
  const items=[];
  for(const sentence of bundle?.content?.sentences||[]){
    for(const item of buildSentenceQueue(sentence,bundle.manifest||{segments:{}})){
      const path=!supportsOpus&&item.mp3_path?item.mp3_path:item.path;
      if(path)items.push({...item,path});
    }
  }
  return items;
}

export function createFullLibraryCacheCoordinator({
  catalog,
  articleBundleStore,
  audioCache,
  supportsOpus=true,
  articleConcurrency=2,
  audioConcurrency=4,
  onProgress=()=>{}
}={}){
  const articles=[...(catalog?.articles||[])];
  let stopped=false;
  let runningPromise=null;
  let state={status:'idle',articlesTotal:articles.length,articlesDone:0,audioTotal:0,audioDone:0,failed:0};

  function emit(){onProgress({...state});}
  function getState(){return {...state};}
  function stop(){stopped=true;if(state.status==='running'){state={...state,status:'stopped'};emit();}}

  async function run(){
    stopped=false;
    state={status:'running',articlesTotal:articles.length,articlesDone:0,audioTotal:0,audioDone:0,failed:0};
    emit();
    const allAudio=[];
    let cursor=0;
    const worker=async()=>{
      while(!stopped&&cursor<articles.length){
        const entry=articles[cursor++];
        try{
          const bundle=await articleBundleStore.get(entry);
          allAudio.push(...audioItemsForBundle(bundle,supportsOpus));
          state={...state,articlesDone:state.articlesDone+1};
        }catch{
          state={...state,articlesDone:state.articlesDone+1,failed:state.failed+1};
        }
        emit();
      }
    };
    const count=Math.min(Math.max(1,Number(articleConcurrency)||1),articles.length||1);
    await Promise.all(Array.from({length:count},()=>worker()));
    if(stopped)return getState();

    const unique=[];const seen=new Set();
    for(const item of allAudio){
      const key=`${item.generation_fingerprint||item.file_hash||''}|${item.path}`;
      if(seen.has(key))continue;
      seen.add(key);unique.push(item);
    }
    state={...state,audioTotal:unique.length};emit();
    const result=await audioCache.ensurePersistentMany(unique,{concurrency:audioConcurrency});
    if(stopped)return getState();
    state={...state,status:'complete',audioDone:result.completed,failed:state.failed+result.failed};
    emit();
    return getState();
  }

  function start(){
    if(runningPromise)return runningPromise;
    runningPromise=run().finally(()=>{runningPromise=null;});
    return runningPromise;
  }

  return {start,stop,getState};
}
