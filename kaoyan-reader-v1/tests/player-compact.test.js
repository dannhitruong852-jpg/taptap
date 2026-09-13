import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');

test('mobile player becomes a full-width bottom dock with safe-area spacing',()=>{
  assert.match(css,/\.player-shell\{[^}]*left:0;right:0;bottom:0;[^}]*width:100%;[^}]*border-radius:28px 28px 0 0;[^}]*box-shadow:0 -8px 32px rgba\(0,0,0,\.08\)/s);
  assert.match(css,/\.page-shell\{padding-bottom:calc\(238px \+ env\(safe-area-inset-bottom,0px\)\)\}/);
  assert.doesNotMatch(css,/width:clamp\(236px,62vw,420px\)/);
});

test('primary transport is a symmetric previous-play-next group',()=>{
  const transport=html.match(/<div class="transport-row">([\s\S]*?)<\/div>/)?.[1]||'';
  assert.match(css,/\.transport-row\{[^}]*display:grid;[^}]*grid-template-columns:46px 64px 46px;[^}]*justify-content:center/s);
  assert.match(css,/\.transport-row \.icon-button\{width:46px;height:46px;?\}/);
  assert.match(css,/\.transport-row \.play-button\{width:64px;height:64px;?\}/);
  assert.match(css,/gap:18px/);
  assert.match(transport,/id="previous"[\s\S]*id="play-toggle"[\s\S]*id="next"/);
  assert.doesNotMatch(transport,/id="replay"/);
  assert.match(html,/<button id="replay"[^>]*hidden[^>]*>/);
});

test('previous and next use balanced inline SVG chevrons',()=>{
  assert.match(html,/<button id="previous"[^>]*>[\s\S]*?<svg class="transport-icon"[^>]*>[\s\S]*?<path d="M14\.5 5\.5 8 12l6\.5 6\.5"\/>[\s\S]*?<\/svg>[\s\S]*?<\/button>/);
  assert.match(html,/<button id="next"[^>]*>[\s\S]*?<svg class="transport-icon"[^>]*>[\s\S]*?<path d="m9\.5 5\.5 6\.5 6\.5-6\.5 6\.5"\/>[\s\S]*?<\/svg>[\s\S]*?<\/button>/);
  assert.match(css,/\.transport-icon\{[^}]*width:20px;height:20px;[^}]*stroke:currentColor;[^}]*stroke-width:2;[^}]*stroke-linecap:round;[^}]*stroke-linejoin:round/s);
  assert.match(css,/\.transport-row \.icon-button::after\{[^}]*inset:3px;[^}]*border-radius:50%;[^}]*background:#f1f0ec/s);
});

test('speed control starts near 86px and keeps the value pill in the top right',()=>{
  assert.match(css,/\.magnetic-speed\{[^}]*grid-template-columns:54px minmax\(0,1fr\);[^}]*padding:8px 28px [^;]+ 20px/s);
  assert.match(css,/\.speed-value\{[^}]*position:absolute;[^}]*top:16px;right:20px;[^}]*width:70px;[^}]*height:48px/s);
  assert.match(css,/\.player-position,\.player-status\{display:none\}/);
});

test('desktop restores a centered rounded dock',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*width:520px;[^}]*left:50%;right:auto;bottom:18px;[^}]*transform:translateX\(-50%\);[^}]*border-radius:28px/s);
});

test('play and pause icons remain CSS-centered independent of font glyph metrics',()=>{
  assert.match(css,/\.transport-row \.play-button::before,\.transport-row \.play-button::after/);
  assert.match(css,/#play-toggle\[aria-label="暂停"\]::after/);
});
