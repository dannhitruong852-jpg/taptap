import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const css=await readFile(new URL('../styles.css',import.meta.url),'utf8');

test('reader removes the two helper copy rows and hides the phrasebook breadcrumb',()=>{
  assert.equal(html.includes('逐句中英对照 · 理解导向的美式日常交流式朗读'),false);
  assert.equal(html.includes('轻点句框查译文'),false);
  assert.match(html,/id="phrase-book-context"[^>]*hidden/);
});

test('phrasebook hides edit and places blur control at the right edge',()=>{
  assert.match(html,/id="phrase-book-edit"[^>]*hidden/);
  assert.match(css,/\.phrase-book-toolbar-actions\s*\{[^}]*margin-left:auto/s);
});

test('article title is thirty percent smaller and stylesheet cache is bumped',()=>{
  assert.match(css,/font-size:\s*clamp\(22px,\s*5\.6vw,\s*36px\)/);
  assert.match(html,/styles\.css\?v=phrasebook-row-swipe-blur-20260929-v1/);
});
