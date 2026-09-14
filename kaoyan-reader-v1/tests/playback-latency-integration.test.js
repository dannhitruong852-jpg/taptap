import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
test('reader warms current plus next three sentences and viewport-near audio through persistent cache',()=>{
  assert.match(app,/createAudioCache\(\)/);
  assert.match(app,/warmRange\(0,4\)/);
  assert.match(app,/audioCache\.warm\(warm\)/);
  assert.match(app,/resolveAudio:item=>audioCache\.resolve\(item\)/);
  assert.match(app,/pinAudio:key=>audioCache\.pin\(key\)/);
  assert.match(app,/unpinAudio:key=>audioCache\.unpin\(key\)/);
  assert.match(app,/warmVisibleSentences\(\)/);
  assert.doesNotMatch(app,/audioPlayer\.preload\(warm\)/);
  assert.doesNotMatch(app,/new Audio\(\);preload\.preload='auto'/);
});
