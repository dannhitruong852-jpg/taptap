const CACHE_NAMESPACE='kaoyan-audio-v1';

function fileName(path=''){return String(path).split('/').pop()||'';}
export function assetVersion(item={}){
  return item.generation_fingerprint || item.files?.[fileName(item.path)] || item.file_hash || 'unversioned';
}
export function audioCacheKey(item={}){
  const path=String(item.path||'');
  const version=String(assetVersion(item));
  return `https://kaoyan-audio-cache.invalid/${encodeURIComponent(version)}/${encodeURIComponent(path)}`;
}

export function createAudioCache({
  cacheStorage=typeof caches!=='undefined'?caches:null,
  fetcher=typeof fetch!=='undefined'?fetch.bind(globalThis):null,
  createObjectURL=blob=>URL.createObjectURL(blob),
  revokeObjectURL=url=>URL.revokeObjectURL(url),
  maxBlobEntries=18,
  warmConcurrency=3,
  namespace=CACHE_NAMESPACE
}={}){
  const inflight=new Map();
  const blobs=new Map();
  const pinned=new Set();
  let persistentPromise=null;
  let persistenceDisabled=!cacheStorage;

  async function persistent(){
    if(persistenceDisabled)return null;
    if(!persistentPromise){
      persistentPromise=Promise.resolve(cacheStorage.open(namespace)).catch(()=>{persistenceDisabled=true;return null;});
    }
    return persistentPromise;
  }

  function pin(key){if(key)pinned.add(key);}
  function unpin(key){if(key)pinned.delete(key);}
  function localEntry(src,key){return {src,local:true,key,pin:()=>pin(key),unpin:()=>unpin(key)};}

  function touch(key,entry){
    if(blobs.has(key))blobs.delete(key);
    blobs.set(key,entry);
    let guard=0;
    while(blobs.size>maxBlobEntries&&guard++<blobs.size+2){
      const [oldestKey,oldest]=blobs.entries().next().value;
      if(pinned.has(oldestKey)){
        blobs.delete(oldestKey);blobs.set(oldestKey,oldest);continue;
      }
      blobs.delete(oldestKey);
      try{revokeObjectURL(oldest.src);}catch{}
    }
  }

  async function resolvePersistent(item,key){
    const store=await persistent();
    if(!store)return {src:item.path,local:false,key};
    let response;
    try{response=await store.match(key);}catch{return {src:item.path,local:false,key};}
    if(!response){
      if(!fetcher)return {src:item.path,local:false,key};
      const network=await fetcher(item.path);
      if(!network?.ok)throw new Error('audio-fetch-failed');
      response=network;
      try{await store.put(key,network.clone());}catch{}
    }
    const blob=await response.blob();
    const entry=localEntry(createObjectURL(blob),key);
    touch(key,entry);
    return entry;
  }

  async function resolve(item){
    if(!item?.path)throw new Error('audio-path-required');
    const key=audioCacheKey(item);
    const memory=blobs.get(key);
    if(memory){touch(key,memory);return memory;}
    if(inflight.has(key))return inflight.get(key);
    const task=resolvePersistent(item,key).finally(()=>inflight.delete(key));
    inflight.set(key,task);
    return task;
  }

  async function warm(items=[]){
    const unique=[];const seen=new Set();
    for(const item of items){
      if(!item?.path)continue;const key=audioCacheKey(item);if(seen.has(key))continue;seen.add(key);unique.push(item);
    }
    let cursor=0;
    const worker=async()=>{while(cursor<unique.length){const item=unique[cursor++];try{await resolve(item);}catch{}}};
    const workers=Array.from({length:Math.min(Math.max(1,warmConcurrency),unique.length)},()=>worker());
    await Promise.all(workers);
  }

  function clearMemory(){
    for(const [key,entry] of blobs){
      if(pinned.has(key))continue;
      try{revokeObjectURL(entry.src);}catch{}
      blobs.delete(key);
    }
  }
  async function pruneOldGenerations(){
    if(!cacheStorage?.keys)return;
    try{
      const names=await cacheStorage.keys();
      await Promise.all(names.filter(name=>/^kaoyan-audio-v/.test(name)&&name!==namespace).map(name=>cacheStorage.delete(name)));
    }catch{}
  }
  return {resolve,warm,pin,unpin,clearMemory,pruneOldGenerations,getState:()=>({memory:blobs.size,inflight:inflight.size,persistenceDisabled})};
}
