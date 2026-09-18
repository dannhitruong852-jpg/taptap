import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const html = readFileSync(join(root, 'index.html'), 'utf8');
const staticCache = readFileSync(join(root, 'static-resource-cache.js'), 'utf8');
const release = 'phrase-study-edit-20260919-v1';

test('reader UI assets share a release cache-busting version', () => {
  for (const asset of ['styles.css', 'catalog.css', 'readalong.css', 'reader-controls.css', 'app.js', 'full-library-bootstrap.js']) {
    const escaped = asset.replaceAll('.', '\\.');
    assert.match(html, new RegExp(`\\./${escaped}\\?v=${release}`), `${asset} must use release ${release}`);
  }
});

test('persistent static resource cache is versioned with the reader release', () => {
  assert.match(staticCache, new RegExp(`DEFAULT_NAMESPACE='kaoyan-static-${release}'`));
});
