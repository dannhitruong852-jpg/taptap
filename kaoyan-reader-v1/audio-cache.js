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
  storageManager=typeof navigator!=='undefined'?navigator.storage:null,
  fetcher=typeof fetch!=='undefined'?fetch.bind(globalThis):null,
  createObjectURL=blob=>URL.createObjectURL(blob),
  revokeObjectURL=url=>URL.revokeObjectURL(url),
  warmConcurrency=3,
  namespace=CACHE_NAMESPACE
}={}){
  const inflight=new Map();
  const responseInflight=new Map();
  const persistentEnsureInflight=new Map();
  const blobs=new Map();
  const pinned=new Set();
  let persistentPromise=null;
  let durableStoragePromise=null;
  let persistenceDisabled=!cacheStorage;

  async function persistent(){
    if(persistenceDisabled)return null;
    if(!persistentPromise){
      persistentPromise=Promise.resolve(cacheStorage.open(namespace)).catch(()=>{persistenceDisabled=true;return null;});
    }
    return persistentPromise;
  }

  function requestPersistentStorage(){
    if(durableStoragePromise)return durableStoragePromise;
    if(!storageManager?.persist){
      durableStoragePromise=Promise.resolve(false);
      return durableStoragePromise;
    }
    durableStoragePromise=Promise.resolve(storageManager.persist()).then(Boolean).catch(()=>false);
    return durableStoragePromise;
  }

  function pin(key){if(key)pinned.add(key);}
  function unpin(key){if(key)pinned.delete(key);}
  function localEntry(src,key){return {src,local:true,key,pin:()=>pin(key),unpin:()=>unpin(key)};}

  function touch(key,entry){
    if(blobs.has(key))blobs.delete(key);
    blobs.set(key,entry);
  }

  async function responseFor(item,key){
    const store=await persistent();
    if(!store)return null;
    if(!responseInflight.has(key)){
      const task=(async()=>{
        let response;
        try{response=await store.match(key);}catch{return null;}
        if(!response){
          if(!fetcher)return null;
          const network=await fetcher(item.path);
          if(!network?.ok)throw new Error('audio-fetch-failed');
          response=network;
          try{await store.put(key,network.clone());}catch{}
        }
        return response;
      })().finally(()=>responseInflight.delete(key));
      responseInflight.set(key,task);
    }
    const response=await responseInflight.get(key);
    return response?.clone?response.clone():response;
  }

  async function resolvePersistent(item,key){
    const response=await responseFor(item,key);
    if(!response)return {src:item.path,local:false,key};
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

  async function getArrayBuffer(item){
    if(!item?.path)throw new Error('audio-path-required');
    const key=audioCacheKey(item);
    const response=await responseFor(item,key);
    if(!response)throw new Error('audio-bytes-unavailable');
    const blob=await response.blob();
    return {buffer:await blob.arrayBuffer(),key,local:true};
  }

  async function ensurePersistent(item){
    if(!item?.path)throw new Error('audio-path-required');
    const key=audioCacheKey(item);
    const store=await persistent();
    if(!store)throw new Error('persistent-cache-unavailable');
    let hit;
    try{hit=await store.match(key);}catch{throw new Error('persistent-cache-unavailable');}
    if(hit)return {key,cached:true};
    if(!persistentEnsureInflight.has(key)){
      const task=(async()=>{
        if(!fetcher)throw new Error('audio-fetch-unavailable');
        const network=await fetcher(item.path);
        if(!network?.ok)throw new Error('audio-fetch-failed');
        await store.put(key,network.clone());
        return {key,cached:false};
      })().finally(()=>persistentEnsureInflight.delete(key));
      persistentEnsureInflight.set(key,task);
    }
    return persistentEnsureInflight.get(key);
  }

  async function ensurePersistentMany(items=[],{concurrency=4}={}){
    const unique=[];const seen=new Set();
    for(const item of items){
      if(!item?.path)continue;
      const key=audioCacheKey(item);
      if(seen.has(key))continue;
      seen.add(key);unique.push(item);
    }
    let cursor=0,completed=0,failed=0;
    const worker=async()=>{
      while(cursor<unique.length){
        const item=unique[cursor++];
        try{await ensurePersistent(item);completed+=1;}catch{failed+=1;}
      }
    };
    const count=Math.min(Math.max(1,Number(concurrency)||1),unique.length||1);
    await Promise.all(Array.from({length:count},()=>worker()));
    return {total:unique.length,completed,failed};
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

  // Kept only for backward compatibility with older app.js builds.
  // The permanent-retention policy intentionally performs no persistent-cache deletion.
  function pruneOldGenerations(){return Promise.resolve();}

  requestPersistentStorage();
  return {resolve,getArrayBuffer,ensurePersistent,ensurePersistentMany,warm,pin,unpin,clearMemory,requestPersistentStorage,pruneOldGenerations,getState:()=>({memory:blobs.size,inflight:inflight.size,responseInflight:responseInflight.size,persistentEnsureInflight:persistentEnsureInflight.size,persistenceDisabled})};
}
