const DEFAULT_NAMESPACE='kaoyan-static-active-sentence-20260918-v2';

export function createStaticResourceCache({
  cacheStorage=typeof caches!=='undefined'?caches:null,
  fetcher=typeof fetch!=='undefined'?fetch.bind(globalThis):null,
  namespace=DEFAULT_NAMESPACE
}={}){
  let storePromise=null;
  const inflight=new Map();

  async function store(){
    if(!cacheStorage)return null;
    if(!storePromise)storePromise=Promise.resolve(cacheStorage.open(namespace)).catch(()=>null);
    return storePromise;
  }

  async function ensure(url){
    const s=await store();
    if(!s)throw new Error('static-cache-unavailable');
    const hit=await s.match(url).catch(()=>null);
    if(hit)return {cached:true};
    if(inflight.has(url))return inflight.get(url);
    const task=(async()=>{
      if(!fetcher)throw new Error('static-resource-fetch-unavailable');
      const response=await fetcher(url);
      if(!response?.ok)throw new Error('static-resource-fetch-failed');
      await s.put(url,response.clone());
      return {cached:false};
    })().finally(()=>inflight.delete(url));
    inflight.set(url,task);
    return task;
  }

  async function json(url,{refresh=false}={}){
    const s=await store();
    if(!s){
      if(!fetcher)throw new Error('static-resource-fetch-unavailable');
      const response=await fetcher(url);
      if(!response?.ok)throw new Error('static-resource-fetch-failed');
      return response.json();
    }
    const hit=await s.match(url).catch(()=>null);
    if(hit){
      if(refresh&&fetcher)void (async()=>{try{const response=await fetcher(url);if(response?.ok)await s.put(url,response.clone());}catch{}})();
      return hit.json();
    }
    if(!fetcher)throw new Error('static-resource-fetch-unavailable');
    const response=await fetcher(url);
    if(!response?.ok)throw new Error('static-resource-fetch-failed');
    await s.put(url,response.clone());
    return response.json();
  }

  return {json,ensure};
}
