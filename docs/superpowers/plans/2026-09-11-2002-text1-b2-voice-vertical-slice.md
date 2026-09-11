# 2002 Text 1 B2 Voice Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current browser `speechSynthesis` placeholder for 2002 Text 1 with pre-generated, scene-aware B2 Chatterbox audio that supports sentence-level and intra-sentence actor changes, local QA, static Opus playback, and zero runtime TTS API calls.

**Architecture:** Keep the existing static GitHub Pages UI, but move article/director data into structured JSON and make the browser consume a static audio manifest. An offline Python pipeline renders each sentence segment with the original English Chatterbox model, applies rate/Opus post-processing, runs local QA, retries failed segments, and writes only approved assets to the site. The first vertical slice uses actor slots 05, 12, and 13 only; the full 15-actor registry remains available for later years.

**Tech Stack:** Static HTML/CSS/ES modules, Node.js built-in `node:test`, Python 3.11, `chatterbox-tts`, PyTorch/torchaudio, FFmpeg/libopus, local `faster-whisper` ASR, local speaker embedding model, JSON manifests.

**Spec:** `docs/superpowers/specs/2026-09-11-kaoyan-b2-voice-system-design.md`

## Global Constraints

- B2 mode: one article may change actors by scene, and one sentence may change actors between narration and dialogue.
- American English is primary; British English is used only where the article context calls for it.
- English learning accuracy outranks dramatic effect: pronunciation, lexical stress, syntax, and pauses must stay clear.
- First-generation library has 15 actor slots; the 2002 Text 1 pilot uses only actor 05, actor 12, and actor 13.
- Shared emotions are exactly: `neutral`, `warm`, `lively`, `serious`, `curious`, `ironic`, `tense`, `emotional`.
- Intensity values are exactly `0`, `1`, `2`; intensity `2` requires explicit textual justification.
- Chatterbox is the only TTS engine in the production generation path; do not add Kokoro, Google TTS, or paid per-character/per-minute APIs.
- Runtime must not perform TTS generation, AI director analysis, or paid API requests.
- Generated audio is precomputed and served as static Opus assets.
- QA covers text fidelity, speaker consistency, technical audio quality, pace/pause plausibility, and cinematic-naturalness review.
- Cinematic-naturalness references are: `The Intern` for general naturalness, `Modern Family` for light/dialogue/humor, and `The Newsroom` for argument/commentary. They are style references only, not cloning targets.
- Do not add background music, environmental sound, or unrelated UI redesign in this phase.
- Existing player behavior must remain: play/pause, previous/next, replay, active sentence highlight, 0.85x/1x/1.15x speed controls, and down-scroll hide/up-scroll reveal.
- The pilot is successful only when it plays reliably on vivo/Android and replaying audio does not create any TTS API cost.

---

## File Structure

### Existing files to modify

- `kaoyan-reader-v1/app.js` — DOM controller; remove browser speech synthesis and delegate to the static-audio player.
- `kaoyan-reader-v1/index.html` — update copy/status text from “device speech” to pre-generated expressive audio.
- `kaoyan-reader-v1/styles.css` — only small state/status changes if required by the new audio player.
- `kaoyan-reader-v1/data.js` — retire after the structured content JSON is live; do not keep two independent truth sources.

### New browser/runtime files

- `kaoyan-reader-v1/package.json` — zero-dependency Node test harness with `type: module`.
- `kaoyan-reader-v1/content/2002/text1.json` — canonical article, sentence, vocabulary, scene, actor, emotion, intensity, and rate data.
- `kaoyan-reader-v1/audio/2002/text1/manifest.json` — generated segment paths, durations, fingerprints, QA state, and generation version.
- `kaoyan-reader-v1/playback.js` — pure queue/state helpers for multi-segment sentence playback.
- `kaoyan-reader-v1/audio-player.js` — thin `HTMLAudioElement` sequencer; no TTS logic.
- `kaoyan-reader-v1/tests/content-schema.test.js` — validates the 2002 Text 1 B2 data contract.
- `kaoyan-reader-v1/tests/playback.test.js` — validates queue order, sentence boundaries, and speed behavior.

### New offline generation files

- `voice-pipeline/requirements.txt` — local-only generation/QA dependencies.
- `voice-pipeline/config/actors.json` — all 15 actor slot definitions and base rates.
- `voice-pipeline/config/emotions.json` — maps the 8 emotion/intensity combinations to Chatterbox parameters.
- `voice-pipeline/references/sources.json` — provenance, license/permission note, version, and local path for every reference clip.
- `voice-pipeline/render.py` — Chatterbox renderer, deterministic fingerprinting, retry seed control, WAV-to-Opus post-processing.
- `voice-pipeline/qa.py` — local QA checks and machine-readable QA report.
- `voice-pipeline/generate_text1.py` — orchestrates the 24-segment 2002 Text 1 pilot and writes the runtime manifest.
- `voice-pipeline/tests/test_config.py` — validates 15 actors and emotion constraints.
- `voice-pipeline/tests/test_fingerprint.py` — validates cache/fingerprint behavior.
- `voice-pipeline/tests/test_qa.py` — validates deterministic QA helpers without loading large models.

### Generated pilot assets

- `kaoyan-reader-v1/audio/2002/text1/s01-a.opus` through the required segment set, including `s09-a`, `s09-b`, `s10-a`, `s10-b`, `s10-c`.
- `voice-pipeline/reports/2002-text1-qa.json` — complete per-segment QA outcome.

---

### Task 1: Add a zero-dependency test harness and structured B2 content data

**Files:**
- Create: `kaoyan-reader-v1/package.json`
- Create: `kaoyan-reader-v1/content/2002/text1.json`
- Create: `kaoyan-reader-v1/tests/content-schema.test.js`
- Modify later: `kaoyan-reader-v1/data.js` only after the new source is proven

**Interfaces:**
- Consumes: the exact 21 English sentences, Chinese translations, and vocabulary entries currently in `kaoyan-reader-v1/data.js`.
- Produces: canonical JSON with `article` and `sentences[]`; every sentence contains `id`, `en`, `zh`, `vocab`, and `segments[]`; every segment contains `id`, `text`, `scene_id`, `speaker_role`, `actor_id`, `emotion`, `intensity`, and `rate`.

- [ ] **Step 1: Add the Node test harness**

```json
{
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test tests/*.test.js"
  }
}
```

- [ ] **Step 2: Write the failing content-schema test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const doc = JSON.parse(fs.readFileSync(new URL('../content/2002/text1.json', import.meta.url)));
const allowedEmotions = new Set(['neutral','warm','lively','serious','curious','ironic','tense','emotional']);

test('2002 Text 1 has 21 complete sentences and valid B2 segments', () => {
  assert.equal(doc.article.year, 2002);
  assert.equal(doc.article.section, 'Text 1');
  assert.equal(doc.sentences.length, 21);
  for (const sentence of doc.sentences) {
    assert.ok(sentence.en.length > 0);
    assert.ok(sentence.zh.length > 0);
    assert.ok(sentence.segments.length > 0);
    for (const segment of sentence.segments) {
      assert.match(segment.id, /^s\d{2}-[a-z]$/);
      assert.ok(['05','12','13'].includes(segment.actor_id));
      assert.ok(allowedEmotions.has(segment.emotion));
      assert.ok([0,1,2].includes(segment.intensity));
      assert.ok(segment.rate >= 0.80 && segment.rate <= 1.05);
    }
  }
});

test('sentences 9 and 10 use intra-sentence B2 role switching', () => {
  assert.deepEqual(doc.sentences[8].segments.map(s => s.actor_id), ['12','05']);
  assert.deepEqual(doc.sentences[9].segments.map(s => s.actor_id), ['13','05','13']);
  assert.equal(doc.sentences[9].segments[2].emotion, 'ironic');
  assert.equal(doc.sentences[9].segments[2].intensity, 2);
});
```

- [ ] **Step 3: Run the test and verify RED**

Run from `kaoyan-reader-v1/`:

```bash
npm test
```

Expected: FAIL because `content/2002/text1.json` does not exist yet.

- [ ] **Step 4: Create the canonical JSON and migrate all 21 existing sentence values exactly**

Use the current `data.js` English, Chinese, and vocabulary data without rewriting it. Apply this exact B2 casting rule:

```json
{
  "article": {
    "year": 2002,
    "section": "Text 1",
    "primary_actor_id": "05",
    "accent": "en-US"
  },
  "sentences": [
    {
      "id": 9,
      "en": "“Who is that?” the new arrival asked St. Peter.",
      "zh": "“那是谁？”新来的人问圣彼得。",
      "vocab": [],
      "segments": [
        {"id":"s09-a","text":"Who is that?","scene_id":"heaven-story","speaker_role":"new-arrival","actor_id":"12","emotion":"curious","intensity":2,"rate":0.90},
        {"id":"s09-b","text":"the new arrival asked St. Peter.","scene_id":"heaven-story","speaker_role":"narrator","actor_id":"05","emotion":"neutral","intensity":1,"rate":0.95}
      ]
    },
    {
      "id": 10,
      "en": "“Oh, that’s God,” came the reply, “but sometimes he thinks he’s a doctor.”",
      "zh": "“哦，那是上帝，”圣彼得回答，“不过有时候，他会以为自己是个医生。”",
      "vocab": [],
      "segments": [
        {"id":"s10-a","text":"Oh, that’s God,","scene_id":"heaven-story","speaker_role":"st-peter","actor_id":"13","emotion":"neutral","intensity":1,"rate":0.91},
        {"id":"s10-b","text":"came the reply,","scene_id":"heaven-story","speaker_role":"narrator","actor_id":"05","emotion":"neutral","intensity":0,"rate":0.95},
        {"id":"s10-c","text":"but sometimes he thinks he’s a doctor.","scene_id":"heaven-story","speaker_role":"st-peter","actor_id":"13","emotion":"ironic","intensity":2,"rate":0.88}
      ]
    }
  ]
}
```

For sentences 1-8 and 11-21, use one segment each with actor `05`; the heaven-story setup may use `lively` intensity `1`, while explanatory prose stays `neutral`/`warm` intensity `0-1`. This yields exactly 24 rendered segments: 19 single-segment sentences + 2 segments for sentence 9 + 3 segments for sentence 10.

- [ ] **Step 5: Run the content test and verify GREEN**

```bash
npm test
```

Expected: PASS for both content-schema tests.

- [ ] **Step 6: Commit**

```bash
git add kaoyan-reader-v1/package.json kaoyan-reader-v1/content/2002/text1.json kaoyan-reader-v1/tests/content-schema.test.js
git commit -m "feat: add structured B2 content for 2002 text1"
```

---

### Task 2: Build a deterministic static-audio playback queue

**Files:**
- Create: `kaoyan-reader-v1/playback.js`
- Create: `kaoyan-reader-v1/tests/playback.test.js`
- Create: `kaoyan-reader-v1/audio/2002/text1/manifest.json` initially with test fixture paths only

**Interfaces:**
- Consumes: `sentences[]` from content JSON and `segments` map from the audio manifest.
- Produces: `buildSentenceQueue(sentence, manifest)`, `applySpeed(baseRate, userSpeed)`, and `nextSentenceIndex(index, delta, length)`.

- [ ] **Step 1: Write failing queue tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSentenceQueue, applySpeed, nextSentenceIndex } from '../playback.js';

const sentence10 = {
  id: 10,
  segments: [{id:'s10-a'},{id:'s10-b'},{id:'s10-c'}]
};
const manifest = {
  segments: {
    's10-a': {path:'./audio/2002/text1/s10-a.opus'},
    's10-b': {path:'./audio/2002/text1/s10-b.opus'},
    's10-c': {path:'./audio/2002/text1/s10-c.opus'}
  }
};

test('buildSentenceQueue preserves intra-sentence actor segment order', () => {
  assert.deepEqual(buildSentenceQueue(sentence10, manifest).map(x => x.id), ['s10-a','s10-b','s10-c']);
});

test('user playback speed multiplies generated segment rate without leaving safe browser range', () => {
  assert.equal(applySpeed(1, 0.85), 0.85);
  assert.equal(applySpeed(1, 1.15), 1.15);
});

test('sentence navigation clamps at article bounds', () => {
  assert.equal(nextSentenceIndex(0, -1, 21), 0);
  assert.equal(nextSentenceIndex(20, 1, 21), 20);
});
```

- [ ] **Step 2: Run and verify RED**

```bash
npm test
```

Expected: FAIL because `playback.js` is missing.

- [ ] **Step 3: Implement the minimal pure helpers**

```js
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

export function buildSentenceQueue(sentence, manifest) {
  return sentence.segments.map(segment => ({
    ...segment,
    ...manifest.segments[segment.id]
  }));
}

export function applySpeed(baseRate, userSpeed) {
  return Number(clamp(baseRate * userSpeed, 0.5, 2).toFixed(2));
}

export function nextSentenceIndex(index, delta, length) {
  if (length <= 0) return 0;
  return clamp(index + delta, 0, length - 1);
}
```

- [ ] **Step 4: Run and verify GREEN**

```bash
npm test
```

Expected: all Node tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/playback.js kaoyan-reader-v1/tests/playback.test.js kaoyan-reader-v1/audio/2002/text1/manifest.json
git commit -m "feat: add static B2 playback queue"
```

---

### Task 3: Replace `speechSynthesis` with an `HTMLAudioElement` sequencer

**Files:**
- Create: `kaoyan-reader-v1/audio-player.js`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/index.html`
- Test: `kaoyan-reader-v1/tests/playback.test.js`

**Interfaces:**
- Consumes: `buildSentenceQueue()`, browser `Audio`, content JSON, audio manifest.
- Produces: `createAudioPlayer({createAudio, onSegmentStart, onSentenceEnd, onError})` with methods `playSentence(queue, playbackRate)`, `pause()`, `resume()`, `stop()`, and `setPlaybackRate(rate)`.

- [ ] **Step 1: Add a failing sequencer test with a fake audio object**

```js
class FakeAudio {
  constructor(src) { this.src = src; this.playbackRate = 1; this.paused = true; }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
  finish() { this.onended?.(); }
}

test('sequencer advances through all segments before ending a sentence', async () => {
  const created = [];
  const ended = [];
  const player = createAudioPlayer({
    createAudio: src => { const a = new FakeAudio(src); created.push(a); return a; },
    onSentenceEnd: () => ended.push(true)
  });
  player.playSentence([
    {id:'s10-a', path:'a.opus'},
    {id:'s10-b', path:'b.opus'},
    {id:'s10-c', path:'c.opus'}
  ], 1);
  assert.equal(created[0].src, 'a.opus');
  created[0].finish();
  assert.equal(created[1].src, 'b.opus');
  created[1].finish();
  assert.equal(created[2].src, 'c.opus');
  created[2].finish();
  assert.equal(ended.length, 1);
});
```

- [ ] **Step 2: Run and verify RED**

```bash
npm test
```

Expected: FAIL because `createAudioPlayer` is missing.

- [ ] **Step 3: Implement the sequencer and keep all state local to the player**

The player must create a fresh `Audio` object per segment, set `preload='auto'`, set `playbackRate`, advance only from `onended`, and surface `error` through `onError`. `stop()` must pause the active element, clear callbacks, and invalidate the current generation so stale `onended` callbacks cannot advance a newer request.

- [ ] **Step 4: Run and verify GREEN**

```bash
npm test
```

Expected: all tests PASS.

- [ ] **Step 5: Rewire `app.js`**

Replace:

```js
const synth = window.speechSynthesis;
```

and all `SpeechSynthesisUtterance` calls with:

```js
const content = await fetch('./content/2002/text1.json').then(r => r.json());
const manifest = await fetch('./audio/2002/text1/manifest.json').then(r => r.json());
const audioPlayer = createAudioPlayer({
  createAudio: src => new Audio(src),
  onSegmentStart: () => setPlaying(true, false),
  onSentenceEnd: handleSentenceEnd,
  onError: () => {
    setPlaying(false, false);
    statusEl.textContent = '音频暂时不可用';
  }
});
```

Keep existing sentence click, previous/next, replay, active-card highlighting, scroll behavior, Chinese/vocabulary toggles, and player visibility logic.

- [ ] **Step 6: Update user-facing copy**

Change the footer/status wording so it no longer claims the browser/device is generating speech. Use wording equivalent to “本篇使用预生成表演式英语音频；播放时不调用 TTS 接口”。

- [ ] **Step 7: Static smoke test**

Run:

```bash
python3 -m http.server 8000 -d kaoyan-reader-v1
```

Open the page and verify the page renders 21 sentence cards even if the initial manifest points to fixture/missing audio. Verify clicking a sentence produces a controlled “音频暂时不可用” state rather than a JavaScript crash.

- [ ] **Step 8: Commit**

```bash
git add kaoyan-reader-v1/app.js kaoyan-reader-v1/audio-player.js kaoyan-reader-v1/index.html kaoyan-reader-v1/tests/playback.test.js
git commit -m "feat: switch reader to static audio playback"
```

---

### Task 4: Define the 15-actor registry, emotion parameters, and reference-pack contract

**Files:**
- Create: `voice-pipeline/config/actors.json`
- Create: `voice-pipeline/config/emotions.json`
- Create: `voice-pipeline/references/sources.json`
- Create: `voice-pipeline/tests/test_config.py`
- Create: `voice-pipeline/requirements.txt`

**Interfaces:**
- Consumes: actor definitions and eight-state performance system from the approved spec.
- Produces: stable `actor_id`, `base_rate`, `accent`, and reference-pack versioning used by the renderer and fingerprint function.

- [ ] **Step 1: Write the failing actor/emotion validation test**

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_actor_and_emotion_registry():
    actors = json.loads((ROOT / 'config/actors.json').read_text())['actors']
    emotions = json.loads((ROOT / 'config/emotions.json').read_text())['emotions']
    assert [a['id'] for a in actors] == [f'{i:02d}' for i in range(1, 16)]
    assert sum(a['accent'] == 'en-US' for a in actors) == 13
    assert sum(a['accent'] == 'en-GB' for a in actors) == 2
    assert set(emotions) == {'neutral','warm','lively','serious','curious','ironic','tense','emotional'}
    assert actors[4]['id'] == '05'
    assert actors[11]['id'] == '12'
    assert actors[12]['id'] == '13'
```

- [ ] **Step 2: Run and verify RED**

```bash
python3 -m unittest discover -s voice-pipeline/tests -p 'test_*.py'
```

Expected: FAIL because the config files do not exist.

- [ ] **Step 3: Create actor and emotion configs**

Actor 05 is the clear, rhythmic presentation voice; actor 12 is the young male dialogue role; actor 13 is the older male role. Celebrity names remain style notes only; the production reference clips must have recorded provenance and permission/license suitable for local processing. `sources.json` must record `actor_id`, `variant`, `source_url`, `license_or_permission`, `local_path`, and `reference_pack_version`.

Use these initial Chatterbox parameter anchors for the original English model:

```json
{
  "emotions": {
    "neutral":   {"exaggeration":0.50,"cfg_weight":0.50},
    "warm":      {"exaggeration":0.55,"cfg_weight":0.45},
    "lively":    {"exaggeration":0.65,"cfg_weight":0.40},
    "serious":   {"exaggeration":0.42,"cfg_weight":0.55},
    "curious":   {"exaggeration":0.60,"cfg_weight":0.45},
    "ironic":    {"exaggeration":0.66,"cfg_weight":0.36},
    "tense":     {"exaggeration":0.72,"cfg_weight":0.34},
    "emotional": {"exaggeration":0.75,"cfg_weight":0.32}
  }
}
```

Intensity mapping is deterministic: `0` subtracts `0.08` from exaggeration, `1` uses the base value, `2` adds `0.10`; clamp to `[0.25, 0.90]`. Do not change `cfg_weight` by intensity in the pilot.

- [ ] **Step 4: Create the dependency list**

```text
chatterbox-tts
faster-whisper
numpy
soundfile
resemblyzer
```

FFmpeg is a system dependency and must be checked separately with `ffmpeg -version`.

- [ ] **Step 5: Run and verify GREEN**

```bash
python3 -m unittest discover -s voice-pipeline/tests -p 'test_*.py'
```

Expected: config test PASS.

- [ ] **Step 6: Commit**

```bash
git add voice-pipeline/config voice-pipeline/references/sources.json voice-pipeline/requirements.txt voice-pipeline/tests/test_config.py
git commit -m "feat: define B2 actor and emotion registries"
```

---

### Task 5: Implement deterministic Chatterbox rendering and Opus encoding

**Files:**
- Create: `voice-pipeline/render.py`
- Create: `voice-pipeline/tests/test_fingerprint.py`
- Modify: `voice-pipeline/references/sources.json`

**Interfaces:**
- Consumes: one segment dict, actor config, emotion config, a local reference clip, `reference_pack_version`, and `model_version`.
- Produces: one Opus file plus metadata `{fingerprint, seed, duration_ms, actor_id, emotion, intensity, rate}`.

- [ ] **Step 1: Write the failing fingerprint test**

```python
from render import generation_fingerprint

def test_generation_fingerprint_changes_only_when_render_inputs_change():
    base = dict(text='Who is that?', actor_id='12', reference_pack_version='1', emotion='curious', intensity=2, rate=0.90, model_version='chatterbox-english')
    a = generation_fingerprint(**base)
    b = generation_fingerprint(**base)
    assert a == b
    changed = dict(base, rate=0.91)
    assert generation_fingerprint(**changed) != a
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=voice-pipeline python3 -m unittest voice-pipeline/tests/test_fingerprint.py
```

Expected: FAIL because `render.py` is missing.

- [ ] **Step 3: Implement the fingerprint and pure parameter resolver first**

```python
import hashlib, json

def generation_fingerprint(**fields):
    payload = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
```

Implement `resolve_exaggeration(emotion_cfg, intensity)` with the exact intensity rule from Task 4.

- [ ] **Step 4: Run unit tests and verify GREEN before loading any model**

```bash
PYTHONPATH=voice-pipeline python3 -m unittest discover -s voice-pipeline/tests -p 'test_*.py'
```

Expected: PASS.

- [ ] **Step 5: Add a runtime preflight command**

`render.py --preflight` must print and exit nonzero if any required component is missing: Python 3.11-compatible environment, `ffmpeg`, reference file readability, and Chatterbox import. It must report whether `cuda`, `mps`, or `cpu` will be used.

- [ ] **Step 6: Implement original English Chatterbox generation**

Use the official API shape:

```python
from chatterbox.tts import ChatterboxTTS
import torchaudio as ta

model = ChatterboxTTS.from_pretrained(device=device)
wav = model.generate(
    text,
    audio_prompt_path=reference_path,
    exaggeration=exaggeration,
    cfg_weight=cfg_weight,
)
ta.save(temp_wav, wav, model.sr)
```

Set `torch.manual_seed(seed)` before each generation. Keep one loaded model per batch; do not reload it per segment.

- [ ] **Step 7: Post-process rate and encode Opus**

For a segment rate `r`, encode with FFmpeg using pitch-preserving `atempo=r` and libopus:

```bash
ffmpeg -y -i segment.wav -filter:a "atempo=0.95" -c:a libopus -b:a 48k segment.opus
```

Clamp runtime generation rate to the content contract `[0.80, 1.05]`. Browser user speed remains a separate playback multiplier.

- [ ] **Step 8: Source the three pilot reference packs**

Acquire three clean English reference clips matching actor slots 05, 12, and 13. Each must be single-speaker, low-reverb, 10-25 seconds, and recorded in `sources.json` with provenance and license/permission note. Do not commit a clip whose provenance is unknown. The clips should match the approved voice archetypes; they do not need to be recognizable celebrity clones.

- [ ] **Step 9: Run one real generation probe**

Generate `s09-a` and verify:

```bash
python3 voice-pipeline/render.py --segment s09-a --content kaoyan-reader-v1/content/2002/text1.json --out /tmp/s09-a.opus
ffprobe -v error -show_entries format=duration -of default=nw=1 /tmp/s09-a.opus
```

Expected: a nonzero-duration Opus file with no renderer exception.

- [ ] **Step 10: Commit source/config/code, but not unreviewed generated pilot audio yet**

```bash
git add voice-pipeline/render.py voice-pipeline/tests/test_fingerprint.py voice-pipeline/references/sources.json
git commit -m "feat: add deterministic Chatterbox renderer"
```

---

### Task 6: Implement local five-part QA and retry classification

**Files:**
- Create: `voice-pipeline/qa.py`
- Create: `voice-pipeline/tests/test_qa.py`

**Interfaces:**
- Consumes: expected segment text, rendered Opus/WAV, reference clip, actor/emotion/intensity metadata.
- Produces: `{status, checks, retry_recommended, cinematic_review_required}` where `status` is `pass`, `retry`, or `manual_review`.

- [ ] **Step 1: Write failing deterministic QA tests**

```python
from qa import normalized_wer, pace_check, needs_cinematic_review

def test_normalized_wer_ignores_case_and_punctuation():
    assert normalized_wer("Who is that?", "who is that") == 0.0

def test_pace_check_flags_extreme_speed():
    assert pace_check(word_count=30, duration_seconds=4.0)['pass'] is False
    assert pace_check(word_count=30, duration_seconds=12.0)['pass'] is True

def test_cinematic_review_targets_strong_or_character_performance():
    assert needs_cinematic_review('ironic', 2, 'st-peter') is True
    assert needs_cinematic_review('neutral', 0, 'narrator') is False
```

- [ ] **Step 2: Run and verify RED**

```bash
PYTHONPATH=voice-pipeline python3 -m unittest voice-pipeline/tests/test_qa.py
```

Expected: FAIL because `qa.py` is missing.

- [ ] **Step 3: Implement deterministic checks**

Use these pilot thresholds:

- Text fidelity: normalized WER `<= 0.08`; any missing/altered numeral or obvious proper-name mismatch forces `retry`.
- Pace: 105-190 spoken words/minute after applying segment rate; outside range forces `retry`.
- Technical peak: reject clipping when absolute PCM peak is `>= 0.999` for more than 0.1% of samples.
- Leading/trailing near-silence: each must be `<= 0.60 s`; larger values trigger trimming once, then re-check.
- Speaker consistency: cosine similarity to the actor reference embedding must be `>= 0.65`; lower values force `retry`.
- Cinematic review: always required for intensity `2`, any non-narrator role, or emotions `ironic`, `tense`, `emotional`.

Use local `faster-whisper` English ASR for transcription and a local speaker embedding model for similarity. No cloud QA API is permitted.

- [ ] **Step 4: Run deterministic tests and verify GREEN**

```bash
PYTHONPATH=voice-pipeline python3 -m unittest discover -s voice-pipeline/tests -p 'test_*.py'
```

Expected: PASS.

- [ ] **Step 5: Run one integration QA on the `s09-a` probe**

```bash
python3 voice-pipeline/qa.py --audio /tmp/s09-a.opus --expected "Who is that?" --actor 12
```

Expected: JSON output containing all five QA categories and either `pass`, `retry`, or `manual_review`; it must never silently skip a category.

- [ ] **Step 6: Commit**

```bash
git add voice-pipeline/qa.py voice-pipeline/tests/test_qa.py
git commit -m "feat: add local audio QA gates"
```

---

### Task 7: Batch-render and cache the complete 24-segment 2002 Text 1 pilot

**Files:**
- Create: `voice-pipeline/generate_text1.py`
- Create/update: `voice-pipeline/reports/2002-text1-qa.json`
- Create/update: `kaoyan-reader-v1/audio/2002/text1/*.opus`
- Create/update: `kaoyan-reader-v1/audio/2002/text1/manifest.json`

**Interfaces:**
- Consumes: content JSON, actor/emotion config, reference packs, renderer, QA.
- Produces: 24 approved static segment files and one manifest consumable by the browser.

- [ ] **Step 1: Write the orchestrator around stable renderer/QA interfaces**

For each segment:

```python
for attempt in range(3):
    seed = base_seed + attempt
    render_result = render_segment(segment, seed=seed)
    qa_result = evaluate_segment(segment, render_result)
    if qa_result['status'] in {'pass', 'manual_review'}:
        break
else:
    raise RuntimeError(f"segment failed after 3 attempts: {segment['id']}")
```

A `manual_review` result is allowed into the candidate build but must be listed prominently in the QA report and is not marked fully approved until the final vivo/Android listening pass.

- [ ] **Step 2: Implement fingerprint cache skipping**

Before rendering, compute the fingerprint from:

```text
text + actor_id + reference_pack_version + emotion + intensity + rate + model_version
```

If the manifest already contains the same fingerprint and QA status is approved, skip generation. A changed field regenerates only that segment.

- [ ] **Step 3: Run the full batch**

```bash
python3 voice-pipeline/generate_text1.py
```

Expected: exactly 24 Opus assets, no missing manifest entries, and a QA report with 24 segment records.

- [ ] **Step 4: Validate files mechanically**

```bash
find kaoyan-reader-v1/audio/2002/text1 -name '*.opus' | wc -l
python3 - <<'PY'
import json
m=json.load(open('kaoyan-reader-v1/audio/2002/text1/manifest.json'))
assert len(m['segments']) == 24
assert all(v['path'].endswith('.opus') for v in m['segments'].values())
print('manifest-ok')
PY
```

Expected: `24` and `manifest-ok`.

- [ ] **Step 5: Commit approved/candidate pilot assets and manifest**

```bash
git add voice-pipeline/generate_text1.py voice-pipeline/reports/2002-text1-qa.json kaoyan-reader-v1/audio/2002/text1
git commit -m "feat: generate 2002 text1 B2 pilot audio"
```

---

### Task 8: Integrate final assets, remove obsolete browser-TTS data path, and verify deployment

**Files:**
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/index.html`
- Delete: `kaoyan-reader-v1/data.js` after confirming no imports remain
- Test: all Node and Python tests

**Interfaces:**
- Consumes: final 24-segment manifest and Opus assets.
- Produces: one public GitHub Pages pilot that plays the B2 audio without any runtime TTS API.

- [ ] **Step 1: Add a regression check that browser TTS is gone**

Run:

```bash
grep -R "speechSynthesis\|SpeechSynthesisUtterance\|Google" kaoyan-reader-v1 --include='*.js' --include='*.html'
```

Expected before cleanup: legacy hits may remain. Expected after cleanup: no runtime TTS hits; historical/spec text outside the runtime directory does not count.

- [ ] **Step 2: Remove the old `data.js` import/source of truth**

After `app.js` is fully reading `content/2002/text1.json`, delete `data.js` and ensure there are no remaining imports of it.

- [ ] **Step 3: Run the complete automated suite**

```bash
cd kaoyan-reader-v1 && npm test
cd .. && PYTHONPATH=voice-pipeline python3 -m unittest discover -s voice-pipeline/tests -p 'test_*.py'
```

Expected: all tests PASS.

- [ ] **Step 4: Run a local HTTP smoke test**

```bash
python3 -m http.server 8000 -d kaoyan-reader-v1
```

Verify sentence 10 plays `s10-a -> s10-b -> s10-c` without skipping, player speed controls alter browser playback rate, previous/next operate on sentence boundaries rather than segment boundaries, and down-scroll/up-scroll player visibility still works.

- [ ] **Step 5: Verify no runtime network dependency beyond static site assets**

Browser network requests during playback should be limited to the page files, content JSON, manifest JSON, and `.opus` assets under the same static site. There must be no TTS/AI API request.

- [ ] **Step 6: Commit final integration**

```bash
git add -A kaoyan-reader-v1
git commit -m "feat: ship 2002 text1 B2 static audio reader"
```

- [ ] **Step 7: Publish the same tested commit to the existing Pages branch**

Move/update the current `gh-pages` deployment to the exact verified commit rather than rebuilding from an unrelated branch state.

- [ ] **Step 8: Verify the deployed site**

Open:

```text
https://dannhitruong852-jpg.github.io/taptap/kaoyan-reader-v1/
```

Verify the page loads, 21 sentence cards render, tapping sentence 9 and sentence 10 plays the correct multi-actor segment sequence, speed controls work, and the existing scroll-hide/reveal behavior still works on vivo/Android.

- [ ] **Step 9: Final acceptance gate**

The user listens to the pilot on vivo/Android. Any complaint about pronunciation, actor fit, pacing, or cinematic naturalness is translated into a segment-level director/reference change; regenerate only the affected fingerprints, not the whole article.

---

## Self-Review Results

- Spec coverage: B2 scene/intra-sentence switching, 15-actor registry, 8 emotions x 3 intensities, Chatterbox-only generation, pre-generated Opus, five-part QA, fingerprint cache, 2002 Text 1 pilot, vivo/Android acceptance, and zero runtime TTS API are all mapped to tasks.
- Scope: limited to the first vertical slice; it does not attempt 2002 full-year or 20+ years of audio.
- Placeholder scan: no `TBD`, `TODO`, “implement later”, or unspecified error-handling steps remain.
- Interface consistency: browser segment IDs, actor IDs, manifest keys, fingerprint inputs, and QA states are defined once and reused consistently.
- YAGNI check: no database, server, authentication, background music, cloud TTS, or new web framework is introduced.
