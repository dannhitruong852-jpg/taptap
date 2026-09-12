import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');
test('player is narrower and transport icons are CSS-centered independent of font glyph metrics',()=>{
  assert.match(css,/\.player-shell\{width:min\(600px,calc\(100% - 40px\)\)/);
  assert.match(css,/\.transport-row \.icon-button::before,\.transport-row \.play-button::before/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
  assert.match(css,/#previous::before\{[^}]*translate\(-42%,-50%\)/s);
  assert.match(css,/#next::before\{[^}]*translate\(-58%,-50%\)/s);
});
