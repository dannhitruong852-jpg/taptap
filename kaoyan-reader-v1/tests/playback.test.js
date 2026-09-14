import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSentenceQueue, applySpeed, nextSentenceIndex } from '../playback.js';
import { createAudioPlayer } from '../audio-player.js';

const sentence10 = { id: 's10', segments: [{id:'s10-a'},{id:'s10-b'},{id:'s10-c'}] };
const manifest = { segments: {
  's10-a': {path:'./audio/2002/text1/s10-a.opus'},
  's10-b': {path:'./audio/2002/text1/s10-b.opus'},
  's10-c': {path:'./audio/2002/text1/s10-c.opus'}
}};

test('buildSentenceQueue preserves intra-sentence actor segment order', () => {
  assert.deepEqual(buildSentenceQueue(sentence10, manifest).map(x => x.id), ['s10-a','s10-b','s10-c']);
});

test('buildSentenceQueue prefers one seamless sentence asset when v2 manifest provides it', () => {
  const v2 = { ...manifest, sentences: {
    s10: { id:'s10', path:'./audio/2002/c-text1/s10.opus', mp3_path:'./audio/2002/c-text1/s10.mp3', duration_seconds:6, cues:[{start:0,end:2},{start:2,end:6}] }
  }};
  const queue = buildSentenceQueue(sentence10, v2);
  assert.equal(queue.length, 1);
  assert.equal(queue[0].path, './audio/2002/c-text1/s10.opus');
  assert.equal(queue[0].cues.length, 2);
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
  constructor(src) { this.src = src; this.playbackRate = 1; this.paused = true; this.preload = ''; this.currentTime=0; this.duration=1; }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
  finish() { this.onended?.(); }
  tick(time) { this.currentTime=time; this.ontimeupdate?.(); }
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
  await Promise.resolve();
  assert.equal(created[0].src, 'a.opus');
  created[0].finish();
  await Promise.resolve();
  assert.equal(created[1].src, 'b.opus');
  created[1].finish();
  await Promise.resolve();
  assert.equal(created[2].src, 'c.opus');
  created[2].finish();
  await Promise.resolve();
  assert.equal(ended.length, 1);
});

test('audio player exposes live timing without changing playback order', async () => {
  const created=[]; const updates=[];
  const player=createAudioPlayer({
    createAudio:src=>{const a=new FakeAudio(src);created.push(a);return a;},
    onTimeUpdate:update=>updates.push(update)
  });
  player.playSentence([{id:'s10',path:'s10.opus',duration_seconds:4}],1);
  await Promise.resolve();
  created[0].duration=4;created[0].tick(1.5);
  assert.equal(updates.at(-1).currentTime,1.5);
  assert.equal(updates.at(-1).duration,4);
});

test('sequencer plays the asynchronously resolved local source instead of the remote manifest path', async () => {
  const created=[];
  const player=createAudioPlayer({
    resolveAudio: async item => ({src:`blob:local/${item.id}`,key:`k:${item.id}`,local:true}),
    createAudio:src=>{const audio=new FakeAudio(src);created.push(audio);return audio;}
  });
  player.playSentence([{id:'s10',path:'./audio/remote-s10.opus'}],1);
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(created.length,1);
  assert.equal(created[0].src,'blob:local/s10');
});

test('active local blob source stays pinned until playback ends', async () => {
  const created=[]; const events=[];
  const player=createAudioPlayer({
    resolveAudio: async item => ({src:`blob:local/${item.id}`,key:`k:${item.id}`,local:true}),
    pinAudio:key=>events.push(`pin:${key}`),
    unpinAudio:key=>events.push(`unpin:${key}`),
    createAudio:src=>{const audio=new FakeAudio(src);created.push(audio);return audio;}
  });
  player.playSentence([{id:'s10',path:'./audio/remote-s10.opus'}],1);
  await Promise.resolve();await Promise.resolve();
  assert.deepEqual(events,['pin:k:s10']);
  created[0].finish();
  await Promise.resolve();
  assert.deepEqual(events,['pin:k:s10','unpin:k:s10']);
});
