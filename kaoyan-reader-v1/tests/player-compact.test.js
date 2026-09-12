import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');
test('player is about 30 percent narrower while touch targets stay accessible',()=>{
  assert.match(css,/\.player-shell\{width:clamp\(236px,62vw,420px\);\}/);
  assert.match(css,/\.transport-row \.icon-button\{width:44px;height:44px;\}/);
  assert.match(css,/\.transport-row \.play-button\{width:56px;height:56px;\}/);
  assert.doesNotMatch(css,/@media\(max-width:430px\)\{\.player-shell\{width:calc\(100% - 40px\)/);
});
test('transport icons remain CSS-centered independent of font glyph metrics',()=>{
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#previous::before\{[^}]*translate\(-42%,-50%\)/s);
  assert.match(css,/#next::before\{[^}]*translate\(-58%,-50%\)/s);
});
