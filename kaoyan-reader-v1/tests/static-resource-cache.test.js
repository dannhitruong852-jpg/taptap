import test from 'node:test';
import assert from 'node:assert/strict';
import {createStaticResourceCache} from '../static-resource-cache.js';

class JsonResponse{
  constructor(value,{ok=true}={}){this.value=value;this.ok=ok;}
  clone(){return new JsonResponse(structuredClone(this.value),{ok:this.ok});}
  async json(){return structuredClone(this.value);}
}
function fakeStorage(){
  const store=new Map();
  const cache={
    async match(key){return store.get(String(key));},
    async put(key,response){store.set(String(key),response.clone());}
  };
  return {store,async open(){return cache;}};
}

test('json serves a persistent hit without blocking on network when refresh is disabled',async()=>{
  const storage=fakeStorage();let fetchCalls=0;
  const cache=createStaticResourceCache({cacheStorage:storage,fetcher:async()=>{fetchCalls+=1;return new JsonResponse({version:1});}});
  assert.deepEqual(await cache.json('./content/a.json',{refresh:false}),{version:1});
  assert.deepEqual(await cache.json('./content/a.json',{refresh:false}),{version:1});
  assert.equal(fetchCalls,1);
});

test('ensure writes a missing resource and then reports cached',async()=>{
  const storage=fakeStorage();let fetchCalls=0;
  const cache=createStaticResourceCache({cacheStorage:storage,fetcher:async()=>{fetchCalls+=1;return new JsonResponse({ok:true});}});
  assert.deepEqual(await cache.ensure('./x.json'),{cached:false});
  assert.deepEqual(await cache.ensure('./x.json'),{cached:true});
  assert.equal(fetchCalls,1);
});
