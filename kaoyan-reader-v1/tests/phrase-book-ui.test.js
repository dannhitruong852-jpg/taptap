import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('reader exposes phrase-book selection action and panel',()=>{
  for(const id of ['phrase-book-open','phrase-selection-action','phrase-book-panel','phrase-book-blur','phrase-book-list']){
    assert.match(html,new RegExp(`id="${id}"`));
  }
});

test('reader maps selected English to existing sentence translation data',()=>{
  assert.match(app,/from '\.\/phrase-book\.js'/);
  assert.match(app,/addEventListener\('selectionchange'/);
  assert.match(app,/closest\('\.en'\)/);
  assert.match(app,/resolvePhraseSnippet\(/);
  assert.match(app,/bilingualMappings\[snapshot\.sentence\.id\]/);
  assert.match(app,/semanticMappings\[snapshot\.sentence\.id\]/);
  assert.match(app,/createPhraseBookStore/);
  assert.match(app,/window\.localStorage/);
  assert.doesNotMatch(app,/openai|anthropic|translate\.google|translation provider/i);
});

test('phrase save uses pointer events and review blur is presentation-only',()=>{
  assert.match(app,/phraseSelectionAction\.addEventListener\('pointerdown'/);
  assert.match(app,/phraseSelectionAction\.addEventListener\('pointerup'/);
  assert.match(css,/\.phrase-book-panel\.is-blurred \.phrase-book-zh/);
  assert.match(css,/filter:blur\(/);
  assert.match(css,/\.en\s*\{[^}]*user-select\s*:\s*text/s);
});
