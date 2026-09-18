import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const app=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const styles=readFileSync(new URL('../styles.css',import.meta.url),'utf8');

test('phrase-book toolbar puts edit immediately to the right of blur',()=>{
  assert.match(html,/id="phrase-book-blur"[^>]*>模糊译文<\/button>\s*<button id="phrase-book-edit"[^>]*>编辑<\/button>/);
});

test('phrase-book edit mode edits only Chinese study gloss and saves it as user-edited',()=>{
  assert.match(app,/phraseBookEditButton/);
  assert.match(app,/contentEditable/);
  assert.match(app,/glossSource:\s*'user-edited'/);
  assert.match(app,/phraseBookEditButton\.textContent=.*完成/);
  assert.doesNotMatch(app,/selectedText\s*=/);
});

test('player phrase-book label stays fixed while openPhraseBook follows current year',()=>{
  assert.doesNotMatch(app,/\$\{year\}\s*词群本|词群本\$\{count/);
  assert.match(app,/const year=Number\(currentEntry\?\.year\)\|\|Number\(yearSelect\.value\)/);
  assert.doesNotMatch(app,/attachSpeedControl\(/);
});

test('top reader settings no longer contain a duplicate phrase-book entry',()=>{
  const settings=html.match(/<div class="reader-settings">([\s\S]*?)<\/div>\s*<\/div>\s*<\/header>/)?.[1]||'';
  assert.doesNotMatch(settings,/phrase-book-open|词群本/);
  assert.match(styles,/\.phrase-book-toolbar-actions/);
});
