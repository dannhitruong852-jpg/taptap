import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');

test('mobile player collapses into one compact bottom panel',()=>{
  assert.match(css,/\.player-shell\{[^}]*left:0;right:0;bottom:0;[^}]*width:100%;[^}]*min-height:154px;[^}]*border-radius:22px 22px 0 0/s);
  assert.match(css,/\.page-shell\{padding-bottom:calc\(174px \+ env\(safe-area-inset-bottom,0px\)\)\}/);
  assert.doesNotMatch(css,/min-height:218px/);
});

test('title and speed pill share the compact top row',()=>{
  assert.match(css,/\.player-meta\{[^}]*min-height:34px;[^}]*padding:9px 92px 0 16px/s);
  assert.match(css,/\.director-mood\{[^}]*min-height:30px;[^}]*font-size:14px/s);
  assert.match(css,/\.speed-value\{[^}]*position:absolute;[^}]*top:9px;right:16px;[^}]*width:68px;[^}]*height:42px/s);
  assert.match(css,/\.player-position,\.player-status\{display:none\}/);
});

test('all four transport controls remain visible while play stays on the visual centerline',()=>{
  assert.match(css,/\.transport-row\{[^}]*display:grid;[^}]*grid-template-columns:44px 44px 58px 44px 44px;[^}]*gap:10px;[^}]*justify-content:center/s);
  assert.match(css,/\.transport-row \.icon-button\{width:44px;height:44px;?\}/);
  assert.match(css,/\.transport-row \.play-button\{width:58px;height:58px;?\}/);
  assert.match(css,/\.transport-row\{grid-template-columns:44px 44px 56px 44px 44px;gap:7px\}/);
});

test('speed slider remains fully functional inside the compact bottom row',()=>{
  assert.match(css,/\.magnetic-speed\{[^}]*grid-template-columns:48px minmax\(0,1fr\);[^}]*gap:8px;[^}]*padding:2px 18px calc\(9px \+ env\(safe-area-inset-bottom,0px\)\) 16px;[^}]*min-height:50px/s);
  assert.match(css,/#speed-range\{[^}]*height:24px/s);
  assert.match(css,/\.speed-ticks\{[^}]*font-size:10px/s);
});

test('desktop remains a centered rounded dock without regaining old height',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*width:520px;[^}]*left:50%;right:auto;bottom:18px;[^}]*transform:translateX\(-50%\);[^}]*border-radius:22px/s);
  assert.match(css,/\.page-shell\{padding-bottom:190px\}/);
});

test('transport icons stay CSS-centered and preserve play pause states',()=>{
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#replay::before/);
});
