# Persistent Audio Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make once-fetched sentence audio replay from persistent local bytes, removing repeat network waits across taps and page reloads while preserving existing sequencing and C-mode audio.

**Architecture:** Add `audio-cache.js` as the persistence and Blob-source boundary. It resolves each manifest item to a versioned cache key, deduplicates fetches, stores successful responses in Cache Storage, creates bounded Blob URLs for hot playback, and falls back to remote URLs when persistent storage is unavailable. `audio-player.js` remains the sequencer; `app.js` only schedules warm priorities and requests resolved sources.

**Tech Stack:** Vanilla ES modules, Cache Storage API, Fetch API, Blob/Object URLs, HTMLAudioElement, Node `node:test` with injected fake cache/fetch primitives.

**Spec:** `docs/superpowers/specs/2026-09-14-reader-bilingual-highlights-persistent-audio-cache-design.md`

## Global Constraints

- Do not regenerate or alter 2002-2006 audio.
- Do not remove natural silence or insert/remove semantic pauses.
- Do not merge articles into one monolithic audio file.
- Do not add runtime AI or year-specific player implementations.
- Warm cached playback target is <=100-150 ms under normal device conditions; automatic warm handoff transport gap target is <100 ms.
- Cache identity must change when the underlying asset version/fingerprint changes.
- Persistent cache failure must degrade to working remote playback.

---

### Task 1: Versioned cache identity and persistent byte lookup

**Files:**
- Create: `kaoyan-reader-v1/audio-cache.js`
- Create: `kaoyan-reader-v1/tests/audio-cache.test.js`

**Interfaces:**
- Produces: `createAudioCache(options) -> cache`
- `cache.resolve(item) -> Promise<{src:string, local:boolean, key:string}>`
- `cache.warm(items) -> Promise<void>`
- `cache.clearMemory() -> void`
- `cache.pruneOldGenerations() -> Promise<void>`
- `item` may contain `path`, `mp3_path`, `generation_fingerprint`, `files`.

- [ ] **Step 1: Write failing identity and repeat-hit tests**

```js
const item={path:'./audio/2003/v4/c-text1/v4-s01.opus',generation_fingerprint:'abc'};
const first=await cache.resolve(item);
const second=await cache.resolve(item);
assert.equal(fetchCalls,1);
assert.equal(first.key,second.key);
assert.equal(second.local,true);
```

Also assert changing `generation_fingerprint` changes `key`.

- [ ] **Step 2: Run focused test and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: FAIL because module/API does not exist.

- [ ] **Step 3: Implement versioned keys and Cache Storage read-through**

Use a cache namespace such as `kaoyan-audio-v1`. Build the identity from the final media path and best available version value:

```js
function assetVersion(item){
  return item.generation_fingerprint || item.files?.[item.path?.split('/').at(-1)] || 'unversioned';
}
```

Persistent flow:

```js
const response=await persistent.match(requestKey);
if(!response){
  const network=await fetcher(remotePath);
  if(!network.ok) throw new Error('audio-fetch-failed');
  await persistent.put(requestKey,network.clone());
  response=network;
}
```

Cache the bytes under a synthetic same-origin request key containing encoded remote path and version so regenerated assets do not collide.

- [ ] **Step 4: Verify focused tests GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: PASS for first-fetch, repeat-hit, and version-change cases.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/tests/audio-cache.test.js
git commit -m "feat: add persistent versioned audio byte cache"
```

---

### Task 2: In-flight deduplication and bounded Blob URL memory layer

**Files:**
- Modify: `kaoyan-reader-v1/audio-cache.js`
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`

**Interfaces:**
- Same public API as Task 1.
- Internal maps: `inflight: Map<key, Promise<...>>`, `blobLru: Map<key,{url,lastUsed}>`.

- [ ] **Step 1: Add failing concurrent/dedup and eviction tests**

Two simultaneous `resolve(item)` calls must produce one fetch. With `maxBlobEntries:2`, resolving three distinct items must revoke the oldest Blob URL while keeping newer entries usable.

- [ ] **Step 2: Run test and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: FAIL on duplicate fetch and/or missing revocation.

- [ ] **Step 3: Implement in-flight map and Blob LRU**

`resolve()` first checks memory, then `inflight`, then persistent/network. Convert successful response bytes with `await response.blob()` and `URL.createObjectURL(blob)`. On eviction call injected `revokeObjectURL(url)`.

Do not revoke a URL returned as active; expose `cache.pin(key)` / `cache.unpin(key)` if necessary so the sequencer can mark the currently playing source.

- [ ] **Step 4: Verify tests GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/tests/audio-cache.test.js
git commit -m "feat: deduplicate audio fetches and bound blob memory"
```

---

### Task 3: Fallback behavior when Cache Storage is unavailable

**Files:**
- Modify: `kaoyan-reader-v1/audio-cache.js`
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`

**Interfaces:**
- `createAudioCache({cacheStorage:null,...})` must still resolve to remote URLs.
- Failed persistent `open/match/put` operations must not break playback.

- [ ] **Step 1: Add failing degraded-mode tests**

Assert that when `cacheStorage.open()` rejects, `resolve(item)` returns `{src:item.path,local:false}` and does not throw if the remote URL can be used directly.

- [ ] **Step 2: Verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: FAIL until fallback exists.

- [ ] **Step 3: Implement graceful degradation**

Wrap persistence setup/operations. If persistence cannot be used, return remote path and retain only session-level in-memory resolved entries when possible. Network fetch errors still propagate to the existing player error UI.

- [ ] **Step 4: Verify GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/tests/audio-cache.test.js
git commit -m "fix: degrade audio cache safely when persistence is unavailable"
```

---

### Task 4: Integrate asynchronous source resolution into the sequencer

**Files:**
- Modify: `kaoyan-reader-v1/audio-player.js`
- Modify: `kaoyan-reader-v1/tests/playback.test.js`
- Modify: `kaoyan-reader-v1/tests/stale-playback.test.js`

**Interfaces:**
- Extend `createAudioPlayer` with injected `resolveAudio(item) -> Promise<{src,key,local}>`.
- `onSegmentStart` must fire when the resolved audio is about to play, not at initial click before media resolution.
- Existing `playSentence(queue, rate)`, pause/resume/stop/speed APIs remain available.

- [ ] **Step 1: Write failing async resolver tests**

Assert that `createAudio` receives the resolved Blob URL rather than the manifest path, and that a resolver completing after `stop()` cannot start stale playback or report stale errors.

- [ ] **Step 2: Verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js tests/stale-playback.test.js`
Expected: FAIL because the current sequencer creates Audio synchronously from `segment.path`.

- [ ] **Step 3: Implement minimal async resolution in `playAt`**

Make `playAt` async. Capture `generation`, await `resolveAudio(segment)`, re-check generation, then create/reuse Audio from resolved `src`. Preserve timing callbacks and speed. `stop()` must invalidate pending resolutions.

- [ ] **Step 4: Verify focused tests GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js tests/stale-playback.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-player.js kaoyan-reader-v1/tests/playback.test.js kaoyan-reader-v1/tests/stale-playback.test.js
git commit -m "feat: resolve local audio sources before playback"
```

---

### Task 5: Integrate article warming priorities

**Files:**
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/tests/reader-interaction.test.js`

**Interfaces:**
- Instantiate one `audioCache` for the page.
- `audioPlayer` receives `resolveAudio:item=>audioCache.resolve(item)`.
- `warmSentenceRange(start,end)` calls `audioCache.warm(queue items)`.

- [ ] **Step 1: Add failing reader integration tests**

Verify that article open schedules current + next 3 sentences, viewport warming schedules visible/near-visible queues, and sentence end warms upcoming sentences without adding any timeout between playback calls.

- [ ] **Step 2: Verify RED**

Run: `cd kaoyan-reader-v1 && npm test -- --test-name-pattern='warm|cache|playback'`
Expected: FAIL until app uses the cache module.

- [ ] **Step 3: Replace direct `<audio preload>` warming with cache warming**

Remove the old `Audio()` preloader mechanism. On article open call high-priority warm for current/next 3. Use `requestIdleCallback` when available, otherwise a zero-delay scheduling fallback, to continue warming the rest of the article with bounded concurrency handled by `audio-cache.js`.

Viewport movement only changes priority by calling `warm()` for nearby queues; duplicate keys must be deduplicated by the cache layer.

- [ ] **Step 4: Verify focused reader tests GREEN**

Run: `cd kaoyan-reader-v1 && npm test -- --test-name-pattern='warm|cache|playback'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/reader-interaction.test.js
git commit -m "feat: warm persistent audio cache around reading position"
```

---

### Task 6: Cache generation pruning and manifest fingerprint contract

**Files:**
- Modify: `kaoyan-reader-v1/audio-cache.js`
- Modify: `kaoyan-reader-v1/playback.js` if queue items need explicit fingerprint propagation
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`
- Modify: `kaoyan-reader-v1/tests/playback.test.js`

**Interfaces:**
- `buildSentenceQueue` must carry through `generation_fingerprint` and file hash metadata from manifest sentence/segment entries.
- `pruneOldGenerations()` may delete cache namespaces older than `kaoyan-audio-v1` but must never delete the current namespace.

- [ ] **Step 1: Write failing metadata propagation test**

For a V4 manifest sentence with `generation_fingerprint:'c9ca...'`, assert `buildSentenceQueue()` returns the same fingerprint on the playback item.

- [ ] **Step 2: Verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js tests/audio-cache.test.js`
Expected: FAIL if metadata is dropped.

- [ ] **Step 3: Preserve version metadata in queue items and add pruning**

Keep path/mp3 path/duration/cues/words plus fingerprint/files metadata. Pruning should enumerate `caches.keys()` and delete only names matching `kaoyan-audio-v*` except the active namespace.

- [ ] **Step 4: Verify GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js tests/audio-cache.test.js`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/playback.js kaoyan-reader-v1/tests/audio-cache.test.js kaoyan-reader-v1/tests/playback.test.js
git commit -m "feat: version persistent audio cache by manifest fingerprint"
```

---

### Task 7: Full reader verification and publication

**Files:**
- Modify: `.github/workflows/reader-tests.yml` only if the new test file is not already covered by `npm test`.
- No content/audio regeneration.

**Interfaces:**
- Verification commands are the acceptance gate.

- [ ] **Step 1: Run full Node reader suite**

Run: `cd kaoyan-reader-v1 && npm test`
Expected: zero failures.

- [ ] **Step 2: Run static/browser contract checks**

Run existing Python browser/static checks from `kaoyan-reader-v1/tests/` against the feature branch tree. Expected: 2002 and one V4 article remain playable; no missing manifest/audio references.

- [ ] **Step 3: Add a deployment smoke script/check for repeat playback**

Use a browser-capable test to play a sentence, wait for cache population, reload, replay the same sentence, and inspect Resource Timing/Network evidence so the second playback does not perform a fresh audio transfer. Also verify automatic next sentence begins without an explicit timer.

- [ ] **Step 4: Trigger the existing publish workflow only after all tests pass**

Republish the validated 2003-2006 candidate plus updated reader code. Do not re-render audio.

- [ ] **Step 5: Verify GitHub Pages deployment and mobile behavior**

Check Pages build/deploy success, then test 2002 and 2003+ on mobile: cold first play, same-sentence replay, page reload replay, arbitrary visible sentence tap, automatic handoff, pause/resume, and 0.85/1.0/1.15 speed.

- [ ] **Step 6: Commit any CI-only adjustments**

```bash
git add .github/workflows/reader-tests.yml kaoyan-reader-v1/tests
git commit -m "test: gate reader on persistent audio cache behavior"
```
