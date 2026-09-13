# C v4 actor expansion automated gate

This phase replaces the audition-board decision for **new** actors with a deterministic, fail-closed gate. It does not reinterpret the eight historical human approvals.

## Policy

Every actor must supply A/B/C renders for all ten director intents. The gate checks transcript WER, actor/reference identity, licensed reference and audio hashes, fingerprint freshness, decodability evidence, alignment and bounded monotonic words, 105–190 WPM, clipping, edge and internal silence, speaker similarity, automated naturalness and intent fidelity, and the immutable `artificial_pause_ms=0` / `post_tempo=false` rules. Candidate ranking is deterministic: mean naturalness/intent/speaker score, distance from the middle of the accepted pace band, then B/A/C as a stable tie-break. Any uncovered intent rejects the whole actor.

Inherited numeric limits come from the existing B2 voice design (WER 0.08, clipping 0.1%, edge silence 0.60 s, speaker similarity 0.65, and the existing `qa.py` 105–190 WPM production band). C v4 automation explicitly versions the previously human-only replacements: internal silence at 1.20 s and machine-produced naturalness and director-intent scores at 0.75. Changes require a new policy ID and tests; they must never be relaxed to admit an actor.

Automated admissions must record `approval_method: automated_c_v4_qa` and `qa_policy`. Existing approvals truthfully retain `approval_method: human_listening`.

## 2026-09-13 environment-blocked run

Actors 03, 06, 07, 10, 11, 14, and 15 were **not evaluated and are not rejected**. The checked-out baseline does not contain their source-speaker mapping or profiles. This container also has no FFmpeg, Chatterbox, Torch, Torchaudio, model weights, or EARS audio, and its outbound HTTPS proxy rejects GitHub, PyPI, and EARS downloads with HTTP 403. Consequently a genuine render and QA run cannot be performed here.

No result from missing evidence is written into `production_approvals.json`. Production remains the historical eight actors until a capable runner generates real evidence. This work is incomplete rather than `human_qa: pending`, `complete_candidate`, or a fabricated automated rejection. No 2003 production work was started, and no reader UI/player file was changed.
