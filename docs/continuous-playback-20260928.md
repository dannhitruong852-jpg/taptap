# Continuous article playback

The reader's **连续播放** switch advances from a naturally completed article
to the next entry in the full catalog, including year boundaries. It starts
at sentence zero without changing playback speed. The switch defaults off
and is remembered on the current device. The final catalog entry stops;
there is no wraparound.

Pausing, disabling continuous playback, or manually choosing an article
cancels a pending automatic handoff. Failed content/audio loads stop with
the existing error feedback. The existing Web Audio and HTMLAudio players
are retained; stopped asynchronous Web Audio attempts cannot start a late
fallback. No Android package changes are required: its WebView loads the
same GitHub Pages reader. Versioned JS/CSS URLs refresh these assets.

## Verification

- `cd kaoyan-reader-v1 && npm test`: 117 tests pass.
- `npm ci && npm run test:dom`: 7 tests pass with the real application,
  controls, catalog, and player modules in jsdom. Only network responses and
  the platform Audio device are substituted. Covers next article/year,
  final stop, saved switch, pause/resume, and cancellation during loading
  via pause, switch, article selector, and next button.
- Review caught ignored next-button clicks during automatic loading. The
  DOM test reproduced unwanted playback before the fix and passes after it.

Actual Android/iOS device behavior and operating-system background playback
are not represented by jsdom tests. Background/lock-screen playback is not
added by this change.
