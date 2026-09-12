import test from 'node:test';
import assert from 'node:assert/strict';
import { sentenceProgress, progressStyle, isExplicitLegacyTimingVersion } from '../progress.js';

test('sentenceProgress maps cue time onto one continuous legacy sentence timeline', () => {
  const cues = [
    { start: 0, end: 2 },
    { start: 2, end: 6 }
  ];
  assert.equal(sentenceProgress(cues, 0, 0), 0);
  assert.equal(sentenceProgress(cues, 0, 1), 1/6);
  assert.equal(sentenceProgress(cues, 1, 1), 3/6);
  assert.equal(sentenceProgress(cues, 1, 4), 1);
});

test('percentage timing is allowed only for explicitly old manifests', () => {
  assert.equal(isExplicitLegacyTimingVersion('v3-content-cast'),true);
  assert.equal(isExplicitLegacyTimingVersion('2002-c-v2-seamless'),true);
  assert.equal(isExplicitLegacyTimingVersion('v1'),true);
  assert.equal(isExplicitLegacyTimingVersion('c-v4-actor-adapter'),false);
  assert.equal(isExplicitLegacyTimingVersion(''),false);
  assert.equal(isExplicitLegacyTimingVersion(undefined),false);
});

test('progressStyle exposes a clamped percentage for the visual progress bar', () => {
  assert.equal(progressStyle(-1), '--read-progress:0%');
  assert.equal(progressStyle(0.375), '--read-progress:37.5%');
  assert.equal(progressStyle(2), '--read-progress:100%');
});
