import test from 'node:test';
import assert from 'node:assert/strict';
import {createAudioCache} from '../audio-cache.js';

class FakeResponse{
  constructor(body,{ok=true}={}){this.body=body;this.ok=ok;}
  clone(){return new FakeResponse(this.body,{ok:this.ok});}
  async blob(){return new Blob([this.body]);}
}
function fakeStorage(){
  const data=new Map();
  const cache={async match(key){return data.get(String(key));},async put(key,response){data.set(String(key),response.clone());}};
  return {async open(){return cache;}};
}

test('ensurePersistentMany reports incremental progress',async()=>{
  const progress=[];
  const cache=createAudioCache({cacheStorage:fakeStorage(),storageManager:null,fetcher:async path=>new FakeResponse(`audio:${path}`)});
  await cache.ensurePersistentMany([
    {path:'./p1.opus',generation_fingerprint:'1'},
    {path:'./p2.opus',generation_fingerprint:'2'}
  ],{concurrency:1,onProgress:value=>progress.push(value)});
  assert.deepEqual(progress.at(-1),{total:2,completed:2,failed:0});
  assert.equal(progress.length,2);
});
