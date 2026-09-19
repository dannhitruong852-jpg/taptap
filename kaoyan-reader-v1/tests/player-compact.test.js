import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const css=readFileSync(new URL('../reader-controls.css',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');

test('player keeps the approved 76px dock size',()=>{
  assert.match(css,/\.player-shell\{[^}]*height:76px;[^}]*min-height:76px/s);
  assert.match(css,/\.player-grabber\{[^}]*width:34px;height:4px/s);
});

test('player contains exactly previous article next article play pause and phrase-book controls',()=>{
  assert.match(html,/id="previous"[^>]*aria-label="上一篇"/);
  assert.match(html,/id="next"[^>]*aria-label="下一篇"/);
  assert.match(html,/id="play-toggle"[^>]*aria-label="播放"/);
  assert.match(html,/id="phrase-book-open"[^>]*aria-haspopup="dialog"/);
  assert.doesNotMatch(html,/id="replay"/);
  assert.doesNotMatch(html,/id="speed-control"/);
  assert.doesNotMatch(html,/id="speed-range"/);
});

test('X-style visual hierarchy uses two small pale controls one larger dark play control and phrase-book pill',()=>{
  assert.match(css,/\.article-nav\{[^}]*width:44px;height:44px/s);
  assert.match(css,/\.article-nav::after\{[^}]*width:32px;height:32px;[^}]*background:#f0ece4/s);
  assert.match(css,/\.play-button\{[^}]*width:52px;height:52px/s);
  assert.match(css,/\.play-button::after\{[^}]*width:46px;height:46px;[^}]*background:#28251f/s);
  assert.match(css,/\.player-phrase-book\{[^}]*width:68px;height:38px;[^}]*border-radius:19px/s);
});

test('phrase-book replaces the old speed menu in the bottom dock',()=>{
  assert.match(html,/id="phrase-book-open"/);
  assert.match(html,/id="phrase-book-backdrop"/);
  assert.match(html,/id="phrase-book-list"/);
  assert.doesNotMatch(html,/id="speed-value"/);
  assert.doesNotMatch(css,/\.speed-menu\{/);
});

test('player motion stays vertical and uses the X-like eased dock transition',()=>{
  assert.match(css,/\.player-shell\{[^}]*transition:transform \.42s cubic-bezier\(\.2,\.8,\.2,1\),opacity \.32s ease/s);
  assert.match(css,/\.player-shell\.is-collapsed\{[^}]*transform:translate3d\(0,calc\(100% \+ 28px \+ env\(safe-area-inset-bottom,0px\)\),0\);[^}]*opacity:0/s);
  assert.doesNotMatch(css,/\.player-shell\.is-collapsed\{[^}]*translateX/s);
});

test('desktop retains horizontal centering in both visible and hidden states',()=>{
  assert.match(css,/@media\(min-width:768px\)\{[^}]*\.player-shell\{[^}]*transform:translate3d\(-50%,0,0\)/s);
  assert.match(css,/\.player-shell\.is-collapsed\{transform:translate3d\(-50%,calc\(100% \+ 46px\),0\)\}/);
});
