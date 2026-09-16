import test from 'node:test';
import assert from 'node:assert/strict';
import { createAudioPlayer } from '../audio-player.js';

class FakeAudio {
  constructor(src) { this.src=src; this.preload=''; this.paused=true; this.currentTime=0; this.loadCalls=0; }
  load() { this.loadCalls += 1; }
  play() { this.paused=false; return Promise.resolve(); }
  pause() { this.paused=true; }
}

test('preloaded audio object is reused when that sentence is played', () => {
  const created=[];
  const player=createAudioPlayer({createAudio:src=>{const audio=new FakeAudio(src);created.push(audio);return audio;}});
  player.preload([{id:'s01',path:'s01.opus'}]);
  assert.equal(created.length,1);
  assert.equal(created[0].preload,'auto');
  assert.equal(created[0].loadCalls,1);
  player.playSentence([{id:'s01',path:'s01.opus'}],1);
  assert.equal(created.length,1,'playback must reuse the warmed Audio object instead of creating a new request');
  assert.equal(created[0].paused,false);
});
