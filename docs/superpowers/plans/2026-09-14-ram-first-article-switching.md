# RAM-First Article Switching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make article switching memory-resident after preload so repeat switches do not perform network requests.

**Architecture:** Add a focused `ArticleBundleStore` that owns content/manifest/bilingual loading, deduplicates year-level bilingual data, retains completed bundles in RAM, and runs bounded background preload. `app.js` asks the store for bundles and starts global preload only after the selected article is rendered.

**Tech Stack:** Browser ES modules, Fetch API, AbortController, Node 22 `node:test`.

**Spec:** `docs/superpowers/specs/2026-09-14-reader-ram-webaudio-zero-latency-design.md`

## Global Constraints

- Resident article switch target: normally <= 50 ms user-perceived.
- A memory hit must not perform fetch or CacheStorage lookup.
- Selected article always outranks global preload.
- Global preload is progressive and bounded; it must not block first render.
- Existing rendering, bilingual highlighting, article navigation, and 2002 compatibility must remain unchanged.
- No content or audio regeneration is allowed for this task.

---

### Task 1: Add the ArticleBundleStore memory contract

**Files:**
- Create: `kaoyan-reader-v1/article-bundle-store.js`
- Create: `kaoyan-reader-v1/tests/article-bundle-store.test.js`
- Reuse: `kaoyan-reader-v1/catalog.js`

**Interfaces:**
- Consumes: `manifestForVersion(entry, audioVersion)` and `bilingualHighlightsPath(entry)` from `catalog.js`.
- Produces: `createArticleBundleStore({fetcher, audioVersion, concurrency})` returning `{get, preload, has, cancelLowPriorityWork, getState}`.
- `get(entry)` resolves `{content, manifest, bilingual}`.

- [ ] **Step 1: Write the failing memory-hit test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {createArticleBundleStore} from '../article-bundle-store.js';

test('second get returns the resident article bundle without new fetches', async()=>{
  const calls=[];
  const fetcher=async url=>{
    calls.push(url);
    if(url.includes('/audio/')) return {ok:true,json:async()=>({sentences:{},segments:{}})};
    if(url.endsWith('bilingual-highlights.json')) return {ok:true,json:async()=>({version:1,articles:{}})};
    return {ok:true,json:async()=>({article_id:'text1',sentences:[]})};
  };
  const entry={id:'2003-text1',year:2003,content:'./content/2003/c/text1.json',manifest:'./audio/2003/v4/c-text1/manifest.json'};
  const store=createArticleBundleStore({fetcher,audioVersion:''});
  const first=await store.get(entry);
  const count=calls.length;
  const second=await store.get(entry);
  assert.strictEqual(second,first);
  assert.equal(calls.length,count);
  assert.equal(store.has(entry.id),true);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/article-bundle-store.test.js`

Expected: FAIL because `../article-bundle-store.js` does not exist.

- [ ] **Step 3: Implement the minimal resident-bundle store**

```js
import {manifestForVersion,bilingualHighlightsPath} from './catalog.js';

export function createArticleBundleStore({fetcher=fetch,audioVersion='',concurrency=4}={}){
  const bundles=new Map();
  const inflight=new Map();
  const yearMappings=new Map();

  async function loadYearMapping(entry){
    if(yearMappings.has(entry.year)) return yearMappings.get(entry.year);
    const promise=fetcher(bilingualHighlightsPath(entry)).then(r=>r.ok?r.json():{version:1,articles:{}}).catch(()=>({version:1,articles:{}}));
    yearMappings.set(entry.year,promise);
    return promise;
  }

  async function load(entry){
    const [content,manifest,bilingual]=await Promise.all([
      fetcher(entry.content).then(r=>{if(!r.ok) throw new Error('content-load-failed');return r.json();}),
      fetcher(manifestForVersion(entry,audioVersion)).then(r=>r.ok?r.json():{segments:{}}).catch(()=>({segments:{}})),
      loadYearMapping(entry)
    ]);
    return {content,manifest,bilingual};
  }

  async function get(entry){
    if(bundles.has(entry.id)) return bundles.get(entry.id);
    if(inflight.has(entry.id)) return inflight.get(entry.id);
    const promise=load(entry).then(bundle=>{bundles.set(entry.id,bundle);return bundle;}).finally(()=>inflight.delete(entry.id));
    inflight.set(entry.id,promise);
    return promise;
  }

  return {
    get,
    preload:async entries=>Promise.allSettled(entries.map(get)),
    has:id=>bundles.has(id),
    cancelLowPriorityWork:()=>{},
    getState:()=>({resident:bundles.size,inflight:inflight.size,concurrency})
  };
}
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/article-bundle-store.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/article-bundle-store.js kaoyan-reader-v1/tests/article-bundle-store.test.js
git commit -m "feat: add resident article bundle store"
```

---

### Task 2: Add bounded preload and interactive priority

**Files:**
- Modify: `kaoyan-reader-v1/article-bundle-store.js`
- Modify: `kaoyan-reader-v1/tests/article-bundle-store.test.js`

**Interfaces:**
- `preload(entries)` queues low-priority work and returns after the queue drains.
- `get(entry)` promotes an already queued entry to interactive priority.
- `cancelLowPriorityWork()` aborts queued/background fetches but never discards resident bundles.

- [ ] **Step 1: Add failing bounded-priority tests**

```js
test('interactive get overtakes queued background preload', async()=>{
  const started=[]; const releases=new Map();
  const fetcher=url=>new Promise(resolve=>{
    started.push(url);
    releases.set(url,()=>resolve({ok:true,json:async()=>url.includes('/audio/')?{segments:{}}:url.endsWith('bilingual-highlights.json')?{version:1,articles:{}}:{article_id:url,sentences:[]}}));
  });
  const make=id=>({id,year:2003,content:`./${id}.json`,manifest:`./audio/${id}.json`});
  const store=createArticleBundleStore({fetcher,concurrency:1});
  const preload=store.preload([make('a'),make('b'),make('c')]);
  await Promise.resolve();
  const urgent=store.get(make('z'));
  for(const release of [...releases.values()]) release();
  await Promise.resolve();
  for(const release of [...releases.values()]) release();
  await Promise.allSettled([preload,urgent]);
  const zIndex=started.findIndex(x=>x.includes('z'));
  const cIndex=started.findIndex(x=>x.includes('c'));
  assert.ok(zIndex>=0&&cIndex>=0&&zIndex<cIndex);
});
```

Add a second test asserting `cancelLowPriorityWork()` does not remove an already resident bundle.

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/article-bundle-store.test.js`

Expected: FAIL because current `preload()` launches every `get()` immediately and has no priority scheduler.

- [ ] **Step 3: Implement a two-queue scheduler**

Use two arrays: `interactiveQueue` and `backgroundQueue`, a `running` counter, and `pump()` that always shifts interactive work first. Each queued job owns an `AbortController`; `cancelLowPriorityWork()` aborts only background jobs and clears the background queue. Preserve `bundles` and `yearMappings`.

Core ordering must be:

```js
function nextJob(){return interactiveQueue.shift()||backgroundQueue.shift()||null;}
function pump(){
  while(running<concurrency){
    const job=nextJob();
    if(!job) break;
    running+=1;
    runJob(job).finally(()=>{running-=1;pump();});
  }
}
```

`get(entry)` must reuse resident/inflight work and, when the entry is only queued in background, move that job into `interactiveQueue` before calling `pump()`.

- [ ] **Step 4: Run focused tests**

Run: `cd kaoyan-reader-v1 && node --test tests/article-bundle-store.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/article-bundle-store.js kaoyan-reader-v1/tests/article-bundle-store.test.js
git commit -m "feat: prioritize interactive article loads"
```

---

### Task 3: Route the reader through ArticleBundleStore

**Files:**
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/tests/playback-latency-integration.test.js`

**Interfaces:**
- Replace `const loadSelection=createSelectionLoader();` with one store instance created after catalog utilities are imported.
- `openArticle(entry)` awaits `articleBundleStore.get(entry)`.
- After first selected article is rendered, call `articleBundleStore.preload(catalog.articles.filter(x=>x.id!==entry.id))` without awaiting it.

- [ ] **Step 1: Write a failing integration contract**

Append:

```js
test('reader routes article selection through the RAM bundle store and starts global preload after render',()=>{
  assert.match(app,/createArticleBundleStore/);
  assert.match(app,/articleBundleStore\.get\(entry\)/);
  assert.match(app,/articleBundleStore\.preload\(/);
  assert.doesNotMatch(app,/const loadSelection=createSelectionLoader\(\)/);
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback-latency-integration.test.js`

Expected: FAIL because `app.js` still uses `createSelectionLoader()`.

- [ ] **Step 3: Implement app integration**

Update imports:

```js
import {pickArticle,selectArticles,adjacentArticle} from './catalog.js';
import {createArticleBundleStore} from './article-bundle-store.js';
```

Create the store once:

```js
const articleBundleStore=createArticleBundleStore();
let globalArticlePreloadStarted=false;
```

Inside `openArticle(entry)` replace selection loading with:

```js
articleBundleStore.cancelLowPriorityWork();
const loaded=await articleBundleStore.get(entry);
if(!loaded||selectionToken!==selectionGeneration)return;
```

After render/update work completes:

```js
if(!globalArticlePreloadStarted&&catalog){
  globalArticlePreloadStarted=true;
  void articleBundleStore.preload(catalog.articles.filter(item=>item.id!==entry.id));
}
```

Do not await global preload.

- [ ] **Step 4: Run integration and full Node suite**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/playback-latency-integration.test.js
npm test
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/playback-latency-integration.test.js
git commit -m "feat: switch articles from resident RAM bundles"
```

---

### Task 4: Add a no-fetch repeat-switch behavioral test and latency instrumentation

**Files:**
- Create: `kaoyan-reader-v1/latency-metrics.js`
- Create: `kaoyan-reader-v1/tests/latency-metrics.test.js`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `docs/standards/PLAYBACK_LATENCY_STANDARD.md`

**Interfaces:**
- `measureLatency(label, start, end=performance.now())` returns `{label,duration_ms}` and emits `performance.measure` when supported.
- `openArticle()` records `article-switch-start:<id>` before lookup and `article-switch-ready:<id>` after render.

- [ ] **Step 1: Write failing metric test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {measureLatency} from '../latency-metrics.js';

test('measureLatency returns deterministic milliseconds',()=>{
  assert.deepEqual(measureLatency('article-switch',10,34.5),{label:'article-switch',duration_ms:24.5});
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/latency-metrics.test.js`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement the metric helper and app marks**

```js
export function measureLatency(label,start,end=performance.now()){
  return {label,duration_ms:Math.max(0,end-start)};
}
```

In `openArticle()` capture `const switchStarted=performance.now();` before store lookup and call `measureLatency('article-switch',switchStarted)` after the DOM is updated. Keep the helper passive; it must never delay rendering.

Update the standard to state: resident repeat switches must execute without selection fetch and target <=50 ms on real devices.

- [ ] **Step 4: Verify all reader tests**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/latency-metrics.js kaoyan-reader-v1/tests/latency-metrics.test.js kaoyan-reader-v1/app.js docs/standards/PLAYBACK_LATENCY_STANDARD.md
git commit -m "test: instrument resident article switch latency"
```

---

### Task 5: CI and browser smoke verification for RAM article switching

**Files:**
- Modify only if needed: `.github/workflows/reader-tests.yml`
- Reuse: `kaoyan-reader-v1/tests/browser-smoke.py`

**Interfaces:**
- Existing `npm test` must discover the new `*.test.js` files automatically.

- [ ] **Step 1: Run the entire reader suite locally/in CI**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: every Node test passes.

- [ ] **Step 2: Verify the workflow includes `npm test` and does not exclude new tests**

Inspect `.github/workflows/reader-tests.yml`. If it already runs `npm test`, make no workflow edit.

- [ ] **Step 3: Push and inspect Reader tests workflow**

Expected: `reader-tests.yml` completes successfully, including bilingual rebuild gates.

- [ ] **Step 4: Real-device smoke checklist**

On the deployed site:

```text
1. Open one article and wait for background preload.
2. Switch A -> B -> A several times.
3. Confirm repeat A/B switches do not show the old multi-second loading behavior.
4. Confirm translations/highlights remain correct.
5. Confirm previous/next article navigation still works.
6. Record article-switch metric values; resident switches should normally be <=50 ms.
```

- [ ] **Step 5: Commit any workflow-only adjustment if one was required**

```bash
git add .github/workflows/reader-tests.yml
git commit -m "ci: cover RAM article switching"
```

If no workflow change was required, do not create an empty commit.
