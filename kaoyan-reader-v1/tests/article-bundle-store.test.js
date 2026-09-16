import test from 'node:test';
import assert from 'node:assert/strict';
import {createArticleBundleStore} from '../article-bundle-store.js';

function makeFetcher(calls){
  return async url=>{
    calls.push(url);
    if(url.includes('/audio/'))return {ok:true,json:async()=>({sentences:{},segments:{}})};
    if(url.endsWith('bilingual-highlights.json'))return {ok:true,json:async()=>({version:1,articles:{}})};
    return {ok:true,json:async()=>({article_id:url,sentences:[]})};
  };
}

function entry(id,year=2003){return {id,year,content:`./content/${year}/c/${id}.json`,manifest:`./audio/${year}/v4/c-${id}/manifest.json`};}

test('second get returns the same resident bundle without new fetches',async()=>{
  const calls=[];
  const store=createArticleBundleStore({fetcher:makeFetcher(calls),audioVersion:''});
  const target=entry('text1');
  const first=await store.get(target);
  const count=calls.length;
  const second=await store.get(target);
  assert.strictEqual(second,first);
  assert.equal(calls.length,count);
  assert.equal(store.has(target.id),true);
});

test('articles from one year share one resident bilingual mapping fetch',async()=>{
  const calls=[];
  const store=createArticleBundleStore({fetcher:makeFetcher(calls),audioVersion:''});
  await store.get(entry('text1'));
  await store.get(entry('text2'));
  assert.equal(calls.filter(url=>url.endsWith('bilingual-highlights.json')).length,1);
});

test('background preload populates RAM for later zero-fetch get',async()=>{
  const calls=[];
  const store=createArticleBundleStore({fetcher:makeFetcher(calls),audioVersion:'',concurrency:2});
  const target=entry('text3');
  await store.preload([target]);
  const count=calls.length;
  await store.get(target);
  assert.equal(calls.length,count);
  assert.equal(store.has(target.id),true);
});
