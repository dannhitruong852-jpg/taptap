# Playback Latency Standard

Status: production standard
Scope: every year and every article in `kaoyan-reader-v1`, including legacy 2002 assets and all V4/current/future assets.

## Goal

Playback must feel immediate. Network/buffer latency must not be perceived as an intentional pause, and it must never be mixed with the actor's semantic/prosodic pauses.

## User-facing latency targets

- Persistent-cache hit: target click-to-audible <= 100-150 ms under normal device conditions.
- Cold first-use asset: download time is physically unavoidable; immediately convert a successful cold fetch into a persistent local asset.
- Automatic sentence-to-sentence continuation with the next asset resident: transport gap target < 100 ms, with no artificial timer.
- UI `playing` state should track actual resolved media playback rather than merely the click event.

These are product/SLO targets. Unit tests verify the deterministic cache and sequencing mechanisms; real-device smoke tests verify end-to-end latency.

## Mandatory playback architecture

1. One playback implementation is shared by all years. No year-specific latency hacks.
2. Browser `HTMLAudioElement.preload` is not accepted as the primary caching mechanism because it is advisory on mobile browsers.
3. Successfully fetched audio bytes are stored in the browser Cache Storage API under a version-aware cache identity.
4. Playback of a cached asset uses a Blob/Object URL created from the cached local bytes, so replay does not require a fresh audio network transfer.
5. Cache identity includes the final resolved media path plus the best available manifest generation fingerprint/file hash. A changed asset version must not reuse stale bytes.
6. Concurrent requests for the same cache identity are deduplicated to one in-flight fetch.
7. Opening an article immediately warms the current sentence and the next 3 sentences, then warms the remainder of the article during idle time.
8. Viewport-near sentences are raised in warm priority while the reader scrolls.
9. Legacy multi-segment sentences warm every segment required for the sentence, not only the first segment.
10. The persistent byte cache survives article changes and page reloads. Only the bounded Blob/Object-URL memory layer is cleared/evicted.
11. Blob URLs are bounded by LRU-style memory management; a source currently in playback is pinned and must not be revoked until playback ends/stops/errors.
12. If Cache Storage is unavailable or denied, playback degrades to the remote media path rather than failing the reader.
13. No added `setTimeout`/sleep is permitted between sentences. Rhetorical pauses belong inside produced audio/direction, never transport code.
14. Playback speed controls 0.85 / 1.0 / 1.15 must continue to work with local cached sources.
15. Stale async cache resolutions from an old article/selection must never start playback or surface errors into the new selection.

## Audio-asset edge-silence standard

For newly generated or regenerated production assets, unintended leading silence should normally be <= 150 ms. This is a production QA guardrail, not a reason to trim meaningful internal pauses or re-render otherwise-correct historical audio.

## Non-goals

- Do not compress, time-stretch, or remove natural pauses inside a sentence to meet transport latency targets.
- Do not change C-mode direction, casting, emotion, sentence segmentation, translation, vocabulary, or content.
- Do not regenerate 2002-2006 audio solely for this transport fix when the asset itself has no abnormal leading silence.
- Do not merge each article into one monolithic audio file just to hide transport latency.

## Verification

A playback change is acceptable only when:

- unit tests prove first fetch stores bytes and later resolution can hit persistent cache without a second network fetch;
- unit tests prove concurrent resolves deduplicate;
- unit tests prove fingerprint/version changes change cache identity;
- unit tests prove active local Blob sources remain pinned through playback and are unpinned afterward;
- stale playback callbacks/resolutions remain suppressed after article/selection changes;
- persistent-cache failure falls back to remote playback;
- the full `kaoyan-reader-v1` Node test suite passes;
- deployed browser/mobile smoke checks cover cold first play, warm replay, reload replay, arbitrary visible-sentence tap, automatic handoff, pause/resume, and speed switching.

This standard is the baseline for 2002 through all future exam years.
