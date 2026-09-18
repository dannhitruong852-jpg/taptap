import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');
const bilingual=readFileSync(new URL('../bilingual-text.js',import.meta.url),'utf8');

test('reader uses one inline mark action and no phrase-book UI',()=>{
  assert.match(html,/id="phrase-highlight-action"/);
  assert.doesNotMatch(html,/phrase-book/);
  assert.match(app,/from '\.\/inline-phrase-highlights\.js'/);
  assert.match(app,/resolveLinkedHighlight/);
  assert.match(app,/addEventListener\('selectionchange'/);
});

test('English and linked Chinese receive persistent inline mark classes',()=>{
  assert.match(css,/\.phrase-mark-en/);
  assert.match(css,/\.phrase-mark-zh/);
  assert.match(app,/phrase-mark-en/);
  assert.match(app,/phrase-mark-zh/);
  assert.match(bilingual,/data-zh-start/);
  assert.match(bilingual,/data-zh-end/);
});