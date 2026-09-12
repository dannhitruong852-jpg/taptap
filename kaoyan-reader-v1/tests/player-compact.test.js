import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');

test('mobile player becomes a full-width bottom dock with safe-area spacing',()=>{
  assert.match(css,/\.player-shell\{[^}]*left:0;right:0;bottom:0;[^}]*width:100%;[^}]*border-radius:28px 28px 0 0;[^}]*box-shadow:0 -8px 32px rgba\(0,0,0,\.08\)/s);
  assert.match(css,/\.page-shell\{padding-bottom:calc\(238px \+ env\(safe-area-inset-bottom,0px\)\)\}/);
  assert.doesNotMatch(css,/width:clamp\(236px,62vw,420px\)/);
});

test('transport grid keeps the play button on the exact visual center',()=>{
  assert.match(css,/\.transport-row\{[^}]*display:grid;[^}]*grid-template-columns:52px 52px 68px 52px 52px;[^}]*justify-content:center/s);
  assert.match(css,/\.transport-row \.icon-button\{width:52px;height:52px;\}/);
  assert.match(css,/\.transport-row \.play-button\{width:68px;height:68px;\}/);
  assert.match(css,/gap:clamp\(8px,3vw,12px\)/);
});

test('speed control starts near 86px and keeps the value pill in the top right',()=>{
  assert.match(css,/\.magnetic-speed\{[^}]*grid-template-columns:54px minmax\(0,1fr\);[^}]*padding:8px 28px [^;]+ 20px/s);
  assert.match(css,/\.speed-value\{[^}]*position:absolute;[^}]*top:16px;right:20px;[^}]*width:70px;[^}]*height:48px/s);
  assert.match(css,/\.player-position,\.player-status\{display:none\}/);
});

test('desktop restores a centered rounded dock',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*width:520px;[^}]*left:50%;right:auto;bottom:18px;[^}]*transform:translateX\(-50%\);[^}]*border-radius:28px/s);
});

test('transport icons remain CSS-centered independent of font glyph metrics',()=>{
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#previous::before\{[^}]*translate\(-42%,-50%\)/s);
  assert.match(css,/#next::before\{[^}]*translate\(-58%,-50%\)/s);
});
