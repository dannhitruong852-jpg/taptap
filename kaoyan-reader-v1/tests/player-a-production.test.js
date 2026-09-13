import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
test('production player uses A order and chevrons',()=>{
  assert.match(html,/id="previous"[\s\S]*id="play-toggle"[\s\S]*id="next"[\s\S]*id="speed-control"/);
  assert.match(html,/transport-icon/);
  assert.match(html,/grid-template-columns:46px 56px 46px 68px/);
});
