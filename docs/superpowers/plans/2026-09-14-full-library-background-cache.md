# Automatic Full-Library Background Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one site visit automatically persist every catalog article and every required audio asset in the background so warm revisits across arbitrary years/articles are local-first without manual traversal.

**Architecture:** Extend the existing version-aware audio cache with a persistent-only path that stores compressed bytes without creating Blob URLs or decoding them. Add a small static JSON CacheStorage layer for article content/manifest/bilingual mappings, then add a `FullLibraryCacheCoordinator` that enumerates `catalog.articles`, persists all required resources with bounded concurrency, and resumes naturally via cache hits on later visits. The existing RAM-first article store and Web Audio working set remain intact.

**Tech Stack:** Browser ES modules, Fetch API, Cache Storage API, `navigator.storage.persist()`, Web Audio API (existing active-player layer only), Node 22 `node:test`, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-14-full-library-background-cache-design.md`

## Global Constraints

- The selected/default article must render before full-library caching begins.
- The user must not need to visit each year/article manually.
- Full-library audio caching stores compressed bytes only; it must not create Blob/Object URLs or decode the entire library into `AudioBuffer` objects.
- Audio cache identity remains path + generation fingerprint/file hash.
- Persistent audio retention remains cumulative with no application quota, LRU, age limit, or automatic deletion.
- Already cached unchanged assets must not be downloaded again.
- Killing/reopening the page must preserve completed CacheStorage writes and resume by skipping cache hits.
- Only the device-selected audio format is required for background caching: Opus when supported, MP3 fallback otherwise.
- Cache failure must not make the reader unusable.
- Existing RAM-first article switching, Web Audio playback, HTMLAudio fallback, bilingual highlighting, actor assignments, C-mode timing, and existing production audio remain unchanged.
- No existing audio regeneration is allowed for this feature.

---

### Task 1: Add persistent-only audio cache APIs

**Files:**
- Modify: `kaoyan-reader-v1/audio-cache.js`
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`

**Interfaces:**
- Consumes: existing `audioCacheKey(item)` and internal `responseFor(item,key)` semantics.
- Produces:
  - `ensurePersistent(item) -> Promise<{key:string, cached:boolean}>`
  - `ensurePersistentMany(items,{concurrency=4}={}) -> Promise<{total:number, completed:number, failed:number}>`
- These methods persist compressed bytes only and never create Blob/Object URLs.

- [ ] **Step 1: Write failing persistent-only tests**

Append to `kaoyan-reader-v1/tests/audio-cache.test.js`:

```js
test('ensurePersistent stores bytes without creating Blob URLs',async()=>{
  const storage=fakeCacheStorage();let fetchCalls=0;let objectUrls=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async()=>{fetchCalls+=1;return new FakeResponse('audio-bytes');},
    createObjectURL:()=>{objectUrls+=1;return 'blob:unexpected';},
    revokeObjectURL:()=>{}
  });
  const item={path:'./audio/a.opus',generation_fingerprint:'v1'};
  const first=await cache.ensurePersistent(item);
  const second=await cache.ensurePersistent(item);
  assert.equal(fetchCalls,1);
  assert.equal(objectUrls,0);
  assert.equal(first.key,second.key);
  assert.equal(first.cached,false);
  assert.equal(second.cached,true);
});

test('ensurePersistentMany persists unique assets with bounded workers and reports failures',async()=>{
  const storage=fakeCacheStorage();let active=0,maxActive=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    storageManager:null,
    fetcher:async path=>{
      active+=1;maxActive=Math.max(maxActive,active);
      await new Promise(resolve=>setTimeout(resolve,5));
      active-=1;
      if(path.includes('bad'))return new FakeResponse('x',{ok:false});
      return new FakeResponse(`audio:${path}`);
    }
  });
  const items=[
    {path:'./a.opus',generation_fingerprint:'1'},
    {path:'./a.opus',generation_fingerprint:'1'},
    {path:'./b.opus',generation_fingerprint:'2'},
    {path:'./bad.opus',generation_fingerprint:'3'}
  ];
  const result=await cache.ensurePersistentMany(items,{concurrency:2});
  assert.deepEqual(result,{total:3,completed:2,failed:1});
  assert.ok(maxActive<=2);
});
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/audio-cache.test.js
```

Expected: FAIL because `ensurePersistent` / `ensurePersistentMany` are not exported by the cache instance.

- [ ] **Step 3: Implement minimal persistent-only APIs**

Inside `createAudioCache()` add:

```js
async function ensurePersistent(item){
  if(!item?.path)throw new Error('audio-path-required');
  const key=audioCacheKey(item);
  const store=await persistent();
  if(!store)throw new Error('persistent-cache-unavailable');
  let hit;
  try{hit=await store.match(key);}catch{throw new Error('persistent-cache-unavailable');}
  if(hit)return {key,cached:true};
  const response=await responseFor(item,key);
  if(!response)throw new Error('audio-bytes-unavailable');
  return {key,cached:false};
}

async function ensurePersistentMany(items=[],{concurrency=4}={}){
  const unique=[];const seen=new Set();
  for(const item of items){
    if(!item?.path)continue;
    const key=audioCacheKey(item);
    if(seen.has(key))continue;
    seen.add(key);unique.push(item);
  }
  let cursor=0,completed=0,failed=0;
  const worker=async()=>{
    while(cursor<unique.length){
      const item=unique[cursor++];
      try{await ensurePersistent(item);completed+=1;}catch{failed+=1;}
    }
  };
  const workerCount=Math.min(Math.max(1,Number(concurrency)||1),unique.length||1);
  await Promise.all(Array.from({length:workerCount},()=>worker()));
  return {total:unique.length,completed,failed};
}
```

Return both methods from `createAudioCache()`.

Important: do not call `resolve()`, `blob()`, `arrayBuffer()`, or `createObjectURL()` in these methods.

- [ ] **Step 4: Run focused and full Node tests**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/audio-cache.test.js
npm test
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/tests/audio-cache.test.js
git commit -m "feat: persist background audio without decoding"
```

---

### Task 2: Add persistent cache for static article resources

**Files:**
- Create: `kaoyan-reader-v1/static-resource-cache.js`
- Create: `kaoyan-reader-v1/tests/static-resource-cache.test.js`
- Modify: `kaoyan-reader-v1/article-bundle-store.js`
- Modify: `kaoyan-reader-v1/tests/article-bundle-store.test.js`

**Interfaces:**
- Produces `createStaticResourceCache({cacheStorage,fetcher,namespace='kaoyan-static-v1'})` with:
  - `json(url,{refresh=true}={}) -> Promise<object>`
  - `ensure(url) -> Promise<{cached:boolean}>`
- `ArticleBundleStore` receives optional `resourceCache`; when present, content/manifest/bilingual loads use `resourceCache.json(url)` instead of raw `fetcher(url)`.

- [ ] **Step 1: Write failing static-cache tests**

Create `kaoyan-reader-v1/tests/static-resource-cache.test.js`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {createStaticResourceCache} from '../static-resource-cache.js';

class JsonResponse{
  constructor(value,{ok=true}={}){this.value=value;this.ok=ok;}
  clone(){return new JsonResponse(structuredClone(this.value),{ok:this.ok});}
  async json(){return structuredClone(this.value);}
}
function fakeStorage(){
  const store=new Map();
  const cache={
    async match(key){return store.get(String(key));},
    async put(key,response){store.set(String(key),response.clone());}
  };
  return {store,async open(){return cache;}};
}

test('json serves a persistent hit without blocking on network when refresh is disabled',async()=>{
  const storage=fakeStorage();let fetchCalls=0;
  const cache=createStaticResourceCache({cacheStorage:storage,fetcher:async()=>{fetchCalls+=1;return new JsonResponse({version:1});}});
  assert.deepEqual(await cache.json('./content/a.json',{refresh:false}),{version:1});
  assert.deepEqual(await cache.json('./content/a.json',{refresh:false}),{version:1});
  assert.equal(fetchCalls,1);
});

test('ensure writes a missing resource and then reports cached',async()=>{
  const storage=fakeStorage();let fetchCalls=0;
  const cache=createStaticResourceCache({cacheStorage:storage,fetcher:async()=>{fetchCalls+=1;return new JsonResponse({ok:true});}});
  assert.deepEqual(await cache.ensure('./x.json'),{cached:false});
  assert.deepEqual(await cache.ensure('./x.json'),{cached:true});
  assert.equal(fetchCalls,1);
});
```

- [ ] **Step 2: Run test and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/static-resource-cache.test.js`

Expected: FAIL because `static-resource-cache.js` does not exist.

- [ ] **Step 3: Implement `static-resource-cache.js`**

Use the URL string itself as the cache key so article resources preserve normal request identity:

```js
const DEFAULT_NAMESPACE='kaoyan-static-v1';

export function createStaticResourceCache({
  cacheStorage=typeof caches!=='undefined'?caches:null,
  fetcher=typeof fetch!=='undefined'?fetch.bind(globalThis):null,
  namespace=DEFAULT_NAMESPACE
}={}){
  let storePromise=null;
  const inflight=new Map();
  async function store(){
    if(!cacheStorage)return null;
    if(!storePromise)storePromise=Promise.resolve(cacheStorage.open(namespace)).catch(()=>null);
    return storePromise;
  }
  async function ensure(url){
    const s=await store();
    if(!s)throw new Error('static-cache-unavailable');
    const hit=await s.match(url).catch(()=>null);
    if(hit)return {cached:true};
    if(inflight.has(url))return inflight.get(url);
    const task=(async()=>{
      const response=await fetcher(url);
      if(!response?.ok)throw new Error('static-resource-fetch-failed');
      await s.put(url,response.clone());
      return {cached:false};
    })().finally(()=>inflight.delete(url));
    inflight.set(url,task);
    return task;
  }
  async function json(url,{refresh=false}={}){
    const s=await store();
    if(!s){
      const response=await fetcher(url);if(!response?.ok)throw new Error('static-resource-fetch-failed');return response.json();
    }
    const hit=await s.match(url).catch(()=>null);
    if(hit){
      if(refresh)void (async()=>{try{const r=await fetcher(url);if(r?.ok)await s.put(url,r.clone());}catch{}})();
      return hit.json();
    }
    const response=await fetcher(url);if(!response?.ok)throw new Error('static-resource-fetch-failed');await s.put(url,response.clone());return response.json();
  }
  return {json,ensure};
}
```

- [ ] **Step 4: Route ArticleBundleStore through the resource cache**

Update constructor:

```js
export function createArticleBundleStore({fetcher=fetch,audioVersion='',concurrency=4,resourceCache=null}={}){
```

Add helper:

```js
async function fetchJson(url,{fallback=null}={}){
  try{
    if(resourceCache)return await resourceCache.json(url,{refresh:true});
    const response=await fetcher(url);
    if(!response.ok)throw new Error('resource-load-failed');
    return response.json();
  }catch(error){
    if(fallback!==null)return fallback;
    throw error;
  }
}
```

Use it for content, manifest, and bilingual mapping. Content remains fatal on failure; manifest/bilingual retain their current safe fallbacks.

- [ ] **Step 5: Add ArticleBundleStore persistent-hit test**

Extend `article-bundle-store.test.js` with a fake `resourceCache` recording calls and assert the second `get()` does not call it because the RAM bundle already exists, while a new store sharing the same fake persistent cache can retrieve the same resource without a network fetch.

- [ ] **Step 6: Run focused and full tests**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/static-resource-cache.test.js tests/article-bundle-store.test.js
npm test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add kaoyan-reader-v1/static-resource-cache.js kaoyan-reader-v1/tests/static-resource-cache.test.js kaoyan-reader-v1/article-bundle-store.js kaoyan-reader-v1/tests/article-bundle-store.test.js
git commit -m "feat: persist article resources for local-first reloads"
```

---

### Task 3: Add FullLibraryCacheCoordinator

**Files:**
- Create: `kaoyan-reader-v1/full-library-cache.js`
- Create: `kaoyan-reader-v1/tests/full-library-cache.test.js`
- Reuse: `kaoyan-reader-v1/playback.js`

**Interfaces:**
- Consumes:
  - `catalog.articles`
  - `articleBundleStore.get(entry)`
  - `audioCache.ensurePersistentMany(items,{concurrency})`
  - codec preference `supportsOpus:boolean`
- Produces `createFullLibraryCacheCoordinator({catalog,articleBundleStore,audioCache,supportsOpus,articleConcurrency=2,audioConcurrency=4,onProgress})` returning:
  - `start() -> Promise<State>`
  - `stop() -> void`
  - `getState() -> State`
- State shape:

```js
{
  status:'idle'|'running'|'complete'|'stopped',
  articlesTotal:0,
  articlesDone:0,
  audioTotal:0,
  audioDone:0,
  failed:0
}
```

- [ ] **Step 1: Write failing coordinator tests**

Create `kaoyan-reader-v1/tests/full-library-cache.test.js` with fixtures for two catalog articles and assert:

```js
test('coordinator traverses all articles without navigation and persists every preferred-codec asset',async()=>{
  const catalog={articles:[{id:'a'},{id:'b'}]};
  const bundles={
    a:{content:{sentences:[{id:'s1',segments:[]}]},manifest:{generation_fingerprint:'ga',sentences:{s1:{path:'./a.opus',mp3_path:'./a.mp3'}}}},
    b:{content:{sentences:[{id:'s2',segments:[]}]},manifest:{generation_fingerprint:'gb',sentences:{s2:{path:'./b.opus',mp3_path:'./b.mp3'}}}}
  };
  const seen=[];
  const coordinator=createFullLibraryCacheCoordinator({
    catalog,
    articleBundleStore:{get:async entry=>bundles[entry.id]},
    audioCache:{ensurePersistentMany:async items=>{seen.push(...items);return {total:items.length,completed:items.length,failed:0};}},
    supportsOpus:true
  });
  const state=await coordinator.start();
  assert.equal(state.status,'complete');
  assert.equal(state.articlesDone,2);
  assert.deepEqual(seen.map(x=>x.path),['./a.opus','./b.opus']);
});
```

Add tests for:

- MP3 path selected when `supportsOpus:false`;
- one article failure increments `failed` and later articles still run;
- calling `stop()` prevents launching later articles;
- second run sharing a fake audio cache only fetches missing assets (cache behavior is exercised through Task 1 implementation).

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/full-library-cache.test.js`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement coordinator**

Core queue derivation:

```js
import {buildSentenceQueue} from './playback.js';

function audioItemsForBundle(bundle,supportsOpus){
  const items=[];
  for(const sentence of bundle?.content?.sentences||[]){
    for(const item of buildSentenceQueue(sentence,bundle.manifest||{segments:{}})){
      const path=!supportsOpus&&item.mp3_path?item.mp3_path:item.path;
      if(path)items.push({...item,path});
    }
  }
  return items;
}
```

`start()` processes article bundles with bounded article concurrency but hands each article's audio list to `ensurePersistentMany(...,{concurrency:audioConcurrency})`. Update state and invoke `onProgress({...state})` after every article and after completion.

Do not call `decodedAudioStore.preload()` or active-player methods.

- [ ] **Step 4: Run coordinator tests and full suite**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/full-library-cache.test.js
npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/full-library-cache.js kaoyan-reader-v1/tests/full-library-cache.test.js
git commit -m "feat: cache the full exam library automatically"
```

---

### Task 4: Integrate automatic startup and passive progress UI

**Files:**
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/index.html`
- Modify: `kaoyan-reader-v1/styles.css`
- Modify: `kaoyan-reader-v1/tests/playback-latency-integration.test.js`

**Interfaces:**
- App creates one `staticResourceCache` and passes it into `createArticleBundleStore()`.
- App creates one `FullLibraryCacheCoordinator` after `catalog` is loaded.
- Full-library `start()` is called only after the first selected article has rendered and controls are enabled.
- Progress is rendered in `#offline-cache-status`.

- [ ] **Step 1: Write failing integration contract**

Extend `playback-latency-integration.test.js`:

```js
test('reader starts full-library persistence automatically after first article render',()=>{
  assert.match(app,/createStaticResourceCache/);
  assert.match(app,/createFullLibraryCacheCoordinator/);
  assert.match(app,/fullLibraryCache\.start\(\)/);
  assert.match(app,/offline-cache-status/);
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback-latency-integration.test.js`

Expected: FAIL because app integration does not exist.

- [ ] **Step 3: Add passive progress element**

In `index.html`, directly below `#content-status` add:

```html
<p id="offline-cache-status" class="offline-cache-status" aria-live="polite">离线缓存准备中</p>
```

Add lightweight CSS that does not alter the reader layout materially:

```css
.offline-cache-status{margin:.25rem 0 0;font-size:.78rem;opacity:.62}
```

- [ ] **Step 4: Wire caches and coordinator in `app.js`**

Add imports:

```js
import {createStaticResourceCache} from './static-resource-cache.js';
import {createFullLibraryCacheCoordinator} from './full-library-cache.js';
```

Create:

```js
const staticResourceCache=createStaticResourceCache();
const articleBundleStore=createArticleBundleStore({resourceCache:staticResourceCache});
const offlineCacheStatus=document.querySelector('#offline-cache-status');
let fullLibraryCache=null;
let fullLibraryCacheStarted=false;
```

Replace the previous bare `createArticleBundleStore()` construction.

After catalog loads:

```js
fullLibraryCache=createFullLibraryCacheCoordinator({
  catalog,
  articleBundleStore,
  audioCache,
  supportsOpus,
  onProgress:state=>{
    if(state.status==='complete')offlineCacheStatus.textContent=`离线缓存完成 · ${state.articlesDone}/${state.articlesTotal} 篇`;
    else if(state.status==='running')offlineCacheStatus.textContent=`离线缓存 ${state.articlesDone}/${state.articlesTotal} 篇 · 音频 ${state.audioDone}/${state.audioTotal}`;
    else if(state.status==='stopped')offlineCacheStatus.textContent='离线缓存暂停 · 下次打开自动继续';
  }
});
```

At the end of the first successful `openArticle()` render path:

```js
if(!fullLibraryCacheStarted&&fullLibraryCache){
  fullLibraryCacheStarted=true;
  void fullLibraryCache.start();
}
```

On `beforeunload`, call `fullLibraryCache?.stop()` before releasing RAM.

Do not await `start()`.

- [ ] **Step 5: Run integration and full reader tests**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/playback-latency-integration.test.js
npm test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add kaoyan-reader-v1/app.js kaoyan-reader-v1/index.html kaoyan-reader-v1/styles.css kaoyan-reader-v1/tests/playback-latency-integration.test.js
git commit -m "feat: start full-library cache after first render"
```

---

### Task 5: Prove resume-by-cache-hit and no full-library decoding

**Files:**
- Modify: `kaoyan-reader-v1/tests/full-library-cache.test.js`
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`
- Modify: `docs/standards/PLAYBACK_LATENCY_STANDARD.md`

**Interfaces:**
- Reuses Task 1 persistent-only API and Task 3 coordinator.

- [ ] **Step 1: Add interruption/restart regression test**

Build two coordinator runs sharing one fake CacheStorage-backed `audioCache`:

1. first run stores article A, then `stop()` before B launches;
2. second run starts from the same catalog and same persistent storage;
3. assert A generates no second network fetch;
4. assert B downloads;
5. assert final state is complete.

- [ ] **Step 2: Add no-decode/no-Blob assertion**

Use an audio cache whose `createObjectURL` increments a counter and assert a full-library coordinator run leaves the counter at `0`.

- [ ] **Step 3: Run focused tests**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/audio-cache.test.js tests/full-library-cache.test.js
```

Expected: PASS.

- [ ] **Step 4: Update latency/storage standard**

Append requirements to `docs/standards/PLAYBACK_LATENCY_STANDARD.md`:

```text
- After the initial selected article renders, the reader automatically persists the entire catalog's required text resources and preferred-codec audio assets.
- Full-library persistence is compressed-byte only; it must not decode the entire library or create Blob/Object URLs for background-only assets.
- Reopening the reader resumes by scanning the catalog and skipping versioned CacheStorage hits; completed assets are not downloaded again.
- Full-library persistence never blocks article rendering or explicit audio playback.
```

- [ ] **Step 5: Run full reader suite**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add kaoyan-reader-v1/tests/audio-cache.test.js kaoyan-reader-v1/tests/full-library-cache.test.js docs/standards/PLAYBACK_LATENCY_STANDARD.md
git commit -m "test: verify resumable full-library persistence"
```

---

### Task 6: CI, publish, and real-device verification

**Files:**
- Reuse: `.github/workflows/reader-tests.yml`
- Reuse: `.github/workflows/publish-kaoyan-batch.yml`
- Modify only if needed: `publish-batch.trigger`

**Interfaces:**
- Existing Reader CI should automatically include new `*.test.js` files through `npm test`.
- Existing publish workflow must reuse validated audio artifacts; no TTS/audio generation workflow should run.

- [ ] **Step 1: Verify Reader CI on the final feature commit**

Required evidence:

```text
reader unit/contract tests: success
bilingual highlight tests: success
reviewed mapping rebuild/validation: success
```

- [ ] **Step 2: Trigger the existing publish workflow without changing validated audio source**

Keep the existing validated batch source run ID and make a publish-only trigger commit if required by the workflow.

- [ ] **Step 3: Verify publish workflow**

Required steps all `success`:

```text
resolve validated source run
download merged candidates
validate merged candidates
install validated candidates
rebuild catalog
validate bilingual highlight coverage
validate static reader contract
commit/publish Pages branch
```

- [ ] **Step 4: Verify GitHub Pages deployment**

Require `build`, `report-build-status`, and `deploy` all `success` for the new `gh-pages` head.

- [ ] **Step 5: Real-device smoke checklist**

```text
1. Clear site data for a true cold start.
2. Open the reader and confirm the default article becomes usable before full-library cache completion.
3. Do not manually switch years/articles; watch offline-cache progress advance automatically.
4. Kill the browser before completion.
5. Reopen the site and confirm progress resumes without restarting already completed downloads.
6. Allow full cache to complete.
7. Kill/reopen again.
8. Switch directly between distant years/articles and verify warm local-first rendering.
9. Tap arbitrary sentences in distant years and verify no fresh audio download is needed.
10. Verify Web Audio pause/resume/speed and HTMLAudio fallback behavior remain intact.
```

- [ ] **Step 6: Record final deployment evidence before claiming completion**

Record:

```text
feature branch head SHA
Reader CI run ID + success
publish run ID + success
gh-pages head SHA
Pages deployment run ID + success
```

Do not claim real-device `<50 ms` or full acoustic latency guarantees from CI alone; those require the user's phone measurement.
