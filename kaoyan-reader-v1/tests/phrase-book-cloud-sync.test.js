import test from 'node:test';
import assert from 'node:assert/strict';
import {createPhraseBookCloudSync, validPhraseBookSyncKey} from '../phrase-book-cloud-sync.js';

function memoryStorage(){
  const map=new Map();
  return {
    getItem:key=>map.has(key)?map.get(key):null,
    setItem:(key,value)=>map.set(key,String(value)),
  };
}
function fixedCrypto(){
  return {getRandomValues(bytes){for(let i=0;i<bytes.length;i++)bytes[i]=i+1;return bytes;}};
}
function storeStub(entries=[]){
  let current=[...entries], merged=[];
  return {
    snapshot:()=>[...current],
    merge:remote=>{merged=[...remote];current=[...remote];return {changed:true,entries:[...current]};},
    get merged(){return merged;}
  };
}

test('generates and persists a valid sync key on first use',()=>{
  const storage=memoryStorage();
  const sync=createPhraseBookCloudSync({store:storeStub(),storage,cryptoApi:fixedCrypto()});
  const key=sync.getKey();
  assert.equal(validPhraseBookSyncKey(key),true);
  assert.equal(sync.getKey(),key);
});

test('sync posts the local snapshot and merges remote entries',async()=>{
  const local=[{articleId:'2014-text1',sentenceId:'s1',enStart:0,enEnd:4,updatedAt:1}];
  const remote=[...local,{articleId:'2014-text2',sentenceId:'s2',enStart:3,enEnd:9,updatedAt:2}];
  const store=storeStub(local);
  let request=null, mergedCalled=false;
  const sync=createPhraseBookCloudSync({
    store,
    storage:memoryStorage(),
    cryptoApi:fixedCrypto(),
    fetchFn:async(url,init)=>{
      request={url,init};
      return {ok:true,json:async()=>({entries:remote})};
    },
    onMerged:()=>{mergedCalled=true;}
  });
  const result=await sync.syncNow();
  assert.equal(result.ok,true);
  assert.equal(mergedCalled,true);
  assert.equal(JSON.parse(request.init.body).entries.length,1);
  assert.deepEqual(store.merged,remote);
});

test('offline sync failure keeps local data untouched',async()=>{
  const local=[{articleId:'2014-text1',sentenceId:'s1',enStart:0,enEnd:4,updatedAt:1}];
  const store=storeStub(local);
  let status='';
  const sync=createPhraseBookCloudSync({
    store,
    storage:memoryStorage(),
    cryptoApi:fixedCrypto(),
    fetchFn:async()=>{throw new Error('offline');},
    onStatus:value=>{status=value;}
  });
  const result=await sync.syncNow();
  assert.equal(result.ok,false);
  assert.equal(status,'offline');
  assert.deepEqual(store.snapshot(),local);
});

test('rejects malformed manual sync keys',()=>{
  const sync=createPhraseBookCloudSync({store:storeStub(),storage:memoryStorage(),cryptoApi:fixedCrypto()});
  assert.throws(()=>sync.setKey('too-short'),/invalid-sync-key/);
});
