import {manifestForVersion,bilingualHighlightsPath} from './catalog.js';

export function createArticleBundleStore({fetcher=fetch,audioVersion='',concurrency=4,resourceCache=null}={}){
  const bundles=new Map();
  const inflight=new Map();
  const yearMappings=new Map();

  async function fetchJson(url,options={}){
    try{
      if(resourceCache)return await resourceCache.json(url,{refresh:true});
      const response=await fetcher(url);
      if(!response?.ok)throw new Error('resource-load-failed');
      return response.json();
    }catch(error){
      if(Object.prototype.hasOwnProperty.call(options,'fallback'))return options.fallback;
      throw error;
    }
  }

  async function loadYearMapping(entry){
    if(yearMappings.has(entry.year))return yearMappings.get(entry.year);
    const promise=fetchJson(bilingualHighlightsPath(entry),{fallback:{version:1,articles:{}}});
    yearMappings.set(entry.year,promise);
    return promise;
  }

  async function load(entry){
    const [content,manifest,bilingual]=await Promise.all([
      fetchJson(entry.content),
      fetchJson(manifestForVersion(entry,audioVersion),{fallback:{segments:{}}}),
      entry.year===undefined||entry.year===null?Promise.resolve({version:1,articles:{}}):loadYearMapping(entry)
    ]);
    return {content,manifest,bilingual};
  }

  async function get(entry){
    if(!entry?.id)throw new Error('article-id-required');
    if(bundles.has(entry.id))return bundles.get(entry.id);
    if(inflight.has(entry.id))return inflight.get(entry.id);
    const task=load(entry).then(bundle=>{bundles.set(entry.id,bundle);return bundle;}).finally(()=>inflight.delete(entry.id));
    inflight.set(entry.id,task);
    return task;
  }

  async function preload(entries=[]){
    const queue=[...entries];
    let cursor=0;
    const worker=async()=>{
      while(cursor<queue.length){
        const item=queue[cursor++];
        try{await get(item);}catch{}
      }
    };
    const count=Math.min(Math.max(1,Number(concurrency)||1),queue.length||1);
    await Promise.all(Array.from({length:count},()=>worker()));
  }

  return {
    get,
    preload,
    has:id=>bundles.has(id),
    cancelLowPriorityWork:()=>{},
    getState:()=>({resident:bundles.size,inflight:inflight.size,concurrency})
  };
}
