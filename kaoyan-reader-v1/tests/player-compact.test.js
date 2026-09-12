import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');

test('mobile player is a half-height bottom control bar',()=>{
  assert.match(css,/\.player-shell\{[^}]*left:0;right:0;bottom:0;[^}]*width:100%;[^}]*height:76px;[^}]*min-height:76px;[^}]*border-radius:16px 16px 0 0/s);
  assert.match(css,/\.page-shell\{padding-bottom:calc\(96px \+ env\(safe-area-inset-bottom,0px\)\)\}/);
  assert.doesNotMatch(css,/min-height:154px/);
});

test('transport controls keep accessible hit boxes while visible circles shrink to seventy percent',()=>{
  assert.match(css,/\.transport-row\{[^}]*position:absolute;[^}]*top:2px;left:0;right:0;[^}]*height:52px;[^}]*padding:0/s);
  assert.match(css,/\.transport-row \.icon-button\{width:44px;height:44px;[^}]*background:radial-gradient\(circle at center,#ebe6dc 0 35%,transparent 36%\)/s);
  assert.match(css,/\.transport-row \.play-button\{width:50px;height:50px;[^}]*background:radial-gradient\(circle at center,#24231f 0 35%,transparent 36%\)/s);
  assert.match(css,/#previous::before,#next::before\{width:7px;height:7px;/);
  assert.match(css,/#replay::before\{width:12px;height:12px;/);
  assert.match(css,/#play-toggle::before\{[^}]*border-top:6px solid transparent;[^}]*border-bottom:6px solid transparent;[^}]*border-left:10px solid currentColor/s);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::before\{width:3px;height:12px;/);
});

test('transport controls stay centered without changing playback geometry',()=>{
  assert.match(css,/#play-toggle\{[^}]*left:50%;[^}]*transform:translateX\(-50%\)/s);
  assert.match(css,/#previous\{[^}]*left:calc\(50% - 124px\)/s);
  assert.match(css,/#replay\{[^}]*left:calc\(50% - 76px\)/s);
  assert.match(css,/#next\{[^}]*left:calc\(50% \+ 30px\)/s);
});

test('player enters and exits only through the bottom at half the previous animation speed',()=>{
  assert.match(css,/\.player-shell\{[^}]*transform:translate3d\(0,0,0\);[^}]*transition:transform \.56s cubic-bezier\([^)]*\),opacity \.44s ease/s);
  assert.match(css,/\.player-shell\.is-collapsed\{[^}]*transform:translate3d\(0,calc\(100% \+ 32px \+ env\(safe-area-inset-bottom,0px\)\),0\);[^}]*opacity:0/s);
  assert.doesNotMatch(css,/\.player-shell\.is-collapsed\{[^}]*translate\(-50%/s);
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

test('desktop keeps the same horizontal center in visible and collapsed states',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*width:520px;[^}]*left:50%;right:auto;bottom:18px;[^}]*transform:translate3d\(-50%,0,0\);[^}]*border-radius:16px/s);
  assert.match(css,/\.player-shell\.is-collapsed\{transform:translate3d\(-50%,calc\(100% \+ 50px\),0\)\}/);
  assert.match(css,/\.page-shell\{padding-bottom:112px\}/);
});

test('transport icons stay CSS-centered and preserve play pause states',()=>{
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#replay::before/);
});

test('reduced-motion users still get an instant dock transition',()=>{
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)\{[^}]*\.player-shell\{transition:none\}/s);
});
