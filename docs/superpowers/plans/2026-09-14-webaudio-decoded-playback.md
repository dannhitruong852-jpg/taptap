# Web Audio Decoded Playback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make current-article sentence playback start from decoded `AudioBuffer` objects in RAM, with persistent CacheStorage bytes and HTMLAudio fallback preserved.

**Architecture:** Extend the existing persistent audio cache with an ArrayBuffer byte resolver, add a `DecodedAudioStore` that deduplicates decode work and retains buffers for the current working set, then add a Web Audio player implementing the existing queue/progress/pause/resume/speed contract. `app.js` prepares the active article first and adjacent articles second, while falling back to the existing HTMLAudio player when Web Audio cannot play an asset.

**Tech Stack:** Browser ES modules, CacheStorage, Web Audio API, Fetch API, Node 22 `node:test`.

**Spec:** `docs/superpowers/specs/2026-09-14-reader-ram-webaudio-zero-latency-design.md`

## Global Constraints

- Decoded current-sentence start target: <= 50 ms from click handler to Web Audio source start after preparation.
- Persistent audio bytes remain application-level permanent: no size cap, no LRU, no automatic deletion.
- Current article audio outranks adjacent/background preparation.
- Existing 0.85 / 1.0 / 1.15 speed controls, pause/resume, progress highlighting, legacy multi-segment queues, and automatic next sentence behavior must remain compatible.
- HTMLAudio/Blob remains a functional fallback.
- Existing production audio is not regenerated.
- Version identity must include final path plus generation fingerprint or exact file hash.

---

### Task 1: Propagate manifest version identity into sentence queue items

**Files:**
- Modify: `kaoyan-reader-v1/playback.js`
- Modify: `kaoyan-reader-v1/tests/playback.test.js`

**Interfaces:**
- `buildSentenceQueue(sentence, manifest)` continues returning queue items.
- Every returned queue item also carries `generation_fingerprint` from its own entry or the root manifest when the entry lacks one.

- [ ] **Step 1: Write the failing fingerprint propagation test**

```js
test('buildSentenceQueue propagates root manifest generation fingerprint to version audio identity',()=>{
  const sentence={id:'s01',segments:[{id:'s01-a'}]};
  const manifest={generation_fingerprint:'root-v9',sentences:{s01:{path:'./audio/s01.opus'}},segments:{}};
  const [item]=buildSentenceQueue(sentence,manifest);
  assert.equal(item.generation_fingerprint,'root-v9');
});
```

Add a second test for legacy segment queues:

```js
test('legacy segment queue inherits root generation fingerprint',()=>{
  const sentence={id:'s02',segments:[{id:'s02-a'}]};
  const manifest={generation_fingerprint:'root-v10',segments:{'s02-a':{path:'./audio/s02-a.opus'}}};
  const [item]=buildSentenceQueue(sentence,manifest);
  assert.equal(item.generation_fingerprint,'root-v10');
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js`

Expected: FAIL because root fingerprint is not copied today.

- [ ] **Step 3: Implement minimal queue propagation**

For seamless sentence assets:

```js
if(seamless?.path) return [{...seamless,id:sentence.id,generation_fingerprint:seamless.generation_fingerprint||manifest?.generation_fingerprint}];
```

For legacy segments:

```js
return sentence.segments.map(segment=>({
  ...segment,
  ...manifest.segments[segment.id],
  generation_fingerprint:manifest.segments[segment.id]?.generation_fingerprint||manifest?.generation_fingerprint
}));
```

- [ ] **Step 4: Run and verify GREEN**

Run: `cd kaoyan-reader-v1 && node --test tests/playback.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/playback.js kaoyan-reader-v1/tests/playback.test.js
git commit -m "fix: propagate audio generation fingerprint"
```

---

### Task 2: Expose compressed audio bytes from the persistent cache

**Files:**
- Modify: `kaoyan-reader-v1/audio-cache.js`
- Modify: `kaoyan-reader-v1/tests/audio-cache.test.js`

**Interfaces:**
- Existing `resolve(item)` remains for Blob/HTMLAudio fallback.
- Add `getArrayBuffer(item)` returning `{buffer,key,local}` where `buffer` is an `ArrayBuffer` loaded from CacheStorage/network.
- `getArrayBuffer` uses the same version-aware key and in-flight network dedup rules as `resolve`.

- [ ] **Step 1: Write failing byte-resolver tests**

```js
test('getArrayBuffer stores cold bytes and reuses persistent bytes after memory reset',async()=>{
  const storage=fakeCacheStorage(); let fetchCalls=0;
  const cache=audioCacheModule.createAudioCache({
    cacheStorage:storage,
    fetcher:async()=>{fetchCalls+=1;return new FakeResponse('bytes-v1');},
    createObjectURL:()=> 'blob:unused',
    revokeObjectURL:()=>{}
  });
  const item={path:'./audio/x.opus',generation_fingerprint:'fp1'};
  const first=await cache.getArrayBuffer(item);
  cache.clearMemory();
  const second=await cache.getArrayBuffer(item);
  assert.equal(fetchCalls,1);
  assert.equal(new TextDecoder().decode(first.buffer),'bytes-v1');
  assert.equal(new TextDecoder().decode(second.buffer),'bytes-v1');
  assert.equal(first.key,second.key);
});
```

Add a test asserting fingerprint changes trigger distinct byte identities.

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js`

Expected: FAIL because `getArrayBuffer` does not exist.

- [ ] **Step 3: Implement one shared persistent-response path**

Refactor the internal persistent fetch into:

```js
async function responseFor(item,key){
  const store=await persistent();
  if(!store) return null;
  let response=await store.match(key).catch(()=>null);
  if(!response){
    if(!fetcher) return null;
    const network=await fetcher(item.path);
    if(!network?.ok) throw new Error('audio-fetch-failed');
    response=network;
    try{await store.put(key,network.clone());}catch{}
  }
  return response;
}
```

Then:

```js
async function getArrayBuffer(item){
  if(!item?.path) throw new Error('audio-path-required');
  const key=audioCacheKey(item);
  const response=await responseFor(item,key);
  if(!response) throw new Error('audio-bytes-unavailable');
  const blob=await response.blob();
  return {buffer:await blob.arrayBuffer(),key,local:true};
}
```

`resolvePersistent()` should call `responseFor()` and preserve its current remote fallback behavior when persistent storage is unavailable.

- [ ] **Step 4: Run focused and full cache tests**

Run: `cd kaoyan-reader-v1 && node --test tests/audio-cache.test.js tests/audio-cache-player-lifecycle.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/audio-cache.js kaoyan-reader-v1/tests/audio-cache.test.js
git commit -m "feat: expose persistent audio bytes for Web Audio"
```

---

### Task 3: Add DecodedAudioStore

**Files:**
- Create: `kaoyan-reader-v1/decoded-audio-store.js`
- Create: `kaoyan-reader-v1/tests/decoded-audio-store.test.js`

**Interfaces:**
- Consumes: `audioCache.getArrayBuffer(item)` and one shared `AudioContext`.
- Produces: `createDecodedAudioStore({audioContext,audioCache,maxArticles})` returning `{get,preload,has,dropArticle,clearDecoded,getState}`.
- `get(item,{articleId})` resolves `{buffer,key,articleId}`.

- [ ] **Step 1: Write the failing decode-dedup tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {createDecodedAudioStore} from '../decoded-audio-store.js';

test('concurrent decoded requests share one byte load and one decode',async()=>{
  let byteCalls=0,decodeCalls=0;
  const audioCache={getArrayBuffer:async item=>{byteCalls+=1;return {buffer:new Uint8Array([1,2,3]).buffer,key:`k:${item.generation_fingerprint}`};}};
  const audioContext={decodeAudioData:async()=>{decodeCalls+=1;return {duration:2.5};}};
  const store=createDecodedAudioStore({audioContext,audioCache});
  const item={path:'./x.opus',generation_fingerprint:'v1'};
  const [a,b]=await Promise.all([store.get(item,{articleId:'a'}),store.get(item,{articleId:'a'})]);
  assert.strictEqual(a.buffer,b.buffer);
  assert.equal(byteCalls,1);
  assert.equal(decodeCalls,1);
});
```

Add tests for:
- version change => a second decode identity;
- `dropArticle('a')` removes only decoded RAM entries tagged to article `a`;
- no persistent-cache deletion method is called.

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/decoded-audio-store.test.js`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement the decoded store**

Use two maps:

```js
const decoded=new Map();
const inflight=new Map();
```

`get()` should call `audioCache.getArrayBuffer(item)`, key the decoded map by the returned versioned key, call `audioContext.decodeAudioData(buffer.slice(0))`, and retain `{buffer,key,articleId}`.

`dropArticle(articleId)` deletes only matching decoded map entries. `clearDecoded()` clears RAM only.

- [ ] **Step 4: Run focused tests**

Run: `cd kaoyan-reader-v1 && node --test tests/decoded-audio-store.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/decoded-audio-store.js kaoyan-reader-v1/tests/decoded-audio-store.test.js
git commit -m "feat: add decoded audio RAM store"
```

---

### Task 4: Implement the Web Audio sentence player contract

**Files:**
- Create: `kaoyan-reader-v1/web-audio-player.js`
- Create: `kaoyan-reader-v1/tests/web-audio-player.test.js`

**Interfaces:**
- `createWebAudioPlayer({audioContext,resolveDecoded,onSegmentStart,onTimeUpdate,onSentenceEnd,onError,schedule,cancelSchedule})`
- Public methods mirror the current player where practical: `{playSentence,pause,resume,stop,setPlaybackRate,getState}`.
- `resolveDecoded(segment)` resolves `{buffer,key}`.

- [ ] **Step 1: Write failing start/queue tests with a fake AudioContext**

Provide fakes:

```js
class FakeSource{
  constructor(ctx){this.ctx=ctx;this.playbackRate={value:1};}
  connect(){}
  start(when=0,offset=0){this.started={when,offset};this.ctx.lastSource=this;}
  stop(){this.stopped=true;}
  finish(){this.onended?.();}
}
class FakeContext{
  constructor(){this.currentTime=10;this.destination={};this.state='running';}
  createBufferSource(){return new FakeSource(this);}
  resume(){this.state='running';return Promise.resolve();}
}
```

Test:

```js
test('decoded buffer starts directly through AudioBufferSourceNode and advances queue',async()=>{
  const ctx=new FakeContext(); const ended=[];
  const player=createWebAudioPlayer({
    audioContext:ctx,
    resolveDecoded:async segment=>({buffer:{duration:Number(segment.duration_seconds||1)}}),
    schedule:()=>0,cancelSchedule:()=>{},
    onSentenceEnd:()=>ended.push(true)
  });
  player.playSentence([{id:'a',duration_seconds:1},{id:'b',duration_seconds:1}],1);
  await Promise.resolve();await Promise.resolve();
  assert.equal(ctx.lastSource.started.offset,0);
  ctx.lastSource.finish();
  await Promise.resolve();await Promise.resolve();
  ctx.lastSource.finish();
  assert.equal(ended.length,1);
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/web-audio-player.test.js`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement minimal queue playback**

Keep state:

```js
let source=null,queue=[],index=-1,speed=1,generation=0;
let logicalOffset=0,startedAtContextTime=0,activeDuration=0,paused=false;
```

For each segment:

1. `await resolveDecoded(segment)`;
2. create `AudioBufferSourceNode`;
3. set `.buffer` and `.playbackRate.value=speed`;
4. `source.start(0,logicalOffset)`;
5. compute progress from `audioContext.currentTime`;
6. on ended, advance to the next queue item.

- [ ] **Step 4: Add failing pause/resume/speed/progress tests**

Required assertions:

```js
player.pause();
assert.ok(player.getState().paused);
await player.resume();
assert.ok(ctx.lastSource.started.offset>0);
player.setPlaybackRate(1.15);
assert.equal(ctx.lastSource.playbackRate.value,1.15);
```

Inject `schedule(fn)` and `cancelSchedule(id)` so progress polling is deterministic in Node. Assert that `onTimeUpdate` reports logical media time, not raw context time.

- [ ] **Step 5: Implement pause/resume/speed/progress correctly**

Logical position formula while playing:

```js
const elapsedContext=audioContext.currentTime-startedAtContextTime;
const mediaTime=Math.min(activeDuration,logicalOffset+elapsedContext*speed);
```

On pause, store `logicalOffset=mediaTime` and stop the current source while suppressing its `onended` advancement. On resume, rebuild a source from that offset. On speed change, first snapshot the current logical position, rebuild the source at the new rate, and continue.

- [ ] **Step 6: Run focused tests**

Run: `cd kaoyan-reader-v1 && node --test tests/web-audio-player.test.js`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add kaoyan-reader-v1/web-audio-player.js kaoyan-reader-v1/tests/web-audio-player.test.js
git commit -m "feat: add Web Audio sentence player"
```

---

### Task 5: Add HTMLAudio fallback adapter

**Files:**
- Create: `kaoyan-reader-v1/hybrid-audio-player.js`
- Create: `kaoyan-reader-v1/tests/hybrid-audio-player.test.js`
- Reuse: `kaoyan-reader-v1/audio-player.js`
- Reuse: `kaoyan-reader-v1/web-audio-player.js`

**Interfaces:**
- `createHybridAudioPlayer({webPlayer,fallbackPlayer,canUseWebAudio})` exposes the shared player methods.
- It prefers Web Audio per sentence and falls back to HTMLAudio only when Web Audio preparation/start rejects.

- [ ] **Step 1: Write failing fallback test**

```js
test('hybrid player falls back to HTMLAudio when Web Audio sentence start rejects',async()=>{
  const events=[];
  const web={playSentence(){events.push('web');return Promise.reject(new Error('decode'));},stop(){},pause(){},resume(){},setPlaybackRate(){},getState(){return {}}};
  const fallback={playSentence(){events.push('fallback');},stop(){},pause(){},resume(){},setPlaybackRate(){},getState(){return {playing:true}}};
  const player=createHybridAudioPlayer({webPlayer:web,fallbackPlayer:fallback,canUseWebAudio:()=>true});
  await player.playSentence([{id:'s01'}],1);
  assert.deepEqual(events,['web','fallback']);
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/hybrid-audio-player.test.js`

Expected: FAIL because module does not exist.

- [ ] **Step 3: Implement the adapter**

Track the currently active engine. `playSentence()` calls `webPlayer.playSentence()` and catches rejection; on catch call `fallbackPlayer.playSentence()` and mark fallback active. Forward pause/resume/stop/speed/getState to the active engine.

- [ ] **Step 4: Run focused tests**

Run: `cd kaoyan-reader-v1 && node --test tests/hybrid-audio-player.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/hybrid-audio-player.js kaoyan-reader-v1/tests/hybrid-audio-player.test.js
git commit -m "feat: add Web Audio playback fallback"
```

---

### Task 6: Integrate decoded preparation into the reader

**Files:**
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/tests/playback-latency-integration.test.js`

**Interfaces:**
- `audioCache` remains durable byte storage.
- Create one `AudioContext` lazily after the first user interaction or when preparation is permitted by the browser.
- Create `DecodedAudioStore` with that context and `audioCache`.
- Create `webAudioPlayer` + existing `audioPlayer` fallback + `hybridAudioPlayer`.
- `warmRange` becomes decode-aware preparation for the active article.

- [ ] **Step 1: Write failing integration contracts**

Add assertions:

```js
assert.match(app,/createDecodedAudioStore/);
assert.match(app,/createWebAudioPlayer/);
assert.match(app,/createHybridAudioPlayer/);
assert.match(app,/decodedAudioStore\.preload/);
assert.match(app,/articleId:/);
```

Also assert the old fallback player still exists:

```js
assert.match(app,/createAudioPlayer/);
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/playback-latency-integration.test.js`

Expected: FAIL because Web Audio modules are not wired yet.

- [ ] **Step 3: Wire a lazy shared AudioContext**

Use:

```js
let audioContext=null,decodedAudioStore=null,webAudioPlayer=null;
function ensureWebAudio(){
  const Ctor=window.AudioContext||window.webkitAudioContext;
  if(!Ctor) return null;
  if(!audioContext){
    audioContext=new Ctor({latencyHint:'interactive'});
    decodedAudioStore=createDecodedAudioStore({audioContext,audioCache});
    webAudioPlayer=createWebAudioPlayer({audioContext,resolveDecoded:item=>decodedAudioStore.get(item,{articleId:currentEntry?.id||'unknown'}),...callbacks});
  }
  return webAudioPlayer;
}
```

Create the hybrid wrapper around a lazy Web Audio proxy and the existing HTMLAudio player.

- [ ] **Step 4: Make active-article preparation decode-aware**

Replace `audioCache.warm(warm)` in current-article preparation with:

```js
const web=ensureWebAudio();
if(web&&decodedAudioStore){
  void decodedAudioStore.preload(warm,{articleId:currentEntry?.id||'unknown'}).catch(()=>audioCache.warm(warm));
}else{
  void audioCache.warm(warm);
}
```

The first four sentences remain highest priority. Remainder follows. Adjacent article preparation runs only after current article remainder has been scheduled/completed.

- [ ] **Step 5: Route playback through the hybrid player**

Every call site currently using the old player (`playSentence`, `pause`, `resume`, `stop`, `setPlaybackRate`, `getState`) must use the hybrid wrapper. Keep the old player instance alive only as fallback.

- [ ] **Step 6: Run integration and full Node suite**

Run:

```bash
cd kaoyan-reader-v1
node --test tests/playback-latency-integration.test.js
npm test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/playback-latency-integration.test.js
git commit -m "feat: use decoded Web Audio for prepared sentences"
```

---

### Task 7: Adjacent-article audio preparation and stale-work suppression

**Files:**
- Modify: `kaoyan-reader-v1/decoded-audio-store.js`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/tests/decoded-audio-store.test.js`
- Modify: `kaoyan-reader-v1/tests/playback-latency-integration.test.js`

**Interfaces:**
- Add `preload(items,{articleId,generation})` to `DecodedAudioStore`.
- Add `setGeneration(value)` or equivalent stale-completion guard.
- Old article decode completion may populate neutral cache only if desired, but must not change active reader/player state.

- [ ] **Step 1: Write failing stale-generation test**

```js
test('stale decode completion cannot report itself as active generation',async()=>{
  let release;
  const gate=new Promise(r=>{release=r;});
  const audioCache={getArrayBuffer:async()=>({buffer:new Uint8Array([1]).buffer,key:'k'})};
  const audioContext={decodeAudioData:async()=>{await gate;return {duration:1};}};
  const store=createDecodedAudioStore({audioContext,audioCache});
  const pending=store.get({path:'a',generation_fingerprint:'v1'},{articleId:'old',generation:1});
  store.setGeneration(2);
  release();
  const result=await pending;
  assert.equal(result.stale,true);
});
```

- [ ] **Step 2: Run and verify RED**

Run: `cd kaoyan-reader-v1 && node --test tests/decoded-audio-store.test.js`

Expected: FAIL because generation control does not exist.

- [ ] **Step 3: Implement generation tagging**

The store keeps `activeGeneration`. A result from `get(...,{generation})` returns `{...entry,stale:generation!==undefined&&generation!==activeGeneration}`. `preload()` ignores stale completion for readiness callbacks.

- [ ] **Step 4: Add adjacent preparation in app.js**

After current article preload completes, compute:

```js
const neighbors=[adjacentArticle(catalog,currentEntry.id,-1),adjacentArticle(catalog,currentEntry.id,1)].filter(Boolean);
```

For resident neighbor bundles, build their sentence queues and call low-priority decode preload tagged with the current selection generation. Never block current article rendering or playback.

- [ ] **Step 5: Run all reader tests**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add kaoyan-reader-v1/decoded-audio-store.js kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/decoded-audio-store.test.js kaoyan-reader-v1/tests/playback-latency-integration.test.js
git commit -m "feat: prepare adjacent article audio safely"
```

---

### Task 8: Add click-to-source-start instrumentation and standards

**Files:**
- Modify: `kaoyan-reader-v1/latency-metrics.js`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/tests/latency-metrics.test.js`
- Modify: `docs/standards/PLAYBACK_LATENCY_STANDARD.md`

**Interfaces:**
- Add `markLatencyStart(name,now=performance.now())` and `finishLatency(name,start,now=performance.now())` or retain `measureLatency` with explicit start/end.
- `speak()` captures tap/play request time.
- `onSegmentStart` records Web Audio source-start latency.

- [ ] **Step 1: Add failing deterministic metric tests**

```js
test('audio-start metric reports exact elapsed milliseconds',()=>{
  assert.deepEqual(measureLatency('audio-start',100,137.25),{label:'audio-start',duration_ms:37.25});
});
```

- [ ] **Step 2: Run and verify RED only if helper behavior changes**

If `measureLatency` already satisfies this contract from the RAM article plan, keep the test as a regression and proceed without artificial production changes.

- [ ] **Step 3: Wire audio start measurement**

Before `hybridPlayer.playSentence(...)` capture `state.playRequestedAt=performance.now()`. In the first `onSegmentStart` callback for that request, call `measureLatency('audio-start',state.playRequestedAt)` and clear the marker. Do not wait for or display the metric in the playback path.

Update the standard with:

```text
Decoded Web Audio source start target: <=50 ms from the user playback request once the sentence buffer is resident.
```

- [ ] **Step 4: Run full tests**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/latency-metrics.js kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/latency-metrics.test.js docs/standards/PLAYBACK_LATENCY_STANDARD.md
git commit -m "test: instrument Web Audio start latency"
```

---

### Task 9: Verification, publish, and real-device smoke

**Files:**
- Reuse: `.github/workflows/reader-tests.yml`
- Reuse: `.github/workflows/publish-kaoyan-batch.yml`
- Modify only if needed: `publish-batch.trigger`

**Interfaces:**
- Existing Reader tests and bilingual publication gates remain mandatory.

- [ ] **Step 1: Run full local/CI reader suite**

Run: `cd kaoyan-reader-v1 && npm test`

Expected: all Node tests PASS.

- [ ] **Step 2: Run existing Python/bilingual gates**

Run the same Python test/build commands used by `.github/workflows/reader-tests.yml`.

Expected: all PASS; 2003–2006 bilingual coverage remains complete.

- [ ] **Step 3: Push and verify Reader tests workflow**

Inspect the run for the final feature commit. Every step must succeed.

- [ ] **Step 4: Trigger the existing publish workflow using validated source run `34804393175`**

Update only the trigger marker content while preserving the same validated source run ID. Do not regenerate audio.

- [ ] **Step 5: Verify publish and Pages deployment**

Required success:

```text
Publish kaoyan C-mode batch: success
- Download merged candidates
- Validate merged candidates
- Install validated candidates
- Rebuild catalog
- Validate bilingual coverage
- Validate static reader contract
- Commit/publish

Pages build and deployment: build success, report success, deploy success
```

- [ ] **Step 6: Real-device smoke checklist**

On iPhone/Android normal browsing mode:

```text
1. Cold-open one article and allow preparation.
2. Tap first four sentences; note audio-start metric.
3. Wait for current article decode completion, then tap arbitrary late sentences.
4. Confirm prepared sentence taps feel immediate and target <=50 ms source-start metric.
5. Pause/resume mid-sentence.
6. Switch speeds 0.85 -> 1.0 -> 1.15 while playing.
7. Let sentence auto-continue.
8. Switch to next article and back; resident article switching should normally be <=50 ms.
9. Close and reopen browser; compressed audio should reuse persistent CacheStorage, then re-decode into RAM without re-downloading.
10. Confirm incognito/private mode remains isolated and temporary according to browser behavior.
```

- [ ] **Step 7: Do not claim acoustic <=50 ms from CI alone**

Only claim the deterministic architecture/tests/deploy are complete. Real acoustic latency remains a device smoke result.
