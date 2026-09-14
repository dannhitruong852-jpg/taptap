# RAM-First Reader + Web Audio Low-Latency Design

Status: proposed implementation design
Date: 2026-09-14
Branch: `c-v4-article-preview-actual`
Scope: `kaoyan-reader-v1`

## 1. Goal

Make two user actions feel local rather than network-bound:

1. switching between exam articles;
2. starting any sentence audio in the current article.

The design optimizes for speed first. Storage, bandwidth, and implementation cost are secondary constraints. Existing content, translations, bilingual vocabulary highlighting, actor casting, C-mode direction, speed controls, and persistent audio retention must remain intact.

## 2. Chosen architecture

The approved architecture is a four-tier hot path:

1. decoded Web Audio `AudioBuffer` in RAM;
2. compressed audio bytes in RAM / resolved local bytes;
3. persistent browser `CacheStorage`;
4. network fallback.

Article text/data uses a separate RAM-first path:

1. article bundle in an in-memory map;
2. browser/network fetch only when the bundle is not yet resident.

The browser must never wait on a network request after a memory hit.

## 3. Alternatives considered

### A. Network-only CDN/HTTP playback

Keep every click network-bound and optimize delivery with CDN/HTTP2/HTTP3. This avoids local state but cannot remove network RTT, first-byte delay, buffering, or decode delay. Rejected because it is slower and less deterministic than RAM.

### B. Persistent CacheStorage + HTMLAudio only

This is the current architecture. It is robust and already much faster than cold network playback, but every play still resolves bytes, creates a Blob/Object URL, creates an `HTMLAudioElement`, and lets the media stack initialize. It also leaves article switching dependent on per-selection fetches. Retained as a fallback layer, not the fastest layer.

### C. RAM-first article bundles + Web Audio decoded buffers

Preload article data into RAM and decode current/nearby article audio before the click. This minimizes the click-time work to memory lookup, source-node creation, and start. Chosen.

### D. Audio sprite / one monolithic audio file per article

A single article file with sentence offsets could reduce request and decode count further, but it would require a new asset production format and broad regeneration/migration. It is not necessary to achieve the current latency goal and would increase risk to established C-mode assets. Rejected for this iteration.

## 4. Article switching architecture

### 4.1 Article bundle

Create a year-neutral `ArticleBundleStore` responsible for loading and retaining the data required to render an article:

- article content JSON;
- audio manifest JSON;
- year bilingual-highlight JSON or a year-level shared mapping reference;
- any additional static data required by the existing renderer.

The store exposes a stable API such as:

- `get(entry)` — return the resident bundle immediately when available, otherwise load it;
- `preload(entries)` — populate RAM without changing UI selection;
- `has(id)` — test memory residency;
- `cancelLowPriorityWork()` — stop obsolete background work when the user changes priority.

### 4.2 Startup strategy

Startup is progressive, not blocking:

1. load catalog and the selected/default article at highest priority;
2. render it as soon as its bundle is available;
3. immediately begin loading every remaining article bundle into RAM with bounded concurrency;
4. if the user selects an article that is still pending, promote that article to highest priority;
5. once an article bundle is resident, later switches to it must not fetch it again during the same page lifetime.

This preserves a fast first paint while converging quickly to instant switching across all loaded years.

### 4.3 Remove forced revalidation from the switch hot path

The current selection loader uses `cache:'no-cache'` for manifests and bilingual mappings. In the new RAM-first path, repeated article switches must not invoke these requests after the bundle is resident. Network freshness belongs to page load/version deployment, not every selection event.

### 4.4 Switching performance target

For a resident article bundle:

- no network request;
- no CacheStorage lookup;
- only memory lookup + state swap + DOM rendering;
- target user-perceived switch latency: one frame to a few frames on modern phones, normally <= 50 ms excluding unusually heavy browser main-thread contention.

## 5. Audio architecture

### 5.1 Keep persistent byte cache

Existing `CacheStorage` remains the durable source of audio bytes:

- no capacity limit;
- no LRU eviction of persistent bytes;
- no automatic deletion by the app;
- persistent-storage request remains best-effort;
- network is used only when the versioned asset is not already cached.

The in-memory decoded layer is separate and may be discarded when the page closes.

### 5.2 Add decoded audio buffer store

Create a `DecodedAudioStore` around one shared `AudioContext`.

Responsibilities:

- resolve the versioned audio asset through the existing persistent cache;
- obtain compressed bytes as `ArrayBuffer` without forcing playback through `HTMLAudioElement`;
- decode them with `AudioContext.decodeAudioData`;
- retain decoded `AudioBuffer` objects in RAM;
- deduplicate concurrent decode requests;
- expose readiness and load/decode promises;
- allow clearing obsolete decoded buffers while never deleting persistent CacheStorage bytes.

### 5.3 Current-article and neighbor preparation

When an article becomes active:

1. current sentence and next three sentences get highest audio preparation priority;
2. the rest of the current article is fetched/decoded immediately after;
3. previous and next article audio are prepared in the background after the current article is ready;
4. changing articles cancels/deprioritizes obsolete network/decode work so it cannot steal bandwidth/CPU from the new current article;
5. decoded RAM is a working set, not permanent storage. Persistent CacheStorage remains permanent.

The implementation may retain the current article plus adjacent article buffers, but it must not decode all 20+ years at startup.

### 5.4 Web Audio player

Create a Web Audio playback implementation that preserves the existing player contract as closely as practical.

Required behavior:

- sentence start from a decoded `AudioBuffer` using `AudioBufferSourceNode.start()`;
- playback rates 0.85 / 1.0 / 1.15;
- pause and resume by tracking logical offset and rebuilding a source node at the correct offset;
- stop and stale-generation suppression;
- sentence completion callback;
- accurate progress callbacks derived from `AudioContext.currentTime`, logical start time, playback rate, and buffer duration;
- legacy multi-segment sentence queues remain supported;
- no artificial transport delay between segments or sentences;
- current C-mode timing/highlighting behavior remains functionally equivalent.

### 5.5 Fallback

If Web Audio is unavailable, suspended in an unsupported way, or decoding fails for an asset:

- fall back to the existing HTMLAudio/Blob path;
- do not make the article unreadable;
- do not delete the persistent cached asset;
- surface the existing audio error UI only if both primary and fallback playback fail.

## 6. Version identity and invalidation

The cache/decode identity must include:

- final resolved audio path;
- manifest generation fingerprint or exact file hash when available.

The root manifest generation fingerprint must be propagated into queue items when sentence entries do not carry their own fingerprint. A newly generated asset at the same path must not reuse stale persistent bytes or a stale decoded `AudioBuffer`.

## 7. Priority and cancellation

The current article always wins.

Priority order:

1. selected article bundle;
2. selected sentence audio;
3. next three sentence audio;
4. remainder of selected article audio;
5. adjacent article audio;
6. global article-bundle preload.

Background fetches must be cancellable with `AbortController` where fetch is still pending. Decode tasks that cannot be aborted must be ignored on completion if their generation is stale.

This prevents the current problem where old-article warming competes with a newly selected article.

## 8. Memory policy

### Persistent storage

No application-level eviction. Cached audio is retained indefinitely unless:

- the browser/OS removes site data;
- the user clears site data;
- the asset version changes and a new version is requested.

### RAM

RAM is intentionally aggressive but bounded to the active working set:

- all article text/data bundles may remain resident for the page lifetime;
- decoded audio remains focused on current + adjacent articles;
- leaving/reloading the page releases decoded buffers naturally;
- RAM policy must never remove persistent CacheStorage bytes.

## 9. Initial-entry cost

Cold first visit:

1. shell/catalog/default article load;
2. default article render;
3. all remaining article bundles preload in background;
4. default article audio resolves from network/cache and decodes;
5. nearby article audio prepares afterward.

The UI must not wait for global preload completion before becoming usable.

Warm revisit:

- article bundles reload quickly from static HTTP/browser cache and then stay in RAM;
- audio compressed bytes primarily come from persistent CacheStorage;
- only RAM reconstruction and Web Audio decoding are repeated;
- no repeated network download for already cached versioned audio.

## 10. Performance targets

These are product targets, not protocol guarantees:

- resident article switch: normally <= 50 ms user-perceived;
- decoded current-sentence start: target <= 50 ms from click handler to Web Audio source start;
- automatic handoff between ready buffers: no intentional gap; target transport contribution < 50 ms;
- cold first audio remains bounded by actual network + decode time;
- after current article preparation completes, arbitrary sentence taps in that article should no longer depend on network or decode work.

Real-device iPhone/Android smoke measurement remains mandatory because CI cannot prove acoustic output latency.

## 11. Compatibility requirements

The change must not regress:

- 2002 legacy rendering/playback compatibility;
- 2003–2006 V4 assets;
- future years;
- bilingual level >= 6 highlighting;
- semantic read-progress highlighting;
- actor IDs and C-mode direction;
- previous/next article controls;
- arbitrary sentence playback;
- pause/resume;
- 0.85 / 1.0 / 1.15 speed;
- automatic next-sentence playback;
- persistent audio retention policy.

No existing production audio should be regenerated merely to implement this transport architecture.

## 12. Testing strategy

Implementation is TDD-first.

Required automated coverage:

### Article bundle store

- first load fetches required bundle pieces;
- second load returns memory-resident data without fetch;
- startup global preload uses bounded concurrency;
- a user-selected pending article is promoted ahead of background work;
- stale selection results never replace the current article;
- switching between already resident articles performs no fetch.

### Decoded audio store

- persistent bytes are decoded once and reused in RAM;
- concurrent decode requests deduplicate;
- version/fingerprint changes produce a different decoded identity;
- stale decode completion cannot become the active article state;
- cache/network/decode failure falls back correctly.

### Web Audio player

- start, stop, pause, resume, speed change;
- progress math at each supported speed;
- queue continuation;
- generation cancellation;
- no stale callback after article switch;
- fallback to HTMLAudio on decode/Web Audio failure.

### Integration

- article switching from a memory hit causes no selection fetch;
- current article is prepared before adjacent article audio;
- old background audio fetches are cancelled/deprioritized when selection changes;
- persistent CacheStorage remains untouched by RAM cleanup;
- full existing reader test suite remains green.

## 13. Rollout

1. Introduce/test `ArticleBundleStore` without changing rendering semantics.
2. Route article selection through the RAM store and verify instant repeat switching.
3. Introduce/test `DecodedAudioStore` behind existing cache resolution.
4. Introduce Web Audio player behind a feature boundary with HTMLAudio fallback.
5. Migrate playback to Web Audio by default after parity tests pass.
6. Add instrumentation for article-switch and click-to-source-start timing.
7. Publish to the existing Pages branch and perform real-device smoke testing.

## 14. Acceptance criteria

The architecture is accepted when:

- the selected article can switch from an in-memory bundle without network access;
- all available article bundles are progressively loaded into RAM after startup;
- the current article can be fully decoded into Web Audio buffers without regenerating source audio;
- a decoded sentence starts without CacheStorage/network/decode work on the click path;
- adjacent article preparation does not interfere with the selected article;
- persistent audio retention remains indefinite at the application level;
- all automated tests and publish gates pass;
- production deployment succeeds;
- real-device testing shows materially faster article switching and sentence-start response than the current HTMLAudio-only path.
