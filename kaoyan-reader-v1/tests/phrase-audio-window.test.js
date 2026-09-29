import test from 'node:test';
import assert from 'node:assert/strict';
import {alignedPhraseWindow,refinePhraseWindowWithWaveform,estimatedPhraseWindow} from '../phrase-audio-window.js';

const words=[
  {word:'one',char_start:0,char_end:3,start:.10,end:.40},
  {word:'two',char_start:4,char_end:7,start:.48,end:.78},
  {word:'three',char_start:8,char_end:13,start:.86,end:1.30},
  {word:'four',char_start:14,char_end:18,start:1.38,end:1.72},
];

function fakeBuffer({duration=2,sampleRate=1000,regions=[]}={}){
  const data=new Float32Array(Math.ceil(duration*sampleRate));
  for(const [start,end,amplitude] of regions){
    for(let i=Math.floor(start*sampleRate);i<Math.min(data.length,Math.ceil(end*sampleRate));i++)data[i]=amplitude;
  }
  return {sampleRate,length:data.length,duration,numberOfChannels:1,getChannelData:()=>data};
}

test('aligned phrase window follows real word timestamps instead of text percentage',()=>{
  const clip=alignedPhraseWindow(words,4,13,2);
  assert.equal(clip.source,'aligned');
  assert.equal(clip.firstWord,1);
  assert.equal(clip.lastWord,2);
  assert.ok(clip.start>=.40&&clip.start<=.48);
  assert.ok(clip.end>=1.30&&clip.end<=1.38);
});

test('aligned phrase window never starts before previous aligned word ends',()=>{
  const clip=alignedPhraseWindow(words,8,13,2);
  assert.ok(clip.start>=.78);
  assert.ok(clip.end<=1.38);
});

test('waveform refinement expands to real onset and cuts trailing silence quickly',()=>{
  const localWords=[
    {word:'before',char_start:0,char_end:6,start:.12,end:.25},
    {word:'target',char_start:7,char_end:13,start:.42,end:.76},
    {word:'after',char_start:14,char_end:19,start:.95,end:1.20},
  ];
  const coarse=alignedPhraseWindow(localWords,7,13,1.5);
  const buffer=fakeBuffer({duration:1.5,regions:[[.08,.27,.65],[.35,.82,.8],[.91,1.22,.7]]});
  const clip=refinePhraseWindowWithWaveform(buffer,coarse);
  assert.equal(clip.source,'aligned-waveform');
  assert.ok(clip.start>=.31&&clip.start<=.35,`start=${clip.start}`);
  assert.ok(clip.end>=.82&&clip.end<=.85,`end=${clip.end}`);
});

test('waveform refinement cannot run into the next word when there is no silence',()=>{
  const localWords=[
    {word:'target',char_start:0,char_end:6,start:.20,end:.60},
    {word:'after',char_start:7,char_end:12,start:.68,end:1.0},
  ];
  const coarse=alignedPhraseWindow(localWords,0,6,1.2);
  const buffer=fakeBuffer({duration:1.2,regions:[[.12,1.02,.75]]});
  const clip=refinePhraseWindowWithWaveform(buffer,coarse);
  assert.ok(clip.end<=.68,`end=${clip.end}`);
});

test('estimated window remains a fallback when timestamps are unavailable',()=>{
  const clip=estimatedPhraseWindow('one two three four',4,13,2);
  assert.equal(clip.source,'estimated');
  assert.ok(clip.end>clip.start);
});
