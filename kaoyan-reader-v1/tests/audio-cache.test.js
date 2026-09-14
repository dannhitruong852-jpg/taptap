import test from 'node:test';
import assert from 'node:assert/strict';

let audioCacheModule=null;
try { audioCacheModule=await import('../audio-cache.js'); } catch {}

class FakeResponse {
  constructor(body,{ok=true}={}){this.body=body;this.ok=ok;}
  clone(){return new FakeResponse(this.body,{ok:this.ok});}
  async blob(){return new Blob([this.body]);}
}

function fakeCacheStorage(){
  const store=new Map();let deleteCalls=0;
  const cache={
    async match(key){return store.get(String(key))||undefined;},
    async put(key,response){store.set(String(key),response.clone());},
    async keys(){return [...store.keys()];}
  };
  return {
    store,cache,
    async open(){return cache;},
    async keys(){return ['kaoyan-audio-v1','kaoyan-audio-v0'];},
    async delete(){deleteCalls+=1;return true;},
    get deleteCalls(){return deleteCalls;}
  };
}

test('persistent audio cache exports createAudioCache',()=>{
  assert.equal(typeof audioCacheModule?.createAudioCache,'function');
});

test('first resolve fetches once and second resolve reuses persistent bytes',async()=>{
  const storage=fakeCacheStorage();let fetchCalls=0;let objectId=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async()=>{fetchCalls+=1;return new FakeResponse('audio-bytes');},
    createObjectURL:()=>`blob:test/${++objectId}`,
    revokeObjectURL:()=>{}
  });
  const item={path:'./audio/2003/v4/c-text1/v4-s01.opus',generation_fingerprint:'abc'};
  const first=await cache.resolve(item);cache.clearMemory();const second=await cache.resolve(item);
  assert.equal(fetchCalls,1);
  assert.equal(first.local,true);
  assert.equal(second.local,true);
  assert.equal(first.key,second.key);
});

test('concurrent resolves deduplicate network fetch and fingerprint changes cache identity',async()=>{
  const storage=fakeCacheStorage();let fetchCalls=0;let release;
  const gate=new Promise(resolve=>{release=resolve;});
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async()=>{fetchCalls+=1;await gate;return new FakeResponse('audio');},
    createObjectURL:()=>`blob:${Math.random()}`,
    revokeObjectURL:()=>{}
  });
  const a={path:'./x.opus',generation_fingerprint:'v1'};
  const p1=cache.resolve(a),p2=cache.resolve(a);release();
  const [r1,r2]=await Promise.all([p1,p2]);
  assert.equal(fetchCalls,1);
  assert.equal(r1.key,r2.key);
  const r3=await cache.resolve({...a,generation_fingerprint:'v2'});
  assert.notEqual(r3.key,r1.key);
});

test('persistent cache failure degrades to remote playback URL',async()=>{
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:{async open(){throw new Error('storage denied');}},
    storageManager:null,
    fetcher:async()=>{throw new Error('should not fetch in degraded direct-url mode');},
    createObjectURL:()=>{throw new Error('should not create blob');},
    revokeObjectURL:()=>{}
  });
  const item={path:'./audio/fallback.opus',generation_fingerprint:'v1'};
  const resolved=await cache.resolve(item);
  assert.deepEqual(resolved,{src:item.path,local:false,key:resolved.key});
});

test('normal browsing requests durable storage once',async()=>{
  let persistCalls=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:fakeCacheStorage(),
    storageManager:{async persist(){persistCalls+=1;return true;}},
    fetcher:async()=>new FakeResponse('audio'),
    createObjectURL:()=>`blob:test/${Math.random()}`,
    revokeObjectURL:()=>{}
  });
  assert.equal(await cache.requestPersistentStorage(),true);
  assert.equal(await cache.requestPersistentStorage(),true);
  assert.equal(persistCalls,1);
});

test('persistent cache is never automatically deleted or capacity-evicted',async()=>{
  const storage=fakeCacheStorage();let objectId=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async path=>new FakeResponse(`audio:${path}`),
    createObjectURL:()=>`blob:test/${++objectId}`,
    revokeObjectURL:()=>{}
  });
  for(let i=0;i<40;i++)await cache.resolve({path:`./audio/s${i}.opus`,generation_fingerprint:`v${i}`});
  await cache.pruneOldGenerations();
  assert.equal(storage.store.size,40);
  assert.equal(storage.deleteCalls,0);
});

test('durable-storage request degrades safely when browser refuses or does not support it',async()=>{
  const denied=audioCacheModule.createAudioCache({cacheStorage:fakeCacheStorage(),storageManager:{async persist(){return false;}}});
  assert.equal(await denied.requestPersistentStorage(),false);
  const unsupported=audioCacheModule.createAudioCache({cacheStorage:fakeCacheStorage(),storageManager:null});
  assert.equal(await unsupported.requestPersistentStorage(),false);
});
