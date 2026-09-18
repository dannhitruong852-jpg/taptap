import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('reader exposes phrase selection action and phrase book panel',()=>{
  assert.match(html,/id="phrase-selection-action"/);
  assert.match(html,/id="phrase-book-open"/);
  assert.match(html,/id="phrase-book-panel"/);
  assert.match(html,/id="phrase-book-blur"/);
  assert.match(html,/id="phrase-book-list"/);
});

test('reader wires selection to existing sentence data without translation API',()=>{
  assert.match(app,/resolvePhraseSnippet/);
  assert.match(app,/createPhraseBookStore/);
  assert.match(app,/selectionchange/);
  assert.match(app,/translationSnippet/);
  assert.doesNotMatch(app,/openai|anthropic|translate\.google|translation provider/i);
});

test('phrase book blur is visual-only and selection action is mobile-safe',()=>{
  assert.match(css,/\.phrase-translation\.is-blurred[^}]*filter\s*:\s*blur/s);
  assert.match(css,/\.phrase-selection-action[^}]*position\s*:\s*fixed/s);
  assert.match(css,/\.en[^}]*-webkit-user-select\s*:\s*text/s);
});