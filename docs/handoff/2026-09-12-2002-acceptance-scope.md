# 2002-only acceptance checkpoint

The user has narrowed the immediate deliverable to the 2002 paper. All earlier C-mode, translation, vocabulary, scope, static-TTS and mobile-player requirements still apply. Do not restart product design or generate the other 26 years.

## Content

The reviewed manuscript is `content-pipeline/curated/2002.json`. Its compiler produces six units: cloze (13 sentences), Text 1 (21), Text 2 (16), Text 3 (21), Text 4 (15), and the five original underlined translation sentences. Total: 91 sentence rows, 165 explicitly directed audio segments. The 2002 Part B is translation, not a missing seven-choice section. Surrounding translation context is separately described, not mixed into the five designated English segments.

The cloze key is traced to the FLTRP-authorized Sina publication. Its numbering 21–40 maps to uploaded PDF blanks 1–20. Both original choices and deterministic reconstruction are reported under `reports/extraction`. No answer options or writing tasks enter the reader.

English/Chinese alignment, focus and discourse choices are authored offline. Python only compiles these decisions; it is not claimed to create faithful translations or semantic direction from regular expressions. Vocabulary is an explicitly named project-curated 1–9 scale, with 6+ highlighted, not an official graded vocabulary standard.

## Preserved behavior

The original `content/2002/text1.json` and `audio/2002/text1` pilot are retained. New C assets use `content/2002/c` and `audio/2002/c-*`. The existing player shell, Twitter-like downward hide/upward return, speeds, replay, sentence progression and highlights are retained. Catalog navigation cancels old playback; unsupported Opus can use the generated MP3 counterpart. No browser speech synthesis is used.

The old B2 automatic generator is now manual-only to avoid wasting generation when C code changes. Its original sample remains available in the repository.

## Generation and verification

The new `2002 C acceptance build` workflow verifies content, voice and site suites, then runs a real mobile browser smoke test. It can publish readable text before preparing references and starting 18 independent Chatterbox shards. Individual generation failures receive bounded retries; verified partial results are retained. The publisher checks audio hashes and render-input fingerprints, and never force-pushes gh-pages.

Only the three existing lawful pilot references (05/12/13) are used. This does NOT complete the full fifteen-actor reference library. C narration now has explicit clause-level rate, exaggeration, CFG and pause variation; this must still be listened to and accepted. A schema/CI pass is not artistic acceptance.

The renderer checks invalid/silent audio, excessive clipping and implausible pace, and emits Opus plus MP3. ASR comparison and speaker-consistency verification are NOT performed. All generated audio remains `candidate`.

Before stating production is underway or complete, inspect the actual workflow run and `reports/qa/2002-audio.json`. No run ID or successful deployment is asserted by this source checkpoint itself.
