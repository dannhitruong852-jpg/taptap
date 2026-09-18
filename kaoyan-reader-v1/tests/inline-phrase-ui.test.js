import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('selection action is a fixed bottom study bar, not a selection-adjacent bubble',()=>{
  assert.match(html,/id="phrase-study-bar"/);
  assert.match(html,/id="phrase-highlight-selection"/);
  assert.match(html,/id="phrase-highlight-action"/);
  assert.match(css,/\.phrase-study-bar\s*\{[^}]*position\s*:\s*fixed/s);
  assert.match(css,/\.phrase-study-bar\s*\{[^}]*bottom\s*:/s);
  assert.doesNotMatch(app,/getBoundingClientRect\(\).*positionPhraseHighlightAction/s);
});

test('one mark automatically feeds a year-scoped phrase book',()=>{
  for(const id of ['phrase-book-open','phrase-book-backdrop','phrase-book-year','phrase-book-list','phrase-book-blur']){
    assert.match(html,new RegExp(`id="${id}"`));
  }
  assert.match(app,/inlineHighlightStore\.listYear/);
  assert.match(app,/currentEntry\?\.year/);
  assert.match(app,/translationSnippet/);
});

test('marking keeps single-tap translation and double-tap replay paths intact',()=>{
  assert.match(app,/single:\(\)=>\{if\(!loading&&card\.isConnected\)toggleTranslation\(card\);\}/);
  assert.match(app,/double:\(\)=>\{[\s\S]*?speak\(Number\(card\.dataset\.index\),\{scroll:false\}\)/);
});

test('release versions the modules involved in phrase marking',()=>{
  assert.match(app,/\.\/bilingual-text\.js\?v=/);
  assert.match(app,/\.\/reader-controls\.js\?v=/);
  assert.match(app,/\.\/inline-phrase-highlights\.js\?v=/);
});
