import test from 'node:test';
import assert from 'node:assert/strict';
import {createFullLibraryCacheCoordinator} from '../full-library-cache.js';

test('coordinator forwards incremental audio progress to state callbacks',async()=>{
  const catalog={articles:[{id:'a'},{id:'b'}]};
  const bundles={
    a:{content:{sentences:[{id:'s1',segments:[]}]},manifest:{sentences:{s1:{path:'./a.opus'}}}},
    b:{content:{sentences:[{id:'s2',segments:[]}]},manifest:{sentences:{s2:{path:'./b.opus'}}}}
  };
  const snapshots=[];
  const coordinator=createFullLibraryCacheCoordinator({
    catalog,
    articleBundleStore:{get:async entry=>bundles[entry.id]},
    audioCache:{ensurePersistentMany:async (items,{onProgress})=>{onProgress({total:2,completed:1,failed:0});onProgress({total:2,completed:2,failed:0});return {total:2,completed:2,failed:0};}},
    onProgress:state=>snapshots.push(state)
  });
  await coordinator.start();
  assert.ok(snapshots.some(state=>state.audioDone===1&&state.audioTotal===2));
  assert.equal(snapshots.at(-1).audioDone,2);
});
