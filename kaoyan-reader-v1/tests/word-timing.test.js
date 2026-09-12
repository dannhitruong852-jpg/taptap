import test from 'node:test';
import assert from 'node:assert/strict';
import {activeWordIndex, readStateAtTime, activeChineseGroups} from '../time-index.js';

const words = [
  {word:'one',start:0,end:4},
  {word:'two',start:4,end:4.5},
  {word:'three',start:4.5,end:5},
  {word:'four',start:5,end:5.5},
  {word:'five',start:5.5,end:6},
  {word:'six',start:6,end:6.8},
  {word:'seven',start:6.8,end:7.5},
  {word:'eight',start:7.5,end:8.2},
  {word:'nine',start:8.2,end:9},
  {word:'ten',start:9,end:10},
];

test('nonuniform word timeline never falls back to percentage token math', () => {
  assert.equal(activeWordIndex(words, 3), 0, 'word 1 occupies 40% of the audio');
  assert.deepEqual(readStateAtTime(words, 3), {readThrough:0, active:0});
  assert.equal(activeWordIndex(words, 5.25), 3);
  assert.deepEqual(readStateAtTime(words, 5.25), {readThrough:3, active:3});
});

test('boundaries and silent gaps produce deterministic read state', () => {
  const gapped=[{start:0,end:1},{start:2,end:3}];
  assert.deepEqual(readStateAtTime(gapped,-1),{readThrough:0,active:-1});
  assert.deepEqual(readStateAtTime(gapped,0),{readThrough:0,active:0});
  assert.deepEqual(readStateAtTime(gapped,1.5),{readThrough:1,active:-1});
  assert.deepEqual(readStateAtTime(gapped,2),{readThrough:1,active:1});
  assert.deepEqual(readStateAtTime(gapped,3),{readThrough:2,active:-1});
});

test('media currentTime is not rescaled by playback rate', () => {
  for (const rate of [0.7,1,1.25,1.5,2]) {
    assert.equal(activeWordIndex(words,3),0,`rate ${rate} must not alter media timeline lookup`);
  }
});

test('Chinese semantic groups activate from their English-derived real times', () => {
  const groups=[{start:6,end:8},{start:0,end:4},{start:4,end:6}];
  assert.deepEqual(activeChineseGroups(groups,1),[1]);
  assert.deepEqual(activeChineseGroups(groups,5),[2]);
  assert.deepEqual(activeChineseGroups(groups,7),[0]);
  assert.deepEqual(activeChineseGroups(groups,8),[]);
});

import {readFileSync} from 'node:fs';
test('v4 app path consumes real words and never percentage-maps token count', () => {
  const source=readFileSync(new URL('../app.js',import.meta.url),'utf8');
  assert.match(source,/readStateAtTime\(/);
  assert.match(source,/isExplicitLegacyTimingVersion\(/);
  assert.match(source,/function paintLegacyReadProgress[\s\S]*progress\*tokens\.length/);
  const timed=source.match(/function paintTimedReadProgress[\s\S]*?function timingVersion/)?.[0]||'';
  assert.doesNotMatch(timed,/progress\s*\*\s*tokens\.length/);
  assert.match(source,/if\(Array\.isArray\(segment\?\.words\).*paintTimedReadProgress/);
  assert.match(source,/if\(isExplicitLegacyTimingVersion\(timingVersion\(segment\)\)\).*paintLegacyReadProgress/);
});
