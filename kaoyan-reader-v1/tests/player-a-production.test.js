import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');

test('production player uses previous play next phrase-book order and chevrons',()=>{
  assert.match(html,/id="previous"[\s\S]*id="play-toggle"[\s\S]*id="next"[\s\S]*id="phrase-book-open"/);
  assert.match(html,/transport-icon/);
  assert.match(html,/grid-template-columns:46px 56px 46px 68px/);
  assert.doesNotMatch(html,/id="speed-control"/);
});
