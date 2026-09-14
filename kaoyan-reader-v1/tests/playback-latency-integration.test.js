import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');

test('reader warms current plus next three sentences and viewport-near audio through persistent cache',()=>{
  assert.match(app,/createAudioCache\(\)/);
  assert.match(app,/warmRange\(0,4\)/);
  assert.match(app,/audioCache\.warm\(warm\)/);
  assert.match(app,/resolveAudio:item=>audioCache\.resolve\(item\)/);
  assert.match(app,/warmVisibleSentences\(\)/);
  assert.doesNotMatch(app,/audioPlayer\.preload\(warm\)/);
  assert.doesNotMatch(app,/new Audio\(\);preload\.preload='auto'/);
});

test('reader routes article selection through resident RAM bundles and starts global preload',()=>{
  assert.match(app,/createArticleBundleStore/);
  assert.match(app,/articleBundleStore\.get\(entry\)/);
  assert.match(app,/articleBundleStore\.preload\(/);
  assert.doesNotMatch(app,/const loadSelection=createSelectionLoader\(\)/);
});
