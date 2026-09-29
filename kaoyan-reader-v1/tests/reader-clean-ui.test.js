import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const css=await readFile(new URL('../styles.css',import.meta.url),'utf8');
const app=await readFile(new URL('../app.js',import.meta.url),'utf8');

test('reader removes the two helper copy rows and hides the phrasebook breadcrumb',()=>{
  assert.equal(html.includes('逐句中英对照 · 理解导向的美式日常交流式朗读'),false);
  assert.equal(html.includes('轻点句框查译文'),false);
  assert.match(html,/id="phrase-book-context"[^>]*hidden/);
});

test('phrasebook hides edit and places blur control at the right edge',()=>{
  assert.match(html,/id="phrase-book-edit"[^>]*hidden/);
  assert.match(css,/\.phrase-book-toolbar-actions\s*\{[^}]*margin-left:auto/s);
});

test('phrasebook swipe uses compositor transform follow and spring return',()=>{
  assert.match(css,/\.phrase-book-row\s*\{[^}]*transform:\s*translate3d\(var\(--phrase-swipe-x,0px\),0,0\)[^}]*transition:\s*transform 220ms cubic-bezier\(\.22,\.9,\.28,1\.12\)/s);
  assert.match(css,/\.phrase-book-row\.is-swipe-dragging\s*\{[^}]*transition:none[^}]*will-change:transform/s);
});

test('article title is thirty percent smaller and stylesheet cache is bumped',()=>{
  assert.match(css,/font-size:\s*clamp\(22px,\s*5\.6vw,\s*36px\)/);
  assert.match(html,/styles\.css\?v=phrasebook-swipe-motion-20260929-v1/);
});


test('app cache-busts the inline phrase store module when row-blur APIs change',()=>{
  const appImport=app.match(/from '\.\/inline-phrase-highlights\.js\?v=([^']+)'/);
  assert.ok(appImport,'inline phrase store import must be versioned');
  assert.equal(appImport[1],'phrasebook-row-swipe-blur-20260929-v1');
});
