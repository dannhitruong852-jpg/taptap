import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');

test('mobile player is a half-height bottom control bar',()=>{
  assert.match(css,/\.player-shell\{[^}]*left:0;right:0;bottom:0;[^}]*width:100%;[^}]*height:76px;[^}]*min-height:76px;[^}]*border-radius:16px 16px 0 0/s);
  assert.match(css,/\.page-shell\{padding-bottom:calc\(96px \+ env\(safe-area-inset-bottom,0px\)\)\}/);
  assert.doesNotMatch(css,/min-height:154px/);
});

test('transport controls share one shallow row without shrinking tap targets',()=>{
  assert.match(css,/\.transport-row\{[^}]*position:absolute;[^}]*top:2px;left:0;right:0;[^}]*height:52px;[^}]*padding:0/s);
  assert.match(css,/\.transport-row \.icon-button\{width:44px;height:44px;?\}/);
  assert.match(css,/\.transport-row \.play-button\{width:50px;height:50px;?\}/);
  assert.match(css,/#play-toggle\{[^}]*left:50%;[^}]*transform:translateX\(-50%\)/s);
  assert.match(css,/#previous\{[^}]*left:calc\(50% - 124px\)/s);
  assert.match(css,/#replay\{[^}]*left:calc\(50% - 76px\)/s);
  assert.match(css,/#next\{[^}]*left:calc\(50% \+ 30px\)/s);
});

test('title and speed slider occupy the same thin lower strip',()=>{
  assert.match(css,/\.player-meta\{[^}]*position:absolute;[^}]*left:8px;bottom:0;[^}]*height:22px;[^}]*padding:0/s);
  assert.match(css,/\.director-mood\{[^}]*min-height:0;[^}]*font-size:10px/s);
  assert.match(css,/\.magnetic-speed\{[^}]*position:absolute;[^}]*left:0;right:0;bottom:0;/s);
  assert.match(css,/\.magnetic-speed\{[^}]*height:22px;min-height:22px;[^}]*padding:0 10px 1px 96px;/s);
  assert.match(css,/\.speed-value\{[^}]*position:absolute;[^}]*top:-45px;right:8px;[^}]*width:56px;[^}]*height:36px/s);
  assert.match(css,/#speed-range\{[^}]*height:13px/s);
  assert.match(css,/\.speed-ticks\{[^}]*font-size:8px/s);
});

test('desktop remains centered while using the same ultra-compact height',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*width:520px;[^}]*left:50%;right:auto;bottom:18px;[^}]*transform:translateX\(-50%\);[^}]*border-radius:16px/s);
  assert.match(css,/\.page-shell\{padding-bottom:112px\}/);
});

test('transport icons stay CSS-centered and preserve play pause states',()=>{
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#replay::before/);
});
