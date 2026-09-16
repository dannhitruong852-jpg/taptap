import test from 'node:test';
import assert from 'node:assert/strict';
import {createWebAudioPlayer} from '../web-audio-player.js';

class FakeSource{
  constructor(ctx){this.ctx=ctx;this.playbackRate={value:1};this.onended=null;}
  connect(){}
  start(when=0,offset=0){this.started={when,offset};this.ctx.lastSource=this;}
  stop(){this.stopped=true;}
  finish(){this.onended?.();}
}
class FakeContext{
  constructor(){this.currentTime=10;this.destination={};this.state='running';this.lastSource=null;}
  createBufferSource(){return new FakeSource(this);}
  resume(){this.state='running';return Promise.resolve();}
}
const flush=async()=>{await Promise.resolve();await Promise.resolve();await Promise.resolve();};

test('decoded buffer starts through AudioBufferSourceNode and advances queue',async()=>{
  const ctx=new FakeContext();const ended=[];const started=[];
  const player=createWebAudioPlayer({
    audioContext:ctx,
    resolveDecoded:async segment=>({buffer:{duration:Number(segment.duration_seconds||1)}}),
    schedule:()=>0,cancelSchedule:()=>{},
    onSegmentStart:segment=>started.push(segment.id),
    onSentenceEnd:()=>ended.push(true)
  });
  await player.playSentence([{id:'a',duration_seconds:1},{id:'b',duration_seconds:1}],1);
  assert.deepEqual(ctx.lastSource.started,{when:0,offset:0});
  assert.deepEqual(started,['a']);
  ctx.lastSource.finish();await flush();
  assert.deepEqual(started,['a','b']);
  ctx.lastSource.finish();await flush();
  assert.equal(ended.length,1);
});

test('pause and resume rebuild source at the logical media offset',async()=>{
  const ctx=new FakeContext();
  const player=createWebAudioPlayer({audioContext:ctx,resolveDecoded:async()=>({buffer:{duration:10}}),schedule:()=>0,cancelSchedule:()=>{}});
  await player.playSentence([{id:'a',duration_seconds:10}],1);
  ctx.currentTime=12.5;
  player.pause();
  assert.equal(player.getState().paused,true);
  await player.resume();
  assert.equal(ctx.lastSource.started.offset,2.5);
});

test('speed change preserves logical position and updates new source rate',async()=>{
  const ctx=new FakeContext();
  const player=createWebAudioPlayer({audioContext:ctx,resolveDecoded:async()=>({buffer:{duration:10}}),schedule:()=>0,cancelSchedule:()=>{}});
  await player.playSentence([{id:'a',duration_seconds:10}],1);
  ctx.currentTime=12;
  player.setPlaybackRate(1.15);
  await flush();
  assert.equal(ctx.lastSource.started.offset,2);
  assert.equal(ctx.lastSource.playbackRate.value,1.15);
});

test('stop suppresses stale async decode completion',async()=>{
  const ctx=new FakeContext();let release;const gate=new Promise(r=>{release=r;});const started=[];
  const player=createWebAudioPlayer({audioContext:ctx,resolveDecoded:async()=>{await gate;return {buffer:{duration:1}};},schedule:()=>0,cancelSchedule:()=>{},onSegmentStart:s=>started.push(s.id)});
  const pending=player.playSentence([{id:'old',duration_seconds:1}],1);
  player.stop();release();await pending;await flush();
  assert.deepEqual(started,[]);
});

test('decode failure rejects playSentence before playback starts so caller can fall back',async()=>{
  const ctx=new FakeContext();
  const player=createWebAudioPlayer({audioContext:ctx,resolveDecoded:async()=>{throw new Error('decode-failed');},schedule:()=>0,cancelSchedule:()=>{}});
  await assert.rejects(()=>player.playSentence([{id:'a'}],1),/decode-failed/);
});
