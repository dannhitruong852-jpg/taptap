import test from 'node:test';
import assert from 'node:assert/strict';
import {measureLatency} from '../latency-metrics.js';

test('measureLatency returns deterministic milliseconds',()=>{
  assert.deepEqual(measureLatency('article-switch',10,34.5),{label:'article-switch',duration_ms:24.5});
});

test('audio start metric clamps negative clock anomalies to zero',()=>{
  assert.deepEqual(measureLatency('audio-start',100,99),{label:'audio-start',duration_ms:0});
});
