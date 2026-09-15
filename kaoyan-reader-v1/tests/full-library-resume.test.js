import test from 'node:test';
import assert from 'node:assert/strict';
import {createAudioCache} from '../audio-cache.js';
import {createFullLibraryCacheCoordinator} from '../full-library-cache.js';

class FakeResponse{
  constructor(body,{ok=true}={}){this.body=body;this.ok=ok;}
  clone(){return new FakeResponse(this.body,{ok:this.ok});}
  async blob(){return new Blob([this.body]);}
}
function fakeStorage(){
  const data=new Map();
  const cache={async match(key){return data.get(String(key));},async put(key,response){data.set(String(key),response.clone());}};
  return {data,async open(){return cache;}};
}

test('warm restart skips completed audio and full-library persistence creates no Blob URLs',async()=>{
  const storage=fakeStorage();const fetched=[];let objectUrls=0;
  const audioCache=createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async path=>{fetched.push(path);return new FakeResponse(`audio:${path}`);},
    createObjectURL:()=>{objectUrls+=1;return 'blob:unexpected';},
    revokeObjectURL:()=>{}
  });
  await audioCache.ensurePersistent({path:'./a.opus',generation_fingerprint:'ga'});
  const catalog={articles:[{id:'a'},{id:'b'}]};
  const bundles={
    a:{content:{sentences:[{id:'s1',segments:[]}]},manifest:{generation_fingerprint:'ga',sentences:{s1:{path:'./a.opus'}}}},
    b:{content:{sentences:[{id:'s2',segments:[]}]},manifest:{generation_fingerprint:'gb',sentences:{s2:{path:'./b.opus'}}}}
  };
  const coordinator=createFullLibraryCacheCoordinator({catalog,articleBundleStore:{get:async entry=>bundles[entry.id]},audioCache,supportsOpus:true});
  const state=await coordinator.start();
  assert.equal(state.status,'complete');
  assert.deepEqual(fetched,['./a.opus','./b.opus']);
  assert.equal(objectUrls,0);
  assert.equal(storage.data.size,2);
});
