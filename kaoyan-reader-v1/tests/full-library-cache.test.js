import test from 'node:test';
import assert from 'node:assert/strict';
import {createFullLibraryCacheCoordinator} from '../full-library-cache.js';

function fixtures(){
  const catalog={articles:[{id:'a'},{id:'b'}]};
  const bundles={
    a:{content:{sentences:[{id:'s1',segments:[]}]},manifest:{generation_fingerprint:'ga',sentences:{s1:{path:'./a.opus',mp3_path:'./a.mp3'}}}},
    b:{content:{sentences:[{id:'s2',segments:[]}]},manifest:{generation_fingerprint:'gb',sentences:{s2:{path:'./b.opus',mp3_path:'./b.mp3'}}}}
  };
  return {catalog,bundles};
}

test('coordinator traverses all articles and persists every preferred-codec asset',async()=>{
  const {catalog,bundles}=fixtures();const seen=[];
  const coordinator=createFullLibraryCacheCoordinator({catalog,articleBundleStore:{get:async entry=>bundles[entry.id]},audioCache:{ensurePersistentMany:async items=>{seen.push(...items);return {total:items.length,completed:items.length,failed:0};}},supportsOpus:true});
  const state=await coordinator.start();
  assert.equal(state.status,'complete');
  assert.equal(state.articlesDone,2);
  assert.deepEqual(seen.map(x=>x.path),['./a.opus','./b.opus']);
});

test('coordinator uses mp3 fallback when opus is unsupported',async()=>{
  const {catalog,bundles}=fixtures();const seen=[];
  const coordinator=createFullLibraryCacheCoordinator({catalog,articleBundleStore:{get:async entry=>bundles[entry.id]},audioCache:{ensurePersistentMany:async items=>{seen.push(...items);return {total:items.length,completed:items.length,failed:0};}},supportsOpus:false});
  await coordinator.start();
  assert.deepEqual(seen.map(x=>x.path),['./a.mp3','./b.mp3']);
});

test('coordinator continues after one article fails',async()=>{
  const {catalog,bundles}=fixtures();const seen=[];
  const coordinator=createFullLibraryCacheCoordinator({catalog,articleBundleStore:{get:async entry=>{if(entry.id==='a')throw new Error('bad article');return bundles[entry.id];}},audioCache:{ensurePersistentMany:async items=>{seen.push(...items);return {total:items.length,completed:items.length,failed:0};}},supportsOpus:true});
  const state=await coordinator.start();
  assert.equal(state.status,'complete');
  assert.equal(state.failed,1);
  assert.deepEqual(seen.map(x=>x.path),['./b.opus']);
});
