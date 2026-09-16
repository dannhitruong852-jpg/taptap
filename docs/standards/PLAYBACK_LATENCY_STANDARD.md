# Playback Latency Standard

Status: production standard
Scope: every year and every article in `kaoyan-reader-v1`, including legacy 2002 assets and all V4/current/future assets.

## Goal

Article switching and sentence playback must feel local. Network/buffer latency must not be perceived as an intentional pause, and it must never be mixed with the actor's semantic/prosodic pauses.

## User-facing latency targets

- Resident article bundle switch: normally <= 50 ms user-perceived on a modern phone, excluding unusual main-thread contention.
- Decoded Web Audio sentence start: target <= 50 ms from playback request to `AudioBufferSourceNode.start()` once the sentence buffer is resident.
- Persistent-cache HTMLAudio fallback hit: target click-to-audible <= 100-150 ms under normal device conditions.
- Cold first-use asset: network download and initial decode are physically unavoidable; immediately convert a successful cold fetch into a persistent local asset and decoded RAM working-set entry where Web Audio is supported.
- Automatic sentence-to-sentence continuation with the next decoded buffer resident: no intentional transport gap; target transport contribution < 50 ms.
- UI `playing` state should track actual media/source start rather than merely the click event.

These are product/SLO targets. Automated tests verify deterministic memory/cache/decode/sequencing mechanisms; real-device smoke tests verify acoustic end-to-end latency.

## Mandatory article-switch architecture

1. Article content, manifest data, and bilingual-highlight mappings use a RAM-resident `ArticleBundleStore` during the page lifetime.
2. The currently selected article loads first. Remaining article bundles preload progressively with bounded concurrency after first render.
3. Once an article bundle is resident, later switches to it must not perform a selection-time network request or Cache Storage lookup.
4. Year-level bilingual mappings should be shared/deduplicated rather than fetched once per article.
5. Stale article-selection completions must never replace the current selection.
6. Global article preload must never block first render.
7. Article content, manifests, and bilingual mappings also use a persistent static CacheStorage layer so a new page session can recover locally before background refresh.

## Mandatory playback architecture

1. One playback implementation is shared by all years. No year-specific latency hacks.
2. Browser `HTMLAudioElement.preload` is not accepted as the primary caching mechanism because it is advisory on mobile browsers.
3. Successfully fetched audio bytes are stored in browser Cache Storage under a version-aware identity.
4. Cache identity includes final resolved media path plus the best available manifest generation fingerprint/file hash. Root manifest fingerprints must propagate to sentence/segment queue items when child entries do not carry their own version. A changed asset version must not reuse stale bytes or stale decoded buffers.
5. Concurrent requests for the same cache identity are deduplicated to one in-flight fetch.
6. Web Audio is the preferred prepared-playback path. Compressed cached bytes are decoded into `AudioBuffer` objects and retained in RAM for the active working set.
7. Prepared playback starts from an `AudioBufferSourceNode`, so a decoded sentence click must not perform network fetch, Cache Storage lookup, Blob creation, or decode work on the click path.
8. The existing Blob/Object-URL + HTMLAudio path remains a required fallback when Web Audio is unavailable or a decode/start attempt fails.
9. Opening an article prepares the current sentence and next 3 first, then the remainder of the current article.
10. Previous and next article audio are prepared in the background after the active article work is scheduled, so normal sequential navigation is more likely to arrive with decoded buffers already resident.
11. Viewport-near sentences may be raised in preparation priority while the reader scrolls.
12. Legacy multi-segment sentences must prepare every segment required for the sentence, not only the first segment.
13. Web Audio playback must preserve pause/resume, logical progress timing, automatic queue continuation, and speed controls 0.85 / 1.0 / 1.15.
14. No added `setTimeout`/sleep is permitted between sentences. Rhetorical pauses belong inside produced audio/direction, never transport code.
15. Stale async decode/cache/playback completions from an old article/selection must never start playback or surface errors into the new selection.

## Full-library background persistence

1. After the initial selected article renders, the reader automatically enumerates every article in the current catalog and persists the complete library without requiring manual year/article navigation.
2. Full-library persistence includes required article JSON, manifests, year-level bilingual mappings, and the preferred-codec audio assets for every sentence/segment.
3. Background audio persistence stores compressed bytes only. It must not call `blob()`, create Blob/Object URLs, call `decodeAudioData()`, or retain the entire audio library as decoded `AudioBuffer` objects.
4. Opus is persisted when supported by the device; MP3 is used as the background-cache fallback when Opus is unsupported. Both encodings are not downloaded solely for offline caching.
5. Full-library audio download concurrency is globally bounded to 4 tasks by default.
6. Reopening the reader scans the catalog again and uses version-aware CacheStorage hits as the durable completion record. Already-cached unchanged assets are skipped; only missing/new-version assets are downloaded.
7. If the browser/tab is killed before completion, completed CacheStorage writes remain valid. The next page session automatically resumes by cache-hit skipping; a separate checkpoint database is not required for correctness.
8. Full-library persistence never blocks first article rendering or explicit user playback. The visible/current article and user-requested audio remain the interactive path.
9. Individual resource failures do not abort the whole library job. Failed items are retried naturally on a later page session.
10. A passive progress indicator may report article/audio completion, but no confirmation dialog or download button is required.

## Persistent retention policy

1. Persistent audio retention is cumulative by default. The application must not impose a storage quota, LRU policy, age limit, or automatic deletion of previously cached audio.
2. Normal browsing should request browser persistent-storage protection when `navigator.storage.persist()` is available. Refusal or lack of support must not break playback.
3. Closing an article, reloading the page, or closing the browser must not intentionally delete Cache Storage audio. The browser/OS may still reclaim site data under its own platform policies; the application does not control that external behavior.
4. Private/incognito browsing is storage-isolated from normal browsing and may discard its site data when the private session ends. This is expected platform behavior, not an application cleanup policy.
5. In-page Blob/Object URLs and decoded `AudioBuffer` objects are RAM working-set state and may be released without deleting persistent Cache Storage bytes.
6. If Cache Storage is unavailable or denied, playback degrades to the remote media path rather than failing the reader.

## Audio-asset edge-silence standard

For newly generated or regenerated production assets, unintended leading silence should normally be <= 150 ms. This is a production QA guardrail, not a reason to trim meaningful internal pauses or re-render otherwise-correct historical audio.

## Non-goals

- Do not compress, time-stretch, or remove natural pauses inside a sentence to meet transport latency targets.
- Do not change C-mode direction, casting, emotion, sentence segmentation, translation, vocabulary, or content.
- Do not regenerate 2002-2006 audio solely for this transport fix when the asset itself has no abnormal leading silence.
- Do not merge each article into one monolithic audio file just to hide transport latency.
- Do not automatically evict old persistent audio merely to enforce an application-defined capacity budget.
- Do not decode all years of audio into RAM at startup. Decode the active/nearby working set; article text/data may remain RAM-resident for the page lifetime.

## Verification

A latency change is acceptable only when:

- unit tests prove resident article bundles return without a second fetch;
- unit tests prove year-level mapping reuse and progressive bundle preload;
- unit tests prove first audio fetch stores bytes and later resolution can hit persistent cache without a second network fetch;
- unit tests prove persistent-only full-library audio caching creates no Blob/Object URLs;
- unit tests prove a warm restart skips already completed versioned audio and downloads only missing assets;
- unit tests prove the full-library coordinator traverses all catalog articles without user navigation;
- unit tests prove background audio progress is reported incrementally;
- unit tests prove concurrent byte/decode requests deduplicate;
- unit tests prove fingerprint/version changes change persistent and decoded identity;
- unit tests prove normal browsing requests persistent-storage protection at most once per cache instance;
- unit tests prove application cache-maintenance code performs no persistent Cache Storage deletion or capacity eviction;
- unit tests prove decoded RAM cleanup never deletes persistent audio;
- Web Audio unit tests cover start, queue continuation, stop, pause/resume, speed changes, and stale async suppression;
- hybrid-player tests prove HTMLAudio fallback is used when Web Audio preparation/start fails;
- stale playback callbacks/resolutions remain suppressed after article/selection changes;
- the full `kaoyan-reader-v1` Node test suite passes;
- existing bilingual validation/rebuild gates pass;
- deployed browser/mobile smoke checks cover cold first play, decoded warm replay, reload replay, automatic full-library fill/resume, arbitrary sentence tap, automatic handoff, pause/resume, speed switching, and repeated A -> B -> A article switching.

The reader records passive `article-switch` and `audio-start` performance measurements to support real-device diagnosis. CI must not be used to claim acoustic <= 50 ms; that requires device measurement.

This standard is the baseline for 2002 through all future exam years.
