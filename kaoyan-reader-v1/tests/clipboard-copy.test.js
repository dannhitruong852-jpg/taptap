import test from 'node:test';
import assert from 'node:assert/strict';
import { copyTextWithFallback } from '../clipboard-copy.js';

test('copies the exact selected phrase with the modern clipboard API',async()=>{
  let written='';
  const ok=await copyTextWithFallback('take into account',{
    clipboard:{writeText:async value=>{written=value;}},
    legacyCopy:()=>false,
  });
  assert.equal(ok,true);
  assert.equal(written,'take into account');
});

test('falls back to legacy copy when the modern clipboard API is unavailable',async()=>{
  let written='';
  const ok=await copyTextWithFallback('in light of',{
    clipboard:null,
    legacyCopy:value=>{written=value;return true;},
  });
  assert.equal(ok,true);
  assert.equal(written,'in light of');
});

test('clipboard failure stays isolated from phrase-book saving',async()=>{
  const ok=await copyTextWithFallback('on the grounds that',{
    clipboard:{writeText:async()=>{throw new Error('denied');}},
    legacyCopy:()=>false,
  });
  assert.equal(ok,false);
});
