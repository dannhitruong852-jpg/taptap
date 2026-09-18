import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('reader exposes phrase-book selection action and phrase-book panel',()=>{
  assert.match(html,/id="phrase-book-open"/);
  assert.match(html,/id="phrase-selection-action"/);
  assert.match(html,/id="phrase-book-panel"/);
  assert.match(html,/id="phrase-book-blur"/);
});

test('reader reuses current selection and sentence data without translation API',()=>{
  assert.match(app,/resolvePhraseSnippet/);
  assert.match(app,/createPhraseBookStore/);
  assert.match(app,/selectionchange/);
  assert.match(app,/translationSnippet/);
  assert.doesNotMatch(app,/openai|anthropic|translate\.google|translation provider/i);
});

test('phrase-book blur is presentation-only and mobile text remains selectable',()=>{
  assert.match(css,/\.phrase-translation\.is-blurred[^}]*filter\s*:\s*blur/s);
  assert.match(css,/\.sentence-content[^}]*touch-action\s*:\s*manipulation/s);
  assert.match(css,/\.en[^}]*user-select\s*:\s*text/s);
});
