# Playback Latency Standard

Status: production standard
Scope: every year and every article in `kaoyan-reader-v1`, including legacy 2002 assets and all V4/current/future assets.

## Goal

Playback must feel immediate. Network/buffer latency must not be perceived as an intentional pause, and it must never be mixed with the actor's semantic/prosodic pauses.

## User-facing latency targets

- Warm/preloaded sentence: target click-to-audible <= 250 ms under normal device conditions.
- Cold sentence: target click-to-audible <= 700 ms under normal Wi-Fi/4G/5G conditions.
- Automatic sentence-to-sentence continuation: no artificial inter-sentence timer; the next sentence must already be warming before the current sentence ends.
- UI `playing` state should track actual media start as closely as the browser permits, not merely the click event.

These are product/SLO targets. Unit tests verify the deterministic mechanisms that make them possible; real-device smoke tests are used for end-to-end latency.

## Mandatory playback behavior

1. One playback implementation is shared by all years. Do not add year-specific latency hacks.
2. Opening an article warms the current sentence and the next 3 sentences.
3. The playback cache reuses the exact preloaded `Audio` object for the same resolved media path; a click must not create a second network request when a warm object already exists.
4. Viewport-near sentences are warmed while the reader scrolls so direct sentence taps are normally cache hits.
5. The cache is bounded. Old non-active entries are evicted instead of allowing article-length memory growth.
6. Article changes clear the old article's warm cache and cancel stale playback callbacks.
7. Both Opus and MP3 fallback paths obey the same policy; caching keys use the final resolved path actually played by the browser.
8. Legacy multi-segment sentences warm every segment needed for the sentence, not only the first segment.
9. No added `setTimeout`/sleep is permitted between sentences. Any rhetorical pause belongs inside the produced audio or semantic direction, not in transport code.
10. Playback speed controls (0.85 / 1.0 / 1.15) must continue to work on preloaded/reused audio.

## Audio-asset edge-silence standard

For newly generated or regenerated production assets, unintended leading silence should normally be <= 150 ms. This is a production QA guardrail, not a reason to trim meaningful internal pauses or re-render otherwise-correct historical audio.

## Non-goals

- Do not compress, time-stretch, or remove natural pauses inside a sentence to meet transport latency targets.
- Do not change C-mode direction, casting, emotion, sentence segmentation, translation, vocabulary, or content.
- Do not regenerate 2002-2006 audio solely for this transport fix when the asset itself has no abnormal leading silence.

## Verification

A playback change is acceptable only when:

- unit tests prove a preloaded object is reused for playback;
- stale playback callbacks remain suppressed after selection changes;
- the full `kaoyan-reader-v1` Node test suite passes;
- browser smoke verification confirms 2002 and at least one V4 year still play;
- mobile/manual smoke testing checks first-sentence start, arbitrary visible-sentence tap, automatic next-sentence handoff, pause/resume, and speed switching.

This standard is the baseline for 2002 through all future exam years.
