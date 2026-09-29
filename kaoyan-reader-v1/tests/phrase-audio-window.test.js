import test from 'node:test';
import assert from 'node:assert/strict';
import {alignedPhraseWindow,estimatedPhraseWindow} from '../phrase-audio-window.js';

const words=[
  {word:'one',char_start:0,char_end:3,start:.10,end:.40},
  {word:'two',char_start:4,char_end:7,start:.48,end:.78},
  {word:'three',char_start:8,char_end:13,start:.86,end:1.30},
  {word:'four',char_start:14,char_end:18,start:1.38,end:1.72},
];

test('aligned phrase window follows real word timestamps instead of text percentage',()=>{
  const clip=alignedPhraseWindow(words,4,13,2);
  assert.equal(clip.source,'aligned');
  assert.equal(clip.firstWord,1);
  assert.equal(clip.lastWord,2);
  assert.ok(clip.start>=.40&&clip.start<=.48);
  assert.ok(clip.end>=1.30&&clip.end<=1.38);
});

test('aligned phrase window never crosses neighbor midpoint padding',()=>{
  const clip=alignedPhraseWindow(words,8,13,2);
  assert.ok(clip.start>=.82);
  assert.ok(clip.end<=1.34);
});

test('estimated window remains a fallback when timestamps are unavailable',()=>{
  const clip=estimatedPhraseWindow('one two three four',4,13,2);
  assert.equal(clip.source,'estimated');
  assert.ok(clip.end>clip.start);
});
