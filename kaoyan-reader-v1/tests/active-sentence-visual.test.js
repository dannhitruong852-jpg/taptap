import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const readalong = readFileSync(join(root, 'readalong.css'), 'utf8');
const styles = readFileSync(join(root, 'styles.css'), 'utf8');

test('playing sentence is visually active rather than dimmed', () => {
  assert.doesNotMatch(readalong, /\.sentence-card\.is-active[^\{]*\{[^}]*opacity\s*:\s*\.42/);
  assert.match(readalong, /\.sentence-card\.is-active\s*\{[^}]*background\s*:\s*rgba\(37,99,235,\.06\)/);
  assert.match(readalong, /\.sentence-card::before\s*\{[^}]*background\s*:\s*#2563eb/);
  assert.match(readalong, /\.sentence-card\.is-active::before\s*\{[^}]*opacity\s*:\s*1/);
  assert.match(readalong, /\.sentence-card\.is-active \.en\s*\{[^}]*color\s*:\s*#17191c[^}]*font-weight\s*:\s*650/);
  assert.match(readalong, /\.sentence-card\.is-active \.zh\s*\{[^}]*color\s*:\s*#5f6b78/);
  assert.match(readalong, /\.sentence-card\.is-active \.sentence-play-icon\s*\{[^}]*color\s*:\s*#2563eb[^}]*opacity\s*:\s*1/);
  assert.match(readalong, /\.sentence-card\.is-active \.en \.read-token,[\s\S]*?opacity\s*:\s*1/);
  assert.match(readalong, /\.sentence-card\.is-active \.zh \.semantic-group\s*\{[^}]*opacity\s*:\s*1/);
});

test('vocabulary highlight is continuous across phrase spaces instead of per-token decoration', () => {
  assert.match(styles, /\.vocab\s*\{[\s\S]*?-webkit-box-decoration-break\s*:\s*slice[\s\S]*?box-decoration-break\s*:\s*slice/);
  assert.doesNotMatch(readalong, /\.en \.vocab\.read-token/);
});
