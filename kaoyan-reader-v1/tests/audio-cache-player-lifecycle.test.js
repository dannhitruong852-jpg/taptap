import test from 'node:test';
import assert from 'node:assert/strict';
import {createAudioPlayer} from '../audio-player.js';

class FakeAudio {
  constructor(src){this.src=src;this.paused=true;this.currentTime=0;this.duration=1;}
  play(){this.paused=false;return Promise.resolve();}
  pause(){this.paused=true;}
  finish(){this.onended?.();}
}

test('resolved local source pins itself for playback and unpins when ended',async()=>{
  const events=[];const created=[];
  const player=createAudioPlayer({
    resolveAudio:async item=>({
      src:`blob:cache/${item.id}`,key:`k:${item.id}`,local:true,
      pin:()=>events.push(`pin:${item.id}`),
      unpin:()=>events.push(`unpin:${item.id}`)
    }),
    createAudio:src=>{const audio=new FakeAudio(src);created.push(audio);return audio;}
  });
  player.playSentence([{id:'s1',path:'remote.opus'}]);
  await Promise.resolve();await Promise.resolve();
  assert.deepEqual(events,['pin:s1']);
  created[0].finish();
  await Promise.resolve();
  assert.deepEqual(events,['pin:s1','unpin:s1']);
});
