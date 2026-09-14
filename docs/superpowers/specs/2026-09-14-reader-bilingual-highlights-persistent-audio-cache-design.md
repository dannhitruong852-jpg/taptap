# Reader bilingual highlights and persistent audio cache design

Date: 2026-09-14
Status: approved design
Scope: `kaoyan-reader-v1`, all exam years from 2002 through future years

## 1. Problem statement

Two production defects remain after the first 2003-2006 rollout.

First, Chinese translation emphasis is inconsistent. In 2002, English vocabulary entries at level 6+ can be linked to one or more exact Chinese spans through occurrence-specific bilingual mappings. The reader renders those Chinese spans in bold. For 2003-2006, the English vocabulary exists but equivalent Chinese span mappings were not produced, and the reader still loads the legacy 2002 bilingual mapping file directly. The result is that English vocabulary is emphasized while the Chinese translation is not.

Second, playback latency remains perceptible on mobile. The current implementation reuses `Audio` elements and calls `preload='auto'`/`load()`, but browser media preloading is advisory. Mobile browsers may defer or partially satisfy these requests, so a supposedly warm sentence can still wait for network/media buffering when the user taps play.

These are global reader concerns. They must not be fixed with year-specific branches.

## 2. Goals

### 2.1 Bilingual highlighting

- Every year uses the same bilingual-highlight contract.
- Every English vocabulary occurrence with `level >= 6` should have an occurrence-specific Chinese mapping when a faithful corresponding Chinese span exists.
- Chinese emphasis must be derived from reviewed mapping data, not runtime machine translation, fuzzy matching, or dictionary lookup.
- Existing sentence text, translation wording, vocabulary levels, actor direction, and audio are not rewritten merely to create a highlight.
- The build/QA pipeline must detect missing, stale, out-of-range, or text-mismatched mappings before publication.

### 2.2 Playback latency

- Once an audio asset has been fetched successfully, later playback should not depend on a new network request.
- Warm sentence click-to-audible target: <= 100-150 ms under normal device conditions.
- Automatic sentence handoff transport gap target: < 100 ms when the next asset is already resident.
- Cold first-use latency remains constrained by physical download time, but the system should aggressively convert cold assets into persistent local assets.
- The same cache behavior applies to legacy 2002 audio, V4 2003-2006, and all future years.

## 3. Non-goals

- Do not regenerate 2002-2006 TTS solely for this change.
- Do not remove natural silence, prosody, rhetorical pauses, or C-mode timing from audio content.
- Do not merge an article into one monolithic audio file.
- Do not introduce runtime AI.
- Do not infer Chinese highlight spans at runtime.
- Do not add separate player implementations per year.

## 4. Bilingual highlight architecture

### 4.1 Canonical mapping format

Each article receives reviewed occurrence-specific mappings. A mapping entry contains:

- sentence id
- English start/end character offsets
- exact English source text
- one or more Chinese spans with start/end offsets and exact Chinese source text

The contract is intentionally equivalent to the proven 2002 mapping semantics. Shared Chinese spans are allowed where the translation legitimately expresses multiple English vocabulary items together.

### 4.2 Storage

Move from the legacy 2002-only loader to a year/article-neutral mapping layer.

Preferred storage:

`kaoyan-reader-v1/content/<year>/bilingual-highlights.json`

Each file contains all articles for that year. This keeps mappings versionable with the year's reviewed content while avoiding one extra request per article.

2002 can either be migrated into the same location/schema or supported through a one-time compatibility adapter during migration. The end state must expose one uniform loader contract to the reader.

### 4.3 Authoring 2003-2006 mappings

Generate candidate mappings from the curated English vocabulary occurrences and existing Chinese translations, then manually/review deterministically before publication. Candidate generation may assist editors, but publication data must contain exact offsets and exact source text so stale mappings fail closed.

Rules:

- only `level >= 6` occurrences are in scope for required visual emphasis;
- do not force a mapping if the Chinese translation genuinely omits or restructures the concept beyond a clean span;
- if an English occurrence maps to a multi-character phrase, highlight the faithful phrase, not a mechanically short substring;
- preserve translation text byte-for-byte.

### 4.4 Runtime rendering

`renderChinese()` remains the renderer. It receives year/article-specific mappings from the article loader rather than from a global 2002-only promise.

The rendering contract stays strict:

- English offsets must resolve to the declared English text;
- the target occurrence must correspond to a `level >= 6` vocab item;
- Chinese offsets must resolve to the declared Chinese text;
- invalid entries are ignored at render time and fail build-time QA.

### 4.5 QA

Add deterministic validation that reports, per year/article:

- total `level >= 6` vocabulary occurrences;
- mapped occurrences;
- intentionally unmapped reviewed exceptions, if any;
- stale English spans;
- stale Chinese spans;
- out-of-range spans;
- mapping references to nonexistent sentences.

Publication must fail on stale/invalid mappings. Required coverage should be 100% except explicitly reviewed exceptions recorded in data with a reason.

## 5. Persistent audio cache architecture

### 5.1 Why the current approach is insufficient

`HTMLAudioElement.preload` is a hint, not a guarantee that the full media payload has been fetched and retained. Reusing the element avoids object recreation but does not guarantee zero network dependence. This explains the remaining >1 s mobile latency.

### 5.2 Two-layer cache

Use two layers:

1. **Persistent byte cache** using the browser Cache Storage API.
2. **Active in-memory playback layer** using Blob URLs created from cached response bytes.

Flow:

`manifest path -> cache key -> CacheStorage response -> Blob -> object URL -> Audio`

If the asset is absent from Cache Storage:

`network fetch -> validate success -> cache cloned response -> Blob -> object URL -> Audio`

Once cached, future page loads can play from locally stored bytes without a network fetch for that asset.

### 5.3 Cache identity and invalidation

Cache entries must be version-aware. The key should include the final resolved media path plus a stable asset version/fingerprint from the manifest where available. If a manifest does not expose a fingerprint, use a reader audio-cache version namespace plus the path.

When an asset fingerprint/path changes, it becomes a new cache key. Old cache generations can be pruned during startup or after successful warm-up.

Do not rely on mutable path-only caching forever, because regenerated audio at the same URL could otherwise remain stale.

### 5.4 Warming policy

When an article opens:

- immediately warm current sentence;
- warm the next 3 sentences with high priority;
- after first paint/idle time, continue warming the remaining article in the background;
- when the viewport moves, raise visible and near-visible sentences in priority;
- for legacy multi-segment sentences, warm every segment required for that sentence.

The system must avoid flooding the network. Use a small bounded fetch concurrency (for example 2-4 simultaneous audio fetches) and deduplicate in-flight requests by cache key.

### 5.5 Playback policy

The player should request a resolved local playback source from the cache layer rather than constructing an `Audio` directly from the remote path.

For a warm asset:

- obtain/reuse its Blob URL;
- set `Audio.src` to the Blob URL;
- play immediately.

For a cold asset tapped before background warm-up finishes:

- promote that request to highest priority;
- await the existing in-flight fetch if one exists;
- do not issue a duplicate fetch;
- update UI state so `playing` reflects actual media start rather than the initial tap.

### 5.6 Memory management

Cache Storage holds persistent bytes. Blob URLs are only the active memory layer and must be bounded.

- maintain a small LRU of Blob URLs/audio objects around current and nearby sentences;
- revoke object URLs when evicted or when changing article, unless still active;
- never revoke the source used by the currently playing audio;
- keep persistent Cache Storage entries across article changes and page reloads.

### 5.7 Platform fallback

If Cache Storage is unavailable or storage writes fail:

- fall back to the existing network URL playback path;
- retain in-memory reuse for the current session;
- do not make the reader unusable merely because persistent caching is unavailable.

The fallback is degraded performance, not a content failure.

## 6. Reader integration boundaries

Introduce a focused cache module, e.g. `audio-cache.js`, responsible for:

- cache key creation;
- persistent lookup/fetch/store;
- in-flight deduplication;
- Blob URL creation/reuse/revocation;
- warm-window/background-article scheduling;
- cache generation pruning.

`audio-player.js` remains responsible for sequencing, pause/resume, timing callbacks, speed, and stale-generation suppression.

`app.js` remains responsible for article selection, sentence state, viewport awareness, and deciding which queues to warm. It should not directly implement Cache Storage internals.

This separation prevents another large player file from mixing transport, persistence, UI, and article navigation concerns.

## 7. Testing strategy

Follow TDD for production behavior changes.

### 7.1 Bilingual tests

- a 2003+ sentence with a mapped level-6+ vocab occurrence renders the correct Chinese `<strong>` span;
- stale English offset is rejected;
- stale Chinese offset is rejected;
- loader selects mapping data by year/article rather than hardcoded 2002;
- coverage validator catches an unreviewed missing mapping.

### 7.2 Cache tests

With fake Cache Storage/fetch primitives:

- first request fetches network and stores a response;
- second request for the same versioned key does not call network;
- two concurrent requests deduplicate to one fetch;
- warm queue produces local Blob-backed playback sources;
- article/background warming respects bounded concurrency;
- version/fingerprint change creates a new cache identity;
- Blob URL eviction revokes old URLs but not the active one;
- persistent-cache failure falls back to remote playback;
- stale playback callbacks remain suppressed.

### 7.3 Browser smoke

Verify on the deployed site:

- 2002 Chinese vocabulary highlighting still works;
- at least one 2003-2006 article highlights both English and Chinese level-6+ vocabulary;
- first cold play works;
- replay of the same sentence after cache population is near-immediate;
- reload page, replay a previously cached sentence, verify no user-visible network wait;
- automatic next-sentence handoff has no artificial transport pause;
- pause/resume and 0.85/1.0/1.15 speed remain correct.

## 8. Migration and rollout

1. Add the unified bilingual mapping loader and tests.
2. Produce and validate 2003-2006 bilingual highlight mappings without changing translation text.
3. Migrate 2002 to the unified loader contract.
4. Add the persistent audio cache module behind the existing reader player API.
5. Integrate current/next/visible/background article warming.
6. Run full reader unit tests and bilingual mapping coverage QA.
7. Publish to the feature branch Pages target and run browser/mobile smoke checks.
8. Make these contracts part of the standard batch pipeline before starting later-year production.

## 9. Acceptance criteria

The change is accepted only when all of the following are true:

- 2002 remains intact.
- 2003-2006 Chinese translations visually emphasize reviewed equivalents of level-6+ English vocabulary.
- mapping QA is year-neutral and blocks invalid/stale mappings.
- a cached audio asset can be replayed without a new network fetch.
- cache identity changes when the underlying asset version changes.
- automatic sentence transitions introduce no explicit delay timer.
- all existing reader tests plus new bilingual/cache tests pass.
- deployed browser smoke tests pass for 2002 and V4 content.
- the resulting design is the default contract for future 2007-2026 batches.
