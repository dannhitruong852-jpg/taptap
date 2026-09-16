import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

test('full-library bootstrap waits for rendered reader and starts coordinator automatically',()=>{
  const source=readFileSync(new URL('../full-library-bootstrap.js',import.meta.url),'utf8');
  assert.match(source,/createFullLibraryCacheCoordinator/);
  assert.match(source,/whenReaderReady/);
  assert.match(source,/coordinator\.start\(\)/);
  assert.match(source,/beforeunload/);
});
