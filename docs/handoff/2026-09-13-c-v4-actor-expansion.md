# C v4 actor expansion automated gate

This phase replaces the audition-board decision for **new** actors with a deterministic, fail-closed gate. It does not reinterpret the eight historical human approvals.

## Policy

Every actor must supply A/B/C renders for all ten director intents. The gate checks transcript WER, actor/reference identity, licensed reference and audio hashes, fingerprint freshness, decodability evidence, alignment and bounded monotonic words, 105–190 WPM, clipping, edge and internal silence, speaker similarity, automated naturalness and intent fidelity, and the immutable `artificial_pause_ms=0` / `post_tempo=false` rules. Candidate ranking is deterministic: mean naturalness/intent/speaker score, distance from the middle of the accepted pace band, then B/A/C as a stable tie-break. Any uncovered intent rejects the whole actor.

Inherited numeric limits come from the existing B2 voice design (WER 0.08, clipping 0.1%, edge silence 0.60 s, speaker similarity 0.65, and the existing `qa.py` 105–190 WPM production band). C v4 automation explicitly versions the previously human-only replacements: internal silence at 1.20 s and machine-produced naturalness and director-intent scores at 0.75. Changes require a new policy ID and tests; they must never be relaxed to admit an actor.

Automated admissions must record `approval_method: automated_c_v4_qa` and `qa_policy`. Existing approvals truthfully retain `approval_method: human_listening`.

## 2026-09-13 result

Actors 03, 06, 07, 10, 11, 14, and 15 fail closed. The baseline does not contain their actor calibration profiles, licensed same-speaker reference provenance, or generated A/B/C evidence. Consequently none can cover all ten intents and none enters production. Their rejected records are explicit in `production_approvals.json`; the production pool remains 01, 02, 04, 05, 08, 09, 12, and 13 (eight actors).

This is not `human_qa: pending` or `complete_candidate`: it is a final automated rejection on missing mandatory evidence. A later retry must add genuine source provenance and generated evidence, then pass the same policy. No 2003 production work was started, and no reader UI/player file was changed.
