function requestIdentity(item={}){
  return `${String(item.generation_fingerprint||item.file_hash||'unversioned')}|${String(item.path||'')}`;
}

export function createDecodedAudioStore({audioContext,audioCache}={}){
  if(!audioContext?.decodeAudioData)throw new Error('audio-context-required');
  if(!audioCache?.getArrayBuffer)throw new Error('audio-cache-bytes-required');
  const decoded=new Map();
  const inflight=new Map();
  const identityToKey=new Map();

  async function get(item,{articleId='unknown'}={}){
    if(!item?.path)throw new Error('audio-path-required');
    const identity=requestIdentity(item);
    const knownKey=identityToKey.get(identity);
    if(knownKey&&decoded.has(knownKey))return decoded.get(knownKey);
    if(inflight.has(identity))return inflight.get(identity);
    const task=(async()=>{
      const bytes=await audioCache.getArrayBuffer(item);
      identityToKey.set(identity,bytes.key);
      if(decoded.has(bytes.key))return decoded.get(bytes.key);
      const source=bytes.buffer?.slice?bytes.buffer.slice(0):bytes.buffer;
      const buffer=await audioContext.decodeAudioData(source);
      const entry={buffer,key:bytes.key,articleId};
      decoded.set(bytes.key,entry);
      return entry;
    })().finally(()=>inflight.delete(identity));
    inflight.set(identity,task);
    return task;
  }

  async function preload(items=[],options={}){
    await Promise.allSettled((items||[]).filter(item=>item?.path).map(item=>get(item,options)));
  }

  function has(item){
    const key=identityToKey.get(requestIdentity(item));
    return Boolean(key&&decoded.has(key));
  }

  function dropArticle(articleId){
    const removed=new Set();
    for(const [key,entry] of decoded){
      if(entry.articleId===articleId){decoded.delete(key);removed.add(key);}
    }
    if(removed.size){
      for(const [identity,key] of identityToKey)if(removed.has(key))identityToKey.delete(identity);
    }
  }

  function clearDecoded(){
    decoded.clear();
    identityToKey.clear();
  }

  return {
    get,preload,has,dropArticle,clearDecoded,
    getState:()=>({decoded:decoded.size,inflight:inflight.size})
  };
}
