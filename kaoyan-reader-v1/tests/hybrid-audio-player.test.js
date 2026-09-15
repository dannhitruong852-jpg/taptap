import test from 'node:test';
import assert from 'node:assert/strict';
import {createHybridAudioPlayer} from '../hybrid-audio-player.js';

function stub(extra={}){return {playSentence(){},stop(){},pause(){},resume(){},setPlaybackRate(){},getState(){return {};},...extra};}

test('hybrid player prefers Web Audio and falls back to HTMLAudio when Web Audio start rejects',async()=>{
  const events=[];
  const web=stub({async playSentence(){events.push('web');throw new Error('decode');}});
  const fallback=stub({playSentence(){events.push('fallback');}});
  const player=createHybridAudioPlayer({getWebPlayer:()=>web,fallbackPlayer:fallback});
  await player.playSentence([{id:'s01'}],1);
  assert.deepEqual(events,['web','fallback']);
  assert.equal(player.getState().engine,'fallback');
});

test('hybrid player uses fallback immediately when Web Audio is unavailable',async()=>{
  const events=[];
  const fallback=stub({playSentence(){events.push('fallback');}});
  const player=createHybridAudioPlayer({getWebPlayer:()=>null,fallbackPlayer:fallback});
  await player.playSentence([{id:'s01'}],1);
  assert.deepEqual(events,['fallback']);
});

test('control methods are forwarded to the active engine and stop silences both',async()=>{
  const events=[];
  const web=stub({async playSentence(){events.push('web-play');},pause(){events.push('web-pause');},resume(){events.push('web-resume');},setPlaybackRate(){events.push('web-rate');},stop(){events.push('web-stop');}});
  const fallback=stub({stop(){events.push('fallback-stop');}});
  const player=createHybridAudioPlayer({getWebPlayer:()=>web,fallbackPlayer:fallback});
  await player.playSentence([{id:'s'}],1);
  player.pause();await player.resume();player.setPlaybackRate(1.15);player.stop();
  assert.deepEqual(events,['web-play','web-pause','web-resume','web-rate','web-stop','fallback-stop']);
});
