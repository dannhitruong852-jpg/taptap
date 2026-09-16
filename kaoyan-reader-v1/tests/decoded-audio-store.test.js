import test from 'node:test';
import assert from 'node:assert/strict';
import {createDecodedAudioStore} from '../decoded-audio-store.js';

test('concurrent decoded requests share one byte load and one decode',async()=>{
  let byteCalls=0,decodeCalls=0;
  const audioCache={getArrayBuffer:async item=>{byteCalls+=1;return {buffer:new Uint8Array([1,2,3]).buffer,key:`k:${item.generation_fingerprint}`};}};
  const audioContext={decodeAudioData:async()=>{decodeCalls+=1;return {duration:2.5};}};
  const store=createDecodedAudioStore({audioContext,audioCache});
  const item={path:'./x.opus',generation_fingerprint:'v1'};
  const [a,b]=await Promise.all([store.get(item,{articleId:'a'}),store.get(item,{articleId:'a'})]);
  assert.strictEqual(a.buffer,b.buffer);
  assert.equal(byteCalls,1);
  assert.equal(decodeCalls,1);
});

test('generation fingerprint produces a distinct decoded identity',async()=>{
  let decodeCalls=0;
  const audioCache={getArrayBuffer:async item=>({buffer:new Uint8Array([1]).buffer,key:`k:${item.generation_fingerprint}`})};
  const audioContext={decodeAudioData:async()=>({duration:++decodeCalls})};
  const store=createDecodedAudioStore({audioContext,audioCache});
  const a=await store.get({path:'./x.opus',generation_fingerprint:'v1'},{articleId:'a'});
  const b=await store.get({path:'./x.opus',generation_fingerprint:'v2'},{articleId:'a'});
  assert.notEqual(a.key,b.key);
  assert.equal(decodeCalls,2);
});

test('dropArticle releases decoded RAM only and never deletes persistent audio',async()=>{
  let deleteCalls=0;
  const audioCache={
    getArrayBuffer:async item=>({buffer:new Uint8Array([1]).buffer,key:`k:${item.path}`}),
    delete:()=>{deleteCalls+=1;}
  };
  const audioContext={decodeAudioData:async()=>({duration:1})};
  const store=createDecodedAudioStore({audioContext,audioCache});
  await store.get({path:'a.opus'},{articleId:'a'});
  await store.get({path:'b.opus'},{articleId:'b'});
  store.dropArticle('a');
  assert.equal(store.has({path:'a.opus'}),false);
  assert.equal(store.getState().decoded,1);
  assert.equal(deleteCalls,0);
});

test('preload decodes a list for one article and reuses resident buffers',async()=>{
  let decodeCalls=0;
  const audioCache={getArrayBuffer:async item=>({buffer:new Uint8Array([1]).buffer,key:`k:${item.path}`})};
  const audioContext={decodeAudioData:async()=>{decodeCalls+=1;return {duration:1};}};
  const store=createDecodedAudioStore({audioContext,audioCache});
  const items=[{path:'a.opus'},{path:'b.opus'}];
  await store.preload(items,{articleId:'article-a'});
  await store.get(items[0],{articleId:'article-a'});
  assert.equal(decodeCalls,2);
});
