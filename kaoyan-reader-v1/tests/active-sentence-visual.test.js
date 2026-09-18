import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const readalong = readFileSync(join(root, 'readalong.css'), 'utf8');
const styles = readFileSync(join(root, 'styles.css'), 'utf8');
const controls = readFileSync(join(root, 'reader-controls.css'), 'utf8');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const app = readFileSync(join(root, 'app.js'), 'utf8');
const bootstrap = readFileSync(join(root, 'full-library-bootstrap.js'), 'utf8');

test('playing sentence is visually active rather than dimmed', () => {
  assert.doesNotMatch(readalong, /\.sentence-card\.is-active[^\{]*\{[^}]*opacity\s*:\s*\.42/);
  assert.match(readalong, /\.sentence-card\.is-active\s*\{[^}]*background\s*:\s*rgba\(37,99,235,\.06\)/);
  assert.match(readalong, /\.sentence-card::before\s*\{[^}]*background\s*:\s*#2563eb/);
  assert.match(readalong, /\.sentence-card\.is-active::before\s*\{[^}]*opacity\s*:\s*1/);
  assert.match(readalong, /\.sentence-card\.is-active \.en\s*\{[^}]*color\s*:\s*#17191c[^}]*font-weight\s*:\s*650/);
  assert.match(readalong, /\.sentence-card\.is-active \.zh\s*\{[^}]*color\s*:\s*#5f6b78/);
  assert.match(readalong, /\.sentence-card\.is-active \.sentence-number\s*\{[^}]*background\s*:\s*transparent[^}]*color\s*:\s*#2563eb/);
  assert.doesNotMatch(readalong, /sentence-play-icon/);
  assert.match(readalong, /\.sentence-card\.is-active \.en \.read-token,[\s\S]*?opacity\s*:\s*1/);
  assert.match(readalong, /\.sentence-card\.is-active \.zh \.semantic-group\s*\{[^}]*opacity\s*:\s*1/);
});

test('vocabulary highlight is continuous across phrase spaces instead of per-token decoration', () => {
  assert.match(styles, /\.vocab\s*\{[\s\S]*?-webkit-box-decoration-break\s*:\s*slice[\s\S]*?box-decoration-break\s*:\s*slice/);
  assert.doesNotMatch(readalong, /\.en \.vocab\.read-token/);
});


test('reader cleanup removes redundant header chrome and per-sentence play buttons', () => {
  assert.doesNotMatch(html, /class="topline"|class="year-chip"|class="free-chip"|id="content-status"|class="director-card"|id="article-background"/);
  assert.doesNotMatch(html, /先读英文，轻点查译文/);
  assert.match(html, /id="toggle-vocab"/);
  assert.match(html, /id="play-toggle"/);
  assert.match(app, /<span class="sentence-number" aria-hidden="true">/);
  assert.doesNotMatch(app, /sentence-play|sentence-play-icon|#content-status|article-background|year-chip/);
  assert.doesNotMatch(controls, /sentence-play|sentence-play-icon/);
  assert.match(bootstrap, /querySelector\('\.catalog-controls'\)/);
});
