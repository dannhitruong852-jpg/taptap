# Kaoyan C v4 Universal Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the accepted 2002 C-mode prototype into the universal production architecture for all 2000–2026 exam articles: article-driven casting, actor-specific calibration, actor-aware Chatterbox control, seamless sentence audio, real word timestamps, semantic Chinese synchronization, compact global player UI, and explicit three-layer QA.

**Architecture:** Preserve the existing static GitHub Pages reader and original English Chatterbox 0.1.7 renderer. Separate editorial intent from model parameters: Article Voice Profile and Director Intent describe what the article needs; Actor Calibration Profiles describe how each actor performs; Actor Adapter resolves those layers into Chatterbox controls. Generate one final audio file per sentence, then run forced alignment against the known source transcript and publish word timestamps. Keep v3 as the public fallback until the v4 candidate passes technical/browser verification and the user explicitly accepts Voice QA and C Direction QA.

**Tech Stack:** Python 3.11, JSON, original English `chatterbox-tts==0.1.7`, PyTorch/Torchaudio for offline CTC forced alignment, FFmpeg/libopus/libmp3lame, Node.js 22 built-in tests, Playwright/Chromium mobile browser tests, GitHub Actions matrix jobs, static HTML/CSS/ES modules, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-12-kaoyan-c-v4-universal-production-design.md`

## Global Constraints

- The highest C rule remains: “一个真正理解文章的美国人，坐在你面前，把这篇文章讲给你听。”
- Article personality chooses the actor. Actor 05 is a quality benchmark, never the default narrator.
- The same Director Intent may resolve to different Chatterbox parameters for different actors.
- Every production actor must have an actor-specific calibration profile before it can be selected by the production renderer.
- Editorial/content data must not own Chatterbox-specific `exaggeration`, `cfg_weight`, artificial pause, or post-generation tempo controls in the v4 path.
- Artificial silence is always 0. No `apad` and no fixed browser sentence delay.
- V4 must never call FFmpeg `atempo` to manufacture delivery/emotion.
- Runtime remains static: no browser TTS, no translation API, no paid AI API, no runtime alignment model.
- Final playback unit is one seamless sentence asset, except that the source production pipeline may still render semantic/role segments before server-side merging.
- Forced alignment happens only after final sentence audio exists; any regenerated sentence invalidates its prior timestamps.
- Readalong must use actual word timestamps. Percentage × token-count fallback is forbidden for v4 manifests.
- Existing translation-on-tap, native long-press selection, 6+ bilingual vocabulary marking, five-stop magnetic speed control, navigation, and scroll hide/restore must remain intact.
- V4 is a candidate namespace until human listening acceptance. CI success cannot promote Voice QA or C Direction QA by itself.
- 2002 must prove the architecture before the same system is expanded to 2000–2001 and 2003–2026.
- Existing v1/v2/v3 files remain available for reproducibility; v4 does not silently rewrite historical manifests.

---

### Task 1: Add v4 editorial, actor, and director contracts

**Files:** Create `voice-pipeline/c_v4_schema.py`, `voice-pipeline/config/director_intents.json`, `voice-pipeline/tests/test_c_v4_schema.py`, `content-pipeline/voice_profiles/2002.json`, `content-pipeline/direction/2002.json`; modify `.github/workflows/reader-pipeline-checks.yml`.

**Interfaces:**
```python
validate_article_voice_profile(profile: dict) -> list[str]
validate_director_plan(plan: dict) -> list[str]
validate_actor_calibration(profile: dict, *, require_eligible: bool = False) -> list[str]
```

- [ ] Write RED tests requiring Article Voice Profile fields, nonempty article arc, known Director Intent, and rejection of model-specific editorial fields. Example:
```python
self.assertIn('exaggeration is model-specific', validate_director_plan({'segments':[{'director_intent':'contrast','intensity':1,'exaggeration':.7}]}))
self.assertEqual(validate_article_voice_profile(valid_profile), [])
self.assertTrue(any('article_arc' in e for e in validate_article_voice_profile({**valid_profile,'article_arc':[]})))
```
- [ ] Run `PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_c_v4_schema.py -v`; verify RED because contracts do not exist.
- [ ] Implement the universal intents: `neutral_explain`, `warm_explain`, `serious_analysis`, `curious_probe`, `restrained_irony`, `narrative_build`, `action_acceleration`, `contrast`, `qualification`, `information_peak`, `punchline`, `conclusion_landing`, `quoted_character`.
- [ ] Reject `exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`, `rate`, and `pause_*_ms` from v4 Director Plan data.
- [ ] Encode all six 2002 Article Voice Profiles and reviewed segment directions. Preserve article-selected casting: cloze 04, Text1 05, Text2 08, Text3 01, Text4 09, translation 02, plus explicit dialogue roles.
- [ ] Run all content/voice/reader deterministic suites GREEN.
- [ ] Commit `feat: add universal C v4 editorial contracts`.

### Task 2: Build reusable actor calibration and audition infrastructure

**Files:** Create `voice-pipeline/calibration/audition_script.json`, `candidate_grid.py`, `render_auditions.py`, `build_audition_board.py`, profiles under `voice-pipeline/calibration/actors/{01,02,04,05,08,09,12,13}.json`, `voice-pipeline/tests/test_actor_calibration.py`, and `.github/workflows/c-v4-actor-auditions.yml`.

**Interfaces:**
```python
candidate_controls(actor_profile: dict, intent: str, intensity: int) -> list[dict]
build_actor_profile(actor_id: str, cast_cfg: dict, registry: dict) -> dict
```

- [ ] Write RED tests proving all eight current actors have separate profiles, actors start ineligible until listening approval, each tested intent has three bounded candidates, and every candidate has `artificial_pause_ms=0` and `post_tempo=false`.
- [ ] Run `PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_actor_calibration.py -v`; verify RED.
- [ ] Create one common ten-scene audition battery: explanation, rational analysis, warm conversation, story setup, turn/contrast, information emphasis, restrained humor, serious commentary, quotation/role, long complex sentence.
- [ ] Generate deterministic restrained/balanced/expressive candidate grids independently per actor/intent. V3 parameters may seed the search center but never become a global selected table.
- [ ] Reuse each actor’s own EARS source speaker and emotion references; never share reference voices between actors.
- [ ] Render auditions with original English Chatterbox 0.1.7 and record source/reference hash, controls, seed, duration, WPM, clipping, and audio hash.
- [ ] Build a static A/B/C audition board grouped actor → scene; include actor05/Text1 only as the named quality benchmark.
- [ ] Run the 8-actor GitHub Actions matrix and require technical success.
- [ ] **Human checkpoint:** user selects actor-specific candidates. Only then set `eligible:true`/`eligible_for`. These selections are one-time reusable calibration, not per-year tuning.
- [ ] Commit framework, then approved calibration profiles in a separate commit.

### Task 3: Add Actor Adapter; prohibit global performance control in v4

**Files:** Create `voice-pipeline/adapters/__init__.py`, `chatterbox_actor_adapter.py`, `voice-pipeline/tests/test_chatterbox_actor_adapter.py`; modify `voice-pipeline/render.py`.

**Interface:**
```python
resolve_controls(actor_id: str, director_intent: str, intensity: int, profile_dir: Path, *, require_eligible: bool = True) -> dict
```

- [ ] Write RED tests proving the same intent can resolve to different controls for actor05 and actor08; both remain zero-pause/no-post-tempo.
- [ ] Require unknown intent, missing selected calibration, and ineligible actor to hard-fail; v4 has no fallback to `emotions.json` or v3 `PERFORMANCE`.
- [ ] Implement actor-specific intensity bounds and return reference path, Chatterbox controls, profile hash, calibration version.
- [ ] Keep legacy `resolve_exaggeration()` only for old v1–v3 reproducibility. V4 never imports it for performance decisions.
- [ ] Include actor-profile hash/calibration ID in generation fingerprints so recalibrating one actor invalidates only affected audio.
- [ ] Run voice suite GREEN and commit `feat: resolve C v4 controls through actor adapters`.

### Task 4: Make voice-plan application generic and text-safe

**Files:** Create `voice-pipeline/apply_voice_plan.py`, `voice-pipeline/tests/test_apply_voice_plan.py`; modify `content-pipeline/build_2002.py`, `voice-pipeline/batch_schema.py`; keep v3 overlay/renderer intact for reproducibility.

**Interfaces:**
```python
apply_voice_plan(content: dict, article_profile: dict, director_plan: dict, cast_registry: dict) -> dict
load_year_voice_plan(year: int) -> tuple[dict, dict]
```

- [ ] RED-test all six 2002 units: voice overlay must not alter any `en`, `zh`, or `vocab` value.
- [ ] Test narrator comes from article casting and explicit role switches remain role-specific.
- [ ] Test v4 directed segments contain semantic director fields but not model parameters, rate, or physical pauses.
- [ ] Refactor canonical 2002 text generation so v4 does not depend on old model-control fields while preserving the old v3 reproducibility path.
- [ ] Implement generic `apply_voice_plan.py --year 2002` driven by data, not article-name conditionals.
- [ ] Run content/voice suites GREEN and commit.

### Task 5: Add generic v4 rendering, seamless merge, and candidate namespace

**Files:** Create `voice-pipeline/generate_c_v4.py`, `merge_c_v4.py`, `verify_c_v4.py`, plus corresponding unit tests. Candidate assets live under `kaoyan-reader-v1/audio/2002/v4/c-<article>/`.

**CLI:**
```bash
python voice-pipeline/generate_c_v4.py --year 2002 --article text2 --shard 0 --shards 3
python voice-pipeline/merge_c_v4.py --year 2002 --incoming /tmp/c-v4-audio
python voice-pipeline/verify_c_v4.py --year 2002 --root kaoyan-reader-v1
```

- [ ] RED-test deterministic sharding, adapter resolution, profile-fingerprint invalidation, retry isolation, zero artificial pause, no `atempo`/`apad`, and six-unit merge.
- [ ] Add static source tests that v4 contains no global `PERFORMANCE` table and no tempo/padding filter.
- [ ] Implement `Director Intent -> Actor Adapter -> Chatterbox` using original English Chatterbox 0.1.7 and deterministic seeds.
- [ ] Render semantic/role chunks as needed, then server-side merge to exactly one final Opus + MP3 per sentence. Browser never relays v4 microsegments.
- [ ] Manifest stores actor/profile/direction fingerprints and `qa:{technical:'passed',voice:'pending',c_direction:'pending'}`.
- [ ] Verifier checks codecs, hashes, decoding, source coverage, actor sequence and fingerprints; never promotes human QA.
- [ ] Run RED→GREEN and commit.

### Task 6: Implement real word-level forced alignment on final audio

**Files:** Create `voice-pipeline/alignment/__init__.py`, `normalize_transcript.py`, `ctc_align.py`, `align_manifests.py`, and tests `test_transcript_alignment.py`, `test_ctc_align.py`, `test_align_manifests.py`.

**Design:** Known source transcript is ground truth; this is not free ASR. Use CPU `torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H` emissions and our own deterministic CTC trellis/backtrack. Pin the alignment job to `torch==2.7.1` and `torchaudio==2.7.1`; do not rely on deprecated high-level alignment APIs.

**Output:**
```json
"words":[{"word":"If","char_start":0,"char_end":2,"start":0.000,"end":0.135,"score":0.98}]
```

- [ ] First write pure synthetic RED tests without model download: repeated letters, apostrophes, hyphens, number expansions, punctuation ignored acoustically while source offsets remain exact.
- [ ] Require exact source-word order, monotonic timestamps, and final end ≤ audio duration + 80ms.
- [ ] Implement reversible transcript normalization retaining original `char_start`/`char_end`.
- [ ] Implement testable CTC trellis/backtrack against supplied emissions.
- [ ] Implement runtime wrapper: decode final audio, obtain emissions, align, write `words` to v4 manifest.
- [ ] Alignment failure sets `alignment_status:failed` and blocks v4 candidate publication; no percentage fallback.
- [ ] Real-audio canary: short, long, dialogue, and hyphen/number sentence.
- [ ] Commit.

### Task 7: Add full Chinese semantic timing independent of vocabulary mappings

**Files:** Create `content-pipeline/semantic_spans.py`, `content-pipeline/semantic_spans/2002.json`, `content-pipeline/tests/test_semantic_spans.py`. Keep `kaoyan-reader-v1/content/2002/bilingual-highlights.json` exclusively for 6+ vocabulary meaning emphasis.

**Contract:** semantic groups reference inclusive/exclusive English word indexes and exact Chinese character spans.

- [ ] RED-test that every aligned English word belongs to exactly one ordered semantic group and every Chinese non-punctuation character is covered without rewriting `sentence.zh`.
- [ ] Test repeated/reordered translations; no proportional character math.
- [ ] Implement validator/loader only; do not auto-translate.
- [ ] Author/review semantic groups for all 91 2002 sentences at phrase/clause granularity.
- [ ] Implement `attach_semantic_times(groups, words) -> list[dict]`, deriving Chinese group times from English word intervals.
- [ ] Prove semantic timing and existing 6+ bilingual highlights coexist.
- [ ] Run content suite GREEN and commit.

### Task 8: Replace percentage readalong and shrink the global player ~30%

**Files:** Create `kaoyan-reader-v1/time-index.js`, `tests/word-timing.test.js`; modify `progress.js`, `bilingual-text.js`, `app.js`, `readalong.css`, `reader-controls.css`, `tests/progress.test.js`, `tests/player-compact.test.js`, `tests/reader-ux-browser.py`.

**Interfaces:**
```js
activeWordIndex(words, currentTime) -> number
readStateAtTime(words, currentTime) -> {readThrough, active}
activeChineseGroups(groups, currentTime) -> number[]
```

- [ ] RED-test a deliberately nonuniform 10-word timeline: if word 1 occupies 40% of audio, `t=3.0` must still select word 1 rather than word 4.
- [ ] Test boundaries, gaps, pause/resume, and all five playback rates. Do not rescale timestamps for playbackRate; `currentTime` is media timeline time.
- [ ] Link English `.read-token` elements to aligned source offsets without changing plain text.
- [ ] Render Chinese semantic groups with timing while retaining nested 6+ emphasis.
- [ ] Remove percentage×token behavior for v4; legacy percentage handling exists only for explicitly old manifests.
- [ ] Browser-test nonuniform timing with seeks at multiple times.
- [ ] Change the **global** mobile shell to `width:clamp(236px,62vw,420px)`. At 390px this is ~242px, ~31% narrower than the current ~350px shell.
- [ ] Keep 44×44 transport targets and 56×56 play target; reduce gaps/padding and compact/reflow speed controls instead of shrinking touch targets.
- [ ] Browser-test 320×700, 390×844, 412×915: centered, symmetric, no overflow, slider usable, text not materially obscured.
- [ ] Run `npm test` and `python kaoyan-reader-v1/tests/reader-ux-browser.py` GREEN; commit.

### Task 9: Add generic v4 CI with alignment and candidate preview

**Files:** Create `.github/workflows/generate-c-v4.yml`, `verify-c-v4-reader.yml`; modify `reader-pipeline-checks.yml`, `kaoyan-reader-v1/catalog.js`, and candidate selection in `app.js` as needed. Preserve `scripts/publish-reader.sh` non-force-push behavior.

**Pipeline:** contracts/content → actor references → sharded render → final merge → technical verify → forced alignment → semantic timing validation → unit tests → Chromium tests → candidate publish → public cache-busting verify.

- [ ] Add a workflow-contract test first. Require `workflow_dispatch.inputs.year`, generic year-aware renderer CLIs, calibration artifacts, alignment after merge, candidate-only publish.
- [ ] For 2002 use the proven 6 articles × 3 shards matrix.
- [ ] Separate pinned CPU Torch/Torchaudio alignment job and cache model downloads.
- [ ] Candidate is opt-in (`?audioVersion=v4`); normal visits stay on v3 until human promotion.
- [ ] Public smoke check requires all six v4 manifests, 91 sentence assets, 91 nonempty word arrays, zero alignment failures, both codecs, pending human QA.
- [ ] Run public mobile Chromium at 0.7/1/1.25/1.5/2 with timestamp readalong.
- [ ] Upload `2002-c-v4-candidate` artifact with manifests, QA/alignment reports, calibration hashes, screenshots/results.
- [ ] Commit.

### Task 10: Run 2002 mother-template acceptance and promote only after human approval

**Files:** Create `reports/qa/2002-c-v4-acceptance.json`; update reader version selection, handoff docs, and add a supersession note to `docs/superpowers/plans/2026-09-12-kaoyan-c-batch-production.md` for voice/director/readalong only.

- [ ] Require exactly 91 final sentence entries and 182 final files, zero hash/decode failures, all timestamps monotonic/source-covered, all Chinese semantic timing valid.
- [ ] Compare actor05/Text1 with its accepted benchmark to ensure the known-good article did not regress.
- [ ] Present all six articles with actor/rationale to the user. User judges naturalness, actor fit, article-level C arc and sentence failures.
- [ ] Rejected actor returns to calibration; regenerate only affected articles via fingerprint invalidation. Never change casting just to use a better-sounding but semantically wrong actor.
- [ ] Only explicit acceptance of both Voice QA and C Direction QA changes `c_status` from `candidate` to `accepted` and switches default reader v3→v4.
- [ ] Re-run public browser verification after promotion.
- [ ] Older multi-year plan keeps extraction/content scope, but v4 supersedes its actor performance, director parameterization, audio QA and readalong architecture.
- [ ] Commit promotion separately: `release: accept 2002 as the C v4 mother template`.

## Full Verification Before Any Completion Claim

```bash
PYTHONPATH=content-pipeline python -m unittest discover -s content-pipeline/tests -v
PYTHONPATH=voice-pipeline python -m unittest discover -s voice-pipeline/tests -v
cd kaoyan-reader-v1 && npm test
cd ..
python kaoyan-reader-v1/tests/reader-ux-browser.py
PYTHONPATH=voice-pipeline python voice-pipeline/verify_c_v4.py --year 2002 --root kaoyan-reader-v1
```

CI additionally proves all referenced actors are calibrated/eligible, six units remain article-selected, v4 uses no artificial silence/post-tempo, all 91 seamless sentences exist in both codecs, all 91 have post-merge word timestamps, Chinese timing matches unchanged translations, public mobile Chromium passes all five speed stops, and accepted v3 remains untouched until human acceptance.

## Expansion After 2002 Acceptance

Once 2002 is accepted, 2000–2001 and 2003–2026 reuse these modules unchanged. A new year adds only canonical content, Article Voice Profiles, Director Plans, semantic Chinese spans, and any genuinely new actor calibration needed by an uncovered article persona. Existing accepted actors use their saved calibration profiles and are not re-tuned per year.
