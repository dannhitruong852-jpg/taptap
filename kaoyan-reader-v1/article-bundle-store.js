import {manifestForVersion,bilingualHighlightsPath} from './catalog.js';

export function createArticleBundleStore({fetcher=fetch,audioVersion='',concurrency=4}={}){
  const bundles=new Map();
  const inflight=new Map();
  const yearMappings=new Map();

  async function loadYearMapping(entry){
    if(yearMappings.has(entry.year))return yearMappings.get(entry.year);
    const promise=fetcher(bilingualHighlightsPath(entry))
      .then(r=>r.ok?r.json():{version:1,articles:{}})
      .catch(()=>({version:1,articles:{}}));
    yearMappings.set(entry.year,promise);
    return promise;
  }

  async function load(entry){
    const [content,manifest,bilingual]=await Promise.all([
      fetcher(entry.content).then(r=>{if(!r.ok)throw new Error('content-load-failed');return r.json();}),
      fetcher(manifestForVersion(entry,audioVersion)).then(r=>r.ok?r.json():{segments:{}}).catch(()=>({segments:{}})),
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
