# Automatic Full-Library Background Cache Design

Status: proposed implementation design
Date: 2026-09-14
Branch: `c-v4-article-preview-actual`
Scope: `kaoyan-reader-v1`

## 1. Goal

On the first visit, the reader should become usable immediately, then automatically cache the complete exam library in the background without requiring the user to visit each year/article manually.

After the first full cache completes, reopening the site should use local persistent data first so article switching and audio playback no longer depend on fresh network downloads for unchanged assets.

The feature must preserve the current RAM-first article switching, Web Audio playback, HTMLAudio fallback, permanent audio-retention policy, bilingual highlighting, and all existing content/audio assets.

## 2. User-visible behavior

Cold first visit:

1. Load and render the selected/default article at highest priority.
2. Start current-article audio preparation immediately.
3. In the background, enumerate every article in `catalog.json`.
4. Persist all text-side resources for every article.
5. Persist all audio assets for every article in the device-supported format.
6. Continue until the entire catalog is cached.
7. No manual year/article switching is required.

Warm revisit:

1. Load cached content locally first where available.
2. Scan the catalog again.
3. Skip unchanged cached assets.
4. Download only missing/new-version assets.
5. Continue unfinished work automatically if a previous session ended before completion.

The user can continue reading/listening while background caching runs.

## 3. Chosen architecture

The implementation adds a `FullLibraryCacheCoordinator` that orchestrates existing article and audio layers instead of replacing them.

Priority order:

1. current visible article rendering;
2. explicitly requested sentence audio;
3. current article audio preparation;
4. full-library persistent caching;
5. adjacent-article decoded audio warming.

The full-library job is persistent-byte oriented, not decoded-audio oriented.

### Why

Caching 20+ years of compressed audio to CacheStorage is appropriate. Decoding 20+ years into Web Audio `AudioBuffer` objects is not: it would consume excessive RAM and increase the chance mobile browsers kill the tab.

Therefore:

- all text + compressed audio may persist locally;
- all article text bundles may enter RAM during the page lifetime;
- decoded audio remains limited to the current working set.

## 4. Alternatives considered

### A. User-driven cache warming

Current behavior: opening an article warms that article and nearby audio. Rejected as the final behavior because it requires manual traversal and leaves untouched years cold.

### B. Decode the entire library into RAM

Would minimize click-time audio setup but is unsuitable for mobile memory and tab lifecycle. Rejected.

### C. Persist entire library, decode only active working set

Chosen. It provides durable local coverage while keeping RAM bounded.

## 5. Audio persistence changes

Current `audioCache.warm()` resolves audio into Blob/Object URLs, which is appropriate for the active working set but not for a 20+ year library.

Add a persistent-only API to `audio-cache.js`, for example:

- `ensurePersistent(item)` — guarantee that one versioned asset exists in CacheStorage, fetching it only if absent, without creating a Blob/Object URL;
- `ensurePersistentMany(items, {concurrency})` — deduplicate and persist a collection with bounded concurrency.

Requirements:

- reuse the existing version-aware `audioCacheKey(item)`;
- `CacheStorage.match(key)` first;
- if hit: return immediately, no network download;
- if miss: fetch and `store.put(key, response.clone())`;
- do not call `blob()`, `arrayBuffer()`, `createObjectURL()`, or `decodeAudioData()` during full-library background persistence;
- preserve the existing no-LRU/no-cap/no-auto-delete retention policy;
- only the device-selected playback format is required for background caching (Opus where supported; MP3 fallback otherwise), not both formats.

## 6. Text/content persistence

Add a small persistent static-resource cache for:

- article content JSON;
- article manifest JSON;
- year-level `bilingual-highlights.json`;
- other article render resources required by the existing loader.

The article bundle store should use a cache-first local read and keep successful bundles in RAM for the page lifetime.

Freshness policy:

- cached content may be served immediately;
- network refresh/revalidation runs in the background;
- a changed response updates the persistent cache for future reads;
- content caching must not force a network request on every article switch.

The catalog itself remains a fresh startup control file so newly published years/articles can be discovered.

## 7. FullLibraryCacheCoordinator

Create an isolated coordinator module, e.g. `full-library-cache.js`.

Responsibilities:

- accept the catalog, article bundle store, audio cache, codec capability, and concurrency settings;
- enumerate every catalog article;
- load/persist each article bundle;
- derive that article's complete sentence audio queue from content + manifest;
- persist only the preferred codec path for every required segment/sentence asset;
- deduplicate repeated asset identities;
- track progress counts;
- tolerate individual resource failures and continue with the rest;
- expose `start()`, `stop()`, `getState()`, and optional progress callback;
- automatically restart from catalog scan on the next page load;
- rely on CacheStorage hits to make restart effectively incremental rather than redownloading completed bytes.

No database or explicit checkpoint file is required for correctness because CacheStorage itself is the durable completion record per asset.

## 8. Scheduling and concurrency

The coordinator starts only after the initial selected article has rendered.

Recommended default background concurrency: 4 persistent network tasks.

Behavior:

- never block first render;
- never await full-library completion before enabling controls;
- if the user requests uncached current audio, interactive playback remains separate and higher priority;
- background workers stop launching new tasks while the page is unloading;
- already-started fetches may finish naturally;
- on next page load, cached assets are skipped.

No Wi-Fi-only gate is added in this version. Opening the site on any working network starts the background cache automatically, matching the requested "open once and let it run" behavior.

## 9. Progress visibility

Add passive status only; no confirmation dialog and no download button.

A small existing-status-compatible indicator may report:

- `离线缓存 623 / 3021`
- `离线缓存完成`
- `离线缓存暂停，等待下次打开继续`

The cache job itself must not depend on this UI.

## 10. Session interruption / resume

If the browser is killed or the OS suspends the tab:

- completed CacheStorage writes remain;
- RAM/decode state is lost normally;
- unfinished network work stops;
- next site open enumerates the library again;
- each already-cached versioned asset is a fast local hit;
- only missing assets are downloaded.

This provides effective resume without maintaining a separate progress database.

## 11. Versioning

Audio:

- reuse current path + generation fingerprint/file hash identity;
- new version => new cache key => new download;
- old bytes are not proactively deleted.

Text/content:

- cache by resource URL and refresh in the background;
- catalog remains fresh enough to discover new releases;
- cached text is local-first for speed, then updated when network content changes.

## 12. Memory policy

Persistent storage:

- cumulative;
- no application quota;
- no LRU;
- no age-based eviction;
- no automatic deletion.

RAM:

- article bundles may remain resident during the page session;
- full-library audio caching must not create Blob URLs or decoded buffers;
- decoded Web Audio remains limited to the active/nearby working set;
- reload/close naturally releases RAM.

Browser/OS site-storage reclamation remains outside application control.

## 13. Failure handling

A failed article/audio asset must not abort the entire library job.

The coordinator records failures in state, continues other assets, and retries naturally on a later page load.

If CacheStorage is unavailable:

- normal reader/playback fallback behavior remains functional;
- full-library persistence reports unavailable rather than repeatedly hammering the network;
- the site remains usable.

## 14. Testing strategy

Implementation is TDD-first.

Required tests:

### Audio cache

- `ensurePersistent()` hits CacheStorage without network when present;
- miss downloads exactly once and stores bytes;
- persistent-only path creates no Blob/Object URL;
- concurrent same-key requests deduplicate;
- version change creates a new identity;
- persistent cache failures degrade safely.

### Static content cache

- first request stores response;
- second read can return local cached content;
- background refresh can replace changed content;
- article switching after persistence does not require network on the critical path.

### FullLibraryCacheCoordinator

- enumerates all catalog articles without user navigation;
- persists all article bundles;
- derives and persists every preferred-codec audio asset;
- skips already cached assets;
- survives one failed asset and continues;
- second run downloads only missing/version-changed assets;
- bounded concurrency is respected;
- no full-library audio decode/Blob creation occurs.

### Integration

- full-library cache starts automatically after first article render;
- UI remains usable while it runs;
- current article/player priority remains intact;
- killing/restarting is represented by two coordinator runs sharing the same fake CacheStorage and proves resume-by-cache-hit;
- existing Reader CI remains green.

## 15. Rollout

1. Add persistent-only audio cache API and tests.
2. Add static content CacheStorage layer and tests.
3. Add `FullLibraryCacheCoordinator` and tests.
4. Integrate automatic startup after first article render.
5. Add passive progress indicator.
6. Run full Reader CI.
7. Publish without regenerating existing audio.
8. Real-device smoke test: first-run background fill, kill/reopen resume, warm arbitrary-year switch, warm arbitrary-sentence audio.

## 16. Acceptance criteria

The feature is accepted when:

- opening the site once automatically begins caching every catalog article and every required audio asset;
- the user does not need to visit each year/article;
- already cached unchanged assets are not downloaded again;
- interrupting the page preserves completed cache work;
- reopening automatically continues until complete;
- full-library caching does not decode/store all audio in RAM;
- after completion, arbitrary article switching is local-first and arbitrary audio playback no longer requires a fresh network download;
- existing permanent-cache policy remains unchanged;
- all automated tests and deployment gates pass;
- real-device testing confirms materially faster warm revisits across arbitrary years/articles.
