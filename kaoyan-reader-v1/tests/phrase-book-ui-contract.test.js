import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('reader exposes bottom phrase study bar and year phrase book',()=>{
  for(const id of ['phrase-study-bar','phrase-highlight-selection','phrase-highlight-action','phrase-book-open','phrase-book-backdrop','phrase-book-year','phrase-book-blur','phrase-book-list']){
    assert.match(html,new RegExp(`id="${id}"`));
  }
});

test('reader reuses trusted sentence mappings and one inline store',()=>{
  assert.match(app,/resolveLinkedHighlight/);
  assert.match(app,/createInlineHighlightStore/);
  assert.match(app,/snippetFromRanges/);
  assert.match(app,/selectionchange/);
  assert.match(app,/translationSnippet/);
  assert.doesNotMatch(app,/openai|anthropic|translate\.google|translation provider/i);
});

test('phrase book blur is visual-only and bottom action avoids native menu overlap',()=>{
  assert.match(css,/\.phrase-book-panel\.is-blurred \.phrase-book-zh\.has-translation[^}]*filter\s*:\s*blur/s);
  assert.match(css,/\.phrase-study-bar\s*\{[^}]*position\s*:\s*fixed[^}]*bottom\s*:/s);
  assert.match(css,/\.en[^}]*-webkit-user-select\s*:\s*text/s);
  assert.doesNotMatch(app,/positionPhraseHighlightAction/);
});
