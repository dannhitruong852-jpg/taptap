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

**Files:**
- Create: `voice-pipeline/c_v4_schema.py`
- Create: `voice-pipeline/config/director_intents.json`
- Create: `voice-pipeline/tests/test_c_v4_schema.py`
- Create: `content-pipeline/voice_profiles/2002.json`
- Create: `content-pipeline/direction/2002.json`
- Modify: `.github/workflows/reader-pipeline-checks.yml`

**Interfaces:**

```python
validate_article_voice_profile(profile: dict) -> list[str]
validate_director_plan(plan: dict) -> list[str]
validate_actor_calibration(profile: dict, *, require_eligible: bool = False) -> list[str]
```

Editorial `Article Voice Profile` requires:

```json
{
  "year": 2002,
  "article_id": "text2",
  "domain": ["technology", "robotics"],
  "author_stance": "explain_with_contrast",
  "formality": "medium",
  "narrativity": "low",
  "humor_level": "subtle",
  "rationality_emotionality": "strongly_rational",
  "baseline_mood": "curious",
  "speaker_persona": "technology_explainer",
  "preferred_age_impression": "young_to_mid_adult",
  "preferred_gender_if_relevant": null,
  "dialogue_roles": ["dave_lavery"],
  "article_arc": ["familiar_tools", "robotics_progress", "common_sense_limit", "perception_problem"]
}
```

Director plan segment requires semantic intent, not model controls:

```json
{
  "sentence_id": "s03",
  "segment_id": "s03-02",
  "speaker_role": "narrator",
  "director_intent": "contrast",
  "intensity": 1,
  "information_focus": ["come close"],
  "contrast_target": "not yet vs approaching",
  "sentence_role_in_article_arc": "robotics_progress"
}
```

- [ ] Write failing schema tests first. Minimum assertions:

```python
self.assertIn('exaggeration is model-specific', validate_director_plan({
    'segments':[{'director_intent':'contrast','intensity':1,'exaggeration':.7}]
}))
self.assertEqual(validate_article_voice_profile(valid_profile), [])
self.assertTrue(any('article_arc' in e for e in validate_article_voice_profile({**valid_profile,'article_arc':[]})))
self.assertTrue(any('unknown director_intent' in e for e in validate_director_plan(plan_with_bad_intent)))
```

- [ ] Run and verify RED:

```bash
PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_c_v4_schema.py -v
```

Expected RED reason: module/config/profile files do not exist yet.

- [ ] Implement `director_intents.json` with the accepted universal intent vocabulary: `neutral_explain`, `warm_explain`, `serious_analysis`, `curious_probe`, `restrained_irony`, `narrative_build`, `action_acceleration`, `contrast`, `qualification`, `information_peak`, `punchline`, `conclusion_landing`, `quoted_character`.
- [ ] Implement strict validators. Reject Chatterbox parameter fields (`exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`), `pause_*_ms`, and `rate` from v4 editorial Director Plan data.
- [ ] Encode all six 2002 Article Voice Profiles and the existing reviewed sentence/segment direction as v4 intent data. Preserve current primary casting intent: cloze 04, Text1 05, Text2 08, Text3 01, Text4 09, translation 02; preserve explicit dialogue roles. Do not change this casting merely to favor actor 05.
- [ ] Add the v4 schema test to the normal reader pipeline path.
- [ ] Run full deterministic suites and verify GREEN:

```bash
PYTHONPATH=content-pipeline python -m unittest discover -s content-pipeline/tests -v
PYTHONPATH=voice-pipeline python -m unittest discover -s voice-pipeline/tests -v
cd kaoyan-reader-v1 && npm test
```

- [ ] Commit:

```bash
git add voice-pipeline/c_v4_schema.py voice-pipeline/config/director_intents.json voice-pipeline/tests/test_c_v4_schema.py content-pipeline/voice_profiles/2002.json content-pipeline/direction/2002.json .github/workflows/reader-pipeline-checks.yml
git commit -m "feat: add universal C v4 editorial contracts"
```

---

### Task 2: Build reusable actor calibration and audition infrastructure

**Files:**
- Create: `voice-pipeline/calibration/audition_script.json`
- Create: `voice-pipeline/calibration/candidate_grid.py`
- Create: `voice-pipeline/calibration/render_auditions.py`
- Create: `voice-pipeline/calibration/build_audition_board.py`
- Create: `voice-pipeline/calibration/actors/01.json`
- Create: `voice-pipeline/calibration/actors/02.json`
- Create: `voice-pipeline/calibration/actors/04.json`
- Create: `voice-pipeline/calibration/actors/05.json`
- Create: `voice-pipeline/calibration/actors/08.json`
- Create: `voice-pipeline/calibration/actors/09.json`
- Create: `voice-pipeline/calibration/actors/12.json`
- Create: `voice-pipeline/calibration/actors/13.json`
- Create: `voice-pipeline/tests/test_actor_calibration.py`
- Create: `.github/workflows/c-v4-actor-auditions.yml`

**Interfaces:**

```python
candidate_controls(actor_profile: dict, intent: str, intensity: int) -> list[dict]
build_actor_profile(actor_id: str, cast_cfg: dict, registry: dict) -> dict
```

`audition_script.json` must contain the same ten scene classes for every narrator-capable actor:

1. plain explanation
2. rational analysis
3. warm conversation
4. story setup
5. turn/contrast
6. information emphasis
7. restrained humor/punchline
8. serious commentary
9. quotation/role delivery
10. long complex sentence

Role-only actors 12/13 still run the common battery, but their production `eligible_for` list may be narrower.

Calibration profile structure:

```json
{
  "actor_id":"08",
  "source_speaker":"p023",
  "persona":"technology_explainer",
  "reference_variants":{"neutral":"actor08-neutral.wav"},
  "intents":{
    "curious_probe":{
      "reference_emotion":"curious",
      "selected_controls":null,
      "candidate_controls":[...],
      "human_status":"pending"
    }
  },
  "eligible":false,
  "eligible_for":[],
  "benchmark_relation":"must meet the Text1/actor05 naturalness floor"
}
```

- [ ] Write failing tests proving calibration is actor-specific:

```python
profiles = load_profiles()
self.assertEqual(set(profiles), {'01','02','04','05','08','09','12','13'})
self.assertFalse(profiles['08']['eligible'])
self.assertNotEqual(candidate_controls(profiles['05'],'warm_explain',1), [])
self.assertEqual(len(candidate_controls(profiles['08'],'curious_probe',1)), 3)
```

Also assert every candidate is within Chatterbox-safe bounds and always declares `artificial_pause_ms: 0` and `post_tempo: false`.

- [ ] Run RED:

```bash
PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_actor_calibration.py -v
```

- [ ] Implement a deterministic three-candidate grid per intent: restrained / balanced / expressive. The starting center may use the current v3 behavior as a *candidate only*, but selection is saved independently per actor. Do not encode one globally selected result.
- [ ] Reuse `prepare_2002_cast_references.py` for the actor’s own EARS source speaker and emotion-specific reference WAVs; do not share one actor’s reference with another actor.
- [ ] Implement `render_auditions.py` using original English Chatterbox 0.1.7. Each candidate artifact must record actor ID, source/reference hash, intent, controls, seed, duration, WPM, clipping, and audio hash.
- [ ] Implement `build_audition_board.py` to create a static comparison board grouped by actor → scene → candidate A/B/C. Include actor 05’s accepted Text1 behavior as the named quality benchmark, not as a candidate for unrelated article roles.
- [ ] Add GitHub Actions matrix across the eight currently materialized actors. Upload audition board and audio as an artifact; do not publish auditions as the active reader audio.
- [ ] Run unit tests GREEN. Trigger the audition workflow and require all clips to pass technical generation checks.
- [ ] **Human checkpoint:** present the audition board to the user. Record selections in each `voice-pipeline/calibration/actors/<id>.json`. An actor becomes `eligible:true` only after the user approves its naturalness for the relevant intent/persona. This human approval is one-time actor calibration and is reused across future years.
- [ ] Commit framework before selections:

```bash
git add voice-pipeline/calibration voice-pipeline/tests/test_actor_calibration.py .github/workflows/c-v4-actor-auditions.yml
git commit -m "feat: add reusable C v4 actor calibration auditions"
```

- [ ] Commit approved calibration profiles separately after the listening checkpoint:

```bash
git add voice-pipeline/calibration/actors
git commit -m "voice: approve calibrated C v4 actor profiles"
```

---

### Task 3: Add the Actor Adapter and remove global performance control from the v4 path

**Files:**
- Create: `voice-pipeline/adapters/__init__.py`
- Create: `voice-pipeline/adapters/chatterbox_actor_adapter.py`
- Create: `voice-pipeline/tests/test_chatterbox_actor_adapter.py`
- Modify: `voice-pipeline/render.py`

**Interface:**

```python
resolve_controls(
    actor_id: str,
    director_intent: str,
    intensity: int,
    profile_dir: Path,
    *,
    require_eligible: bool = True,
) -> dict
```

Returned dict:

```python
{
  'reference_path': Path(...),
  'exaggeration': 0.0,
  'cfg_weight': 0.0,
  'temperature': 0.8,
  'repetition_penalty': 1.2,
  'artificial_pause_ms': 0,
  'post_tempo': False,
  'actor_profile_sha256': '...',
  'calibration_version': '...'
}
```

- [ ] Write RED tests that prove the architecture, not just syntax:

```python
warm05 = resolve_controls('05','warm_explain',1,profiles,require_eligible=False)
warm08 = resolve_controls('08','warm_explain',1,profiles,require_eligible=False)
self.assertNotEqual((warm05['exaggeration'],warm05['cfg_weight']),
                    (warm08['exaggeration'],warm08['cfg_weight']))
self.assertEqual(warm05['artificial_pause_ms'],0)
self.assertFalse(warm05['post_tempo'])
```

Also require unknown intent, missing selected calibration, and ineligible actor to hard-fail in production mode; no fallback to `emotions.json` or v3 `PERFORMANCE` is permitted.

- [ ] Run RED:

```bash
PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_chatterbox_actor_adapter.py -v
```

- [ ] Implement the adapter. Actor-specific intensity behavior comes from each calibration profile; clamp only to that actor’s approved bounds.
- [ ] Keep old `resolve_exaggeration()` and legacy renderer APIs only where older v1/v2/v3 tests need reproducibility. Mark them legacy in comments; v4 must never import them for actor performance decisions.
- [ ] Add actor profile hash and selected calibration ID to generation fingerprints so changing calibration invalidates only affected caches.
- [ ] Run voice suite GREEN and commit:

```bash
PYTHONPATH=voice-pipeline python -m unittest discover -s voice-pipeline/tests -v
git add voice-pipeline/adapters voice-pipeline/render.py voice-pipeline/tests/test_chatterbox_actor_adapter.py
git commit -m "feat: resolve C v4 controls through actor adapters"
```

---

### Task 4: Make voice application generic and keep editorial text/model controls separated

**Files:**
- Create: `voice-pipeline/apply_voice_plan.py`
- Create: `voice-pipeline/tests/test_apply_voice_plan.py`
- Modify: `content-pipeline/build_2002.py`
- Modify: `voice-pipeline/batch_schema.py`
- Keep unchanged for reproducibility: `voice-pipeline/apply_2002_cast.py`, `voice-pipeline/generate_2002_v3.py`

**Interfaces:**

```python
apply_voice_plan(content: dict, article_profile: dict, director_plan: dict, cast_registry: dict) -> dict
load_year_voice_plan(year: int) -> tuple[dict, dict]
```

- [ ] Write a RED fidelity test using all six 2002 units. Snapshot before/after `en`, `zh`, and `vocab`; assert the voice overlay changes none of them.
- [ ] Test that narrator actor comes from the Article Voice Profile/casting decision and explicit role switches remain role-specific.
- [ ] Test v4 segments contain `director_intent`, `information_focus`, `intensity`, and role metadata but do **not** contain `exaggeration`, `cfg_weight`, `rate`, `pause_before_ms`, or `pause_after_ms` as editorial model instructions.
- [ ] Run RED:

```bash
PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_apply_voice_plan.py -v
```

- [ ] Refactor `build_2002.py` so its canonical text/vocabulary generation no longer requires physical pause/model-control fields for the v4 path. Preserve the old v3 build behavior behind the existing reproducibility route if old tests need it; do not silently break v3 manifests.
- [ ] Implement generic `apply_voice_plan.py --year 2002` with no hard-coded article names beyond data files.
- [ ] Update schema validation to accept the v4 directed representation while retaining older validator compatibility for v1–v3 tests.
- [ ] Run all content/voice tests GREEN and commit.

---

### Task 5: Add generic C v4 rendering, seamless merge, and candidate namespace

**Files:**
- Create: `voice-pipeline/generate_c_v4.py`
- Create: `voice-pipeline/merge_c_v4.py`
- Create: `voice-pipeline/verify_c_v4.py`
- Create: `voice-pipeline/tests/test_generate_c_v4.py`
- Create: `voice-pipeline/tests/test_merge_c_v4.py`
- Create: `voice-pipeline/tests/test_verify_c_v4.py`
- Modify: `kaoyan-reader-v1/catalog.js` only if needed to resolve an explicit candidate manifest URL; do not change default v3 behavior yet.

**CLI:**

```bash
python voice-pipeline/generate_c_v4.py --year 2002 --article text2 --shard 0 --shards 3
python voice-pipeline/merge_c_v4.py --year 2002 --incoming /tmp/c-v4-audio
python voice-pipeline/verify_c_v4.py --year 2002 --root kaoyan-reader-v1
```

**Candidate paths:**

```text
kaoyan-reader-v1/audio/2002/v4/c-cloze/
kaoyan-reader-v1/audio/2002/v4/c-text1/
...
kaoyan-reader-v1/audio/2002/v4/c-translation/
```

- [ ] Write RED tests for deterministic sharding, actor-adapter control resolution, fingerprint changes when actor calibration changes, retry isolation, no artificial pause, no `atempo`, and six-unit merge.
- [ ] Add a static source test asserting `generate_c_v4.py` contains no global `PERFORMANCE={` table and no `atempo`/`apad` filter.
- [ ] Implement generation with `Director Intent -> Actor Adapter -> Chatterbox`. Preserve original English Chatterbox 0.1.7 and deterministic seeds.
- [ ] Render semantic/role segments as needed, then server-side concatenate into exactly one final Opus and one final MP3 per sentence. Do not let the browser relay microsegments for v4.
- [ ] V4 final sentence manifest must include:

```json
{
  "c_mode_version":"v4-actor-calibrated",
  "actor_id":"08",
  "actor_sequence":["08","08"],
  "actor_profile_sha256":"...",
  "director_plan_sha256":"...",
  "artificial_pause_ms":0,
  "post_tempo":false,
  "qa":{"technical":"passed","voice":"pending","c_direction":"pending"}
}
```

- [ ] `verify_c_v4.py` must verify Opus+MP3 existence, hashes, decodability, source sentence coverage, actor sequence, profile/direction fingerprints, and candidate QA states. It must **not** convert pending human QA to accepted.
- [ ] Run RED→GREEN unit suites and commit.

---

### Task 6: Implement real word-level forced alignment on final audio

**Files:**
- Create: `voice-pipeline/alignment/__init__.py`
- Create: `voice-pipeline/alignment/normalize_transcript.py`
- Create: `voice-pipeline/alignment/ctc_align.py`
- Create: `voice-pipeline/alignment/align_manifests.py`
- Create: `voice-pipeline/tests/test_transcript_alignment.py`
- Create: `voice-pipeline/tests/test_ctc_align.py`
- Create: `voice-pipeline/tests/test_align_manifests.py`

**Design:** Use the known source transcript as ground truth. Alignment is not free-form ASR. A CPU CTC acoustic model (`torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H`) supplies emissions; our deterministic trellis/backtrack maps the known normalized transcript to time frames. Pin the alignment job to `torch==2.7.1` and `torchaudio==2.7.1`; do not depend on the deprecated high-level forced-alignment API.

**Output contract:**

```json
"words":[
  {"word":"If","char_start":0,"char_end":2,"start":0.000,"end":0.135,"score":0.98},
  {"word":"you","char_start":3,"char_end":6,"start":0.136,"end":0.230,"score":0.97}
]
```

- [ ] First write pure synthetic RED tests for CTC trellis/backtracking, with no model download. Test repeated letters, apostrophes, hyphenated source words, numbers expanded by existing `spoken_text()` rules, and punctuation ignored acoustically while preserving original character offsets.
- [ ] Test hard invariants:

```python
self.assertEqual([w['word'] for w in words], expected_source_words)
self.assertTrue(all(a['start'] <= a['end'] <= b['start'] for a,b in pairwise(words)))
self.assertLessEqual(words[-1]['end'], duration + 0.08)
```

- [ ] Run RED:

```bash
PYTHONPATH=voice-pipeline python -m unittest voice-pipeline/tests/test_transcript_alignment.py voice-pipeline/tests/test_ctc_align.py voice-pipeline/tests/test_align_manifests.py -v
```

- [ ] Implement transcript normalization as a reversible mapping: acoustic-normalized tokens always retain original source `char_start`/`char_end`.
- [ ] Implement CTC trellis/backtracking against supplied emissions; keep it testable without loading Torch.
- [ ] Implement a thin runtime model wrapper in `align_manifests.py` that decodes final sentence audio to the model sample rate, obtains emissions, runs alignment, and writes `words` into the v4 sentence manifest.
- [ ] Alignment failure must mark that sentence `alignment_status: failed` and block candidate publication. There is no percentage fallback in a v4 manifest.
- [ ] Run a local/CI canary on several real final sentence assets: one short, one long, one with dialogue, one with hyphenation/number expansion. Verify the exact normalized transcript and timing monotonicity.
- [ ] Commit.

---

### Task 7: Add full Chinese semantic timing independent of vocabulary difficulty mappings

**Files:**
- Create: `content-pipeline/semantic_spans.py`
- Create: `content-pipeline/semantic_spans/2002.json`
- Create: `content-pipeline/tests/test_semantic_spans.py`
- Keep: `kaoyan-reader-v1/content/2002/bilingual-highlights.json` for 6+ vocabulary emphasis only.

**Contract per sentence:**

```json
{
  "sentence_id":"s02",
  "groups":[
    {
      "en_word_start":0,
      "en_word_end":5,
      "zh_start":0,
      "zh_end":10,
      "zh_text":"你的幽默必须与听众相关"
    }
  ]
}
```

`en_word_start` is inclusive and `en_word_end` is exclusive against the final aligned English word list.

- [ ] Write RED tests requiring every aligned English word to belong to exactly one ordered semantic group and every Chinese non-punctuation character to be covered by an ordered Chinese span without rewriting `sentence.zh`.
- [ ] Test repeated/reordered translations explicitly; semantic spans are editorial mappings, not proportional character math.
- [ ] Implement validator/loader only; do not auto-translate or rewrite Chinese.
- [ ] Author/review semantic groups for all 91 2002 sentences using the existing accepted Chinese translations. Keep groups at natural phrase/clause granularity rather than one Chinese character per English word.
- [ ] Implement a function that combines semantic groups with final word timestamps to emit runtime `zh_timing`:

```python
attach_semantic_times(groups, words) -> list[dict]
```

Each Chinese group start/end comes from its referenced English word interval.
- [ ] Preserve `bilingual-highlights.json` as the separate occurrence-specific 6+ word ↔ Chinese meaning layer. Tests must prove both mappings can coexist.
- [ ] Run content tests GREEN and commit.

---

### Task 8: Replace percentage readalong with timestamp-driven bilingual readalong and shrink the global player ~30%

**Files:**
- Create: `kaoyan-reader-v1/time-index.js`
- Create: `kaoyan-reader-v1/tests/word-timing.test.js`
- Modify: `kaoyan-reader-v1/progress.js`
- Modify: `kaoyan-reader-v1/bilingual-text.js`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/readalong.css`
- Modify: `kaoyan-reader-v1/reader-controls.css`
- Modify: `kaoyan-reader-v1/tests/progress.test.js`
- Modify: `kaoyan-reader-v1/tests/player-compact.test.js`
- Modify: `kaoyan-reader-v1/tests/reader-ux-browser.py`

**Interfaces:**

```js
activeWordIndex(words, currentTime) -> number
readStateAtTime(words, currentTime) -> {readThrough, active}
activeChineseGroups(groups, currentTime) -> number[]
```

- [ ] Write RED unit tests showing why percentage mapping is forbidden. Example: a 10-word sentence where word 1 occupies 40% of duration must still highlight word 1 at `t=3.0`, not word 4.
- [ ] Add boundary tests: before first word, exact word start, exact word end, gaps between words, after last word, pause/resume, and all five playback rates. Do not rescale timestamp data for playbackRate: `HTMLMediaElement.currentTime` remains media timeline time.
- [ ] Modify English rendering so each `.read-token` can be linked to aligned `char_start`/`char_end`. Preserve the original plain text exactly.
- [ ] Modify Chinese rendering so semantic groups carry `data-start` / `data-end`; retain the existing 6+ `<strong class="vocab zh-vocab">` emphasis inside those timed spans.
- [ ] Remove v4’s use of `Math.floor(progress * tokens.length)` from `paintReadProgress`. Keep legacy percentage handling only when an explicitly old v1/v2/v3 manifest is selected.
- [ ] Browser acceptance must seek/scrub a deliberately nonuniform timestamp fixture and assert the active English token and Chinese semantic group match the manifest at multiple times.
- [ ] Change the **global** mobile `.player-shell`, not a 2002-specific selector. Target:

```css
.player-shell { width: clamp(236px, 62vw, 420px); }
```

At 390px viewport this is approximately 242px, about 31% narrower than the present ~350px shell.
- [ ] Keep transport touch targets at 44×44 and play at 56×56; reduce horizontal gaps/padding instead of shrinking accessibility targets. On narrow mobile, compact/reflow the speed row so the magnetic slider remains usable.
- [ ] Browser-test 320×700, 390×844 and 412×915 viewports: no horizontal overflow; shell centered; four control centers symmetric; slider draggable; text not materially obscured.
- [ ] Run:

```bash
cd kaoyan-reader-v1 && npm test
cd .. && python kaoyan-reader-v1/tests/reader-ux-browser.py
```

Verify GREEN and commit.

---

### Task 9: Add one generic v4 CI pipeline with alignment and candidate preview

**Files:**
- Create: `.github/workflows/generate-c-v4.yml`
- Create: `.github/workflows/verify-c-v4-reader.yml`
- Modify: `.github/workflows/reader-pipeline-checks.yml`
- Modify: `kaoyan-reader-v1/catalog.js`
- Modify: `kaoyan-reader-v1/app.js` only for explicit candidate selection
- Modify: `scripts/publish-reader.sh` only if needed to include candidate assets; do not change its non-force-push behavior.

**Workflow inputs:**

```yaml
workflow_dispatch:
  inputs:
    year:
      required: true
      default: '2002'
```

**Required stages:**

```text
prepare contracts/content
→ prepare actor references
→ render sharded v4 segments
→ merge seamless final sentences
→ technical verification
→ forced alignment
→ semantic timing attachment/validation
→ deterministic unit tests
→ real Chromium reader tests
→ publish candidate assets
→ public cache-busting verification
```

- [ ] Write workflow-contract tests or a Python/YAML checker before adding the workflow. Require `year` input, no hard-coded “2002 only” render API, actor-calibration artifacts, alignment after merge, and candidate-only publish.
- [ ] Adapt the proven v3 18-job matrix for 2002 (6 articles × 3 shards) while making renderer CLIs year-aware.
- [ ] Use a separate alignment job/environment with pinned CPU Torch/Torchaudio. Cache model downloads.
- [ ] Candidate preview must be opt-in, e.g. `?audioVersion=v4`; normal visits remain on accepted v3 until promotion.
- [ ] Public candidate smoke check must fetch all six v4 manifests with cache-busting and assert 91 sentence assets, 91 nonempty word timing arrays, zero alignment failures, Opus+MP3 paths, and `qa.voice == pending` / `qa.c_direction == pending` until user acceptance.
- [ ] Re-run real Chromium against the public candidate URL and verify timestamp readalong at normal speed plus 0.7/1/1.25/1.5/2 rates.
- [ ] Upload one final `2002-c-v4-candidate` artifact containing manifests, QA reports, alignment summaries, actor calibration hashes, and browser screenshots/results.
- [ ] Commit.

---

### Task 10: Run 2002 mother-template acceptance and promote only after human approval

**Files:**
- Create: `reports/qa/2002-c-v4-acceptance.json`
- Modify: `kaoyan-reader-v1/content/catalog.json` or the version-selection config used by the reader
- Modify: `docs/handoff/2026-09-12-2002-acceptance-scope.md`
- Modify: `docs/handoff/2026-09-12-kaoyan-project-handoff.md`
- Modify: `docs/superpowers/plans/2026-09-12-kaoyan-c-batch-production.md` with a supersession note for voice/director/readalong only.

**Acceptance state:**

```json
{
  "year":2002,
  "c_version":"v4-actor-calibrated",
  "technical_complete":true,
  "alignment_complete":true,
  "reader_complete":true,
  "voice_qa":"pending_user_acceptance",
  "c_direction_qa":"pending_user_acceptance",
  "c_status":"candidate"
}
```

- [ ] Run all 2002 technical verification. Exact required result: 91 final sentence entries, 182 final sentence files (Opus + MP3), no missing hashes/decodes, all timestamps monotonic and source-covered, all semantic timing valid.
- [ ] Compare actor 05/Text1 against its accepted benchmark to ensure v4 did not regress the known-good article while changing architecture.
- [ ] Present the six-article candidate to the user with actor identities and article rationale. Ask the user to judge naturalness, actor/article fit, article-level C arc, and any sentence-level failures. CI is not a substitute for this step.
- [ ] If an actor is rejected, return to Task 2/3 for that actor calibration profile and regenerate only affected articles through fingerprint invalidation. Do not change article casting merely to use a better-sounding but semantically wrong actor.
- [ ] Only when both `voice_qa` and `c_direction_qa` are explicitly accepted, change `c_status` to `accepted` and switch the default reader from v3 to v4.
- [ ] Re-run public-browser verification after promotion.
- [ ] Add a supersession note to the older multi-year plan: PDF extraction/content-scope tasks remain valid, but C v4 spec/plan supersede its actor performance, director parameterization, audio QA, and readalong architecture.
- [ ] Commit promotion separately:

```bash
git add reports/qa/2002-c-v4-acceptance.json kaoyan-reader-v1/content/catalog.json docs/handoff docs/superpowers/plans/2026-09-12-kaoyan-c-batch-production.md
git commit -m "release: accept 2002 as the C v4 mother template"
```

---

## Full Verification Commands Before Any Completion Claim

Run fresh after the final implementation commit:

```bash
PYTHONPATH=content-pipeline python -m unittest discover -s content-pipeline/tests -v
PYTHONPATH=voice-pipeline python -m unittest discover -s voice-pipeline/tests -v
cd kaoyan-reader-v1 && npm test
cd ..
python kaoyan-reader-v1/tests/reader-ux-browser.py
PYTHONPATH=voice-pipeline python voice-pipeline/verify_c_v4.py --year 2002 --root kaoyan-reader-v1
```

The GitHub Actions candidate workflow must additionally prove:

- all actor profiles referenced by production are calibrated/eligible;
- six 2002 units use article-selected actors, not one default actor;
- no v4 render path uses artificial silence or post-tempo;
- all 91 seamless sentence assets exist in both codecs;
- all 91 sentences have valid word timestamps generated after final audio merge;
- semantic Chinese timing validates against the unchanged Chinese text;
- all reader unit tests pass;
- public candidate Chromium tests pass at mobile sizes and all five speed stops;
- active v3 remains untouched until human acceptance.

## Expansion After 2002 Acceptance

Once 2002 is accepted, expansion to 2000–2001 and 2003–2026 reuses these modules unchanged. For a new year, production should add only: canonical article content, Article Voice Profiles, Director Plans, semantic Chinese spans, and any genuinely new actor calibration profile required by an uncovered article persona. Existing accepted actors are called through their saved calibration profiles; they are not re-tuned per year.
