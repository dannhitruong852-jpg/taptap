import test from 'node:test';
import assert from 'node:assert/strict';
import {createArticleBundleStore} from '../article-bundle-store.js';

test('article bundle store reads article resources through persistent resource cache when supplied',async()=>{
  const calls=[];
  const resourceCache={json:async url=>{calls.push(url);if(url.includes('/audio/'))return {segments:{}};if(url.endsWith('bilingual-highlights.json'))return {version:1,articles:{}};return {article_id:'2003-text1',sentences:[]};}};
  const store=createArticleBundleStore({resourceCache,fetcher:async()=>{throw new Error('raw-fetch-should-not-run');}});
  const entry={id:'2003-text1',year:2003,content:'./content/2003/c/text1.json',manifest:'./audio/2003/v4/c-text1/manifest.json'};
  const bundle=await store.get(entry);
  assert.equal(bundle.content.article_id,'2003-text1');
  assert.equal(calls.length,3);
});
