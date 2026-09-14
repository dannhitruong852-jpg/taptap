import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
test('reader warms current plus next three sentences and viewport-near audio through shared player cache',()=>{
  assert.match(app,/preloadWindow\(0,4\)/);
  assert.match(app,/audioPlayer\.preload\(warm\)/);
  assert.match(app,/warmVisibleSentences\(\)/);
  assert.doesNotMatch(app,/new Audio\(\);preload\.preload='auto'/);
});
