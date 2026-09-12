# 2002-only acceptance checkpoint

The user has narrowed the immediate deliverable to the 2002 paper. All earlier C-mode, translation, vocabulary, scope, static-TTS and mobile-player requirements still apply. Do not restart product design or generate the other 26 years.

## Verified execution checkpoint — 2026-09-12

This dated checkpoint supersedes the older handoff's implementation-status statements for the 2002 acceptance slice only. The older document remains the source of the broader product requirements.

- Implementation commit: `73d325d5730670760f4b661a8d2805022c7ddbdd`.
- Combined CI run `34677843195` passed: 22 content tests, 20 voice tests, 11 reader tests (53 total). A fresh download of that exact commit's source also passed all three suites locally.
- The initial batch workflow run `34677842696` failed before jobs because runner context was used at job-env level. Commit `a13aa3dd12ce1e86fac41d7c40d1168d8e71eee4` fixed the cache path. Do not confuse this workflow configuration failure with failing content tests.
- Real acceptance run: `34677970587` (`2002 C acceptance build`). Its prepare job `103511151867` completed successfully, including all tests, real Chromium mobile-viewport navigation/scroll tests, text publication, and preparation of three lawful reference clips. Eighteen independent render jobs were started. At this checkpoint audio completion has NOT been verified; inspect that run rather than assuming success.
- The mobile browser test verified six-entry selection, cloze/reading/translation filtering, downward whole-player hiding and upward restoration, with no JavaScript page errors. Screenshots are in artifact `2002-mobile-browser-check` of the acceptance run. This is Chromium at a mobile viewport, not a physical vivo-device acceptance test.
- Text-only Pages publication commit: `085c67586ca1331957c3723e523f8738c149ce48`. The public URL remains `https://dannhitruong852-jpg.github.io/taptap/kaoyan-reader-v1/`.
- Live deployment verification run `34678085851` passed: it fetched the actual public HTML, catalog, and all six article JSON files and verified 91 aligned sentences. This is stronger than merely finding files on gh-pages.
- After render jobs finish, the publish job is configured to merge only matching, intact assets and publish an explicit missing-segment report. Do not assert 165/165 success, complete C listening acceptance, ASR QA, or full speaker-library completion without new evidence.

## Content

The reviewed manuscript is `content-pipeline/curated/2002.json`. Its compiler produces six units: cloze (13 sentences), Text 1 (21), Text 2 (16), Text 3 (21), Text 4 (15), and the five original underlined translation sentences. Total: 91 sentence rows, 165 explicitly directed audio segments. The 2002 Part B is translation, not a missing seven-choice section. Surrounding translation context is separately described, not mixed into the five designated English segments.

The cloze key is traced to the FLTRP-authorized Sina publication. Its numbering 21–40 maps to uploaded PDF blanks 1–20. Both original choices and deterministic reconstruction are reported under `reports/extraction`. No answer options or writing tasks enter the reader.

English/Chinese alignment, focus and discourse choices are authored offline. Python only compiles these decisions; it is not claimed to create faithful translations or semantic direction from regular expressions. Vocabulary is an explicitly named project-curated 1–9 scale, with 6+ highlighted, not an official graded vocabulary standard.

## Preserved behavior

The original `content/2002/text1.json` and `audio/2002/text1` pilot are retained. New C assets use `content/2002/c` and `audio/2002/c-*`. The existing player shell, Twitter-like downward hide/upward return, speeds, replay, sentence progression and highlights are retained. Catalog navigation cancels old playback; unsupported Opus can use the generated MP3 counterpart. No browser speech synthesis is used.

The old B2 automatic generator is now manual-only to avoid wasting generation when C code changes. Its original sample remains available in the repository.

## Generation and verification

The `2002 C acceptance build` workflow verifies content, voice and site suites, then runs a real mobile browser smoke test. It publishes readable text before preparing references and starting 18 independent Chatterbox shards. Individual generation failures receive bounded retries; verified partial results are retained. The publisher checks audio hashes and render-input fingerprints, and never force-pushes gh-pages. An explicit Pages build request follows token-authenticated pushes.

Only the three existing lawful pilot references (05/12/13) are used. This does NOT complete the full fifteen-actor reference library. C narration now has explicit clause-level rate, exaggeration, CFG and pause variation; this must still be listened to and accepted. A schema/CI pass is not artistic acceptance.

The renderer checks invalid/silent audio, excessive clipping and implausible pace, and emits Opus plus MP3. ASR comparison and speaker-consistency verification are NOT performed. All generated audio remains `candidate`.

Before describing the current audio state, inspect run `34677970587`, `reports/qa/2002-audio.json`, and `kaoyan-reader-v1/content/2002/audio-status.json`. A running job may still be installing dependencies; its existence does not by itself prove audio clips have already been generated.
