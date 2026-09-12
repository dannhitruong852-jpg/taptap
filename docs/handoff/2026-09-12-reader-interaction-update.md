# Reader interaction update - 2026-09-12

User-approved scope: default English-only cards; short tap toggles only that card's translation; long press / drag / context menu retain native text selection without toggling translation or audio. A separate numbered play button and the existing transport controls play audio.

The three top pills are replaced by one compact 6+ vocabulary switch. It controls English vocabulary and its occurrence-specific Chinese counterpart together. All six 2002 units have a reviewed sidecar mapping (133 occurrences), without changing original text, translations, vocabulary grades, voice direction or existing audio.

Speed uses a five-stop magnetic slider: 0.7, 1.0, 1.25, 1.5, 2.0. Thumb and numeric display are draggable, the number enlarges while held, intermediate preview applies to the current media element, and release snaps. Keyboard arrows/Home/End select fixed stops. Article switches retain speed but reset translation visibility. Hidden translations still retain their read-along DOM; revealing them never restarts audio.

No TTS generation occurs in the UI acceptance workflow. Both local-served and public Pages mobile browser tests gate delivery; screenshot and test reports are retained as artifacts. Existing scroll direction behavior is retained, with complete off-screen hiding of the player.

Known unchanged limitation: read-along remains the earlier time/cue-proportion implementation, not forced-aligned word timestamps. No new claim of precise bilingual timing or C-mode artistic acceptance is made in this UI release.
