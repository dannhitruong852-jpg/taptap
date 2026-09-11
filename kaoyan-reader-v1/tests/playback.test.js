import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSentenceQueue, applySpeed, nextSentenceIndex } from '../playback.js';
import { createAudioPlayer } from '../audio-player.js';

const sentence10 = { id: 10, segments: [{id:'s10-a'},{id:'s10-b'},{id:'s10-c'}] };
const manifest = { segments: {
  's10-a': {path:'./audio/2002/text1/s10-a.opus'},
  's10-b': {path:'./audio/2002/text1/s10-b.opus'},
  's10-c': {path:'./audio/2002/text1/s10-c.opus'}
}};

test('buildSentenceQueue preserves intra-sentence actor segment order', () => {
  assert.deepEqual(buildSentenceQueue(sentence10, manifest).map(x => x.id), ['s10-a','s10-b','s10-c']);
});

test('user playback speed multiplies generated segment rate without leaving safe browser range', () => {
  assert.equal(applySpeed(1, 0.85), 0.85);
  assert.equal(applySpeed(1, 1.15), 1.15);
});

test('sentence navigation clamps at article bounds', () => {
  assert.equal(nextSentenceIndex(0, -1, 21), 0);
  assert.equal(nextSentenceIndex(20, 1, 21), 20);
});

class FakeAudio {
  constructor(src) { this.src = src; this.playbackRate = 1; this.paused = true; this.preload = ''; }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
  finish() { this.onended?.(); }
}

test('sequencer advances through all segments before ending a sentence', async () => {
  const created = [];
  const ended = [];
  const player = createAudioPlayer({
    createAudio: src => { const a = new FakeAudio(src); created.push(a); return a; },
    onSentenceEnd: () => ended.push(true)
  });
  player.playSentence([
    {id:'s10-a', path:'a.opus'},
    {id:'s10-b', path:'b.opus'},
    {id:'s10-c', path:'c.opus'}
  ], 1);
  assert.equal(created[0].src, 'a.opus');
  created[0].finish();
  assert.equal(created[1].src, 'b.opus');
  created[1].finish();
  assert.equal(created[2].src, 'c.opus');
  created[2].finish();
  assert.equal(ended.length, 1);
});
