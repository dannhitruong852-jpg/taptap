# C-Mode Batch Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the 2002 Text 1 pilot into a fail-soft, multi-year production pipeline that extracts only cloze/reading/Part B/translation prose, enriches it under the C-mode director rules, generates Chatterbox audio in parallel, and progressively publishes the results to the existing GitHub Pages reader.

**Architecture:** Keep GitHub Pages static at runtime. Offline/local preprocessing turns each annual PDF into canonical article JSON, then GitHub Actions performs deterministic validation and sharded Chatterbox rendering. Content and audio are fingerprinted so reruns skip completed work; failures are isolated per article/segment and summarized instead of blocking unrelated years.

**Tech Stack:** Python 3.11, pdftotext/Poppler, JSON, Node.js built-in tests, Chatterbox TTS, FFmpeg/libopus, GitHub Actions matrix jobs, static HTML/CSS/ES modules.

**Spec:** `docs/superpowers/specs/2026-09-12-kaoyan-c-batch-production-design.md`

## Global Constraints

- C mode is the highest-level voice rule: understanding-first, natural American conversational pace, natural prosody in every sentence, micro-contrast at least once in any 3-sentence window, strong acting only with textual evidence.
- Preserve the 15-actor registry; actor selection is automatic and does not require per-article user confirmation.
- Runtime must not call TTS, translation, or paid AI APIs.
- Production content scope is only cloze prose, Reading Part A article prose, Part B article prose, and Translation English prose; exclude questions, answer choices, directions, and all Writing content.
- Chatterbox remains the only production TTS engine.
- Single article/segment failures must not stop unrelated years or articles.
- Existing vivo/Android static reader controls and scroll behavior remain intact.

---

### Task 1: Add canonical batch schemas and C-mode validators

**Files:**
- Create: `voice-pipeline/batch_schema.py`
- Create: `voice-pipeline/tests/test_batch_schema.py`
- Create: `voice-pipeline/config/c_mode.json`

**Interfaces:**
- Produces `validate_article(article) -> list[str]`, `validate_c_mode_density(sentences) -> list[str]`, and one canonical C-mode config.

- [ ] Write failing tests covering allowed section types, required article/sentence/segment fields, actor IDs 01-15, speed limits, and the any-3-sentence micro/strong contrast rule.
- [ ] Run `python -m unittest voice-pipeline/tests/test_batch_schema.py -v` and verify RED.
- [ ] Implement the minimal schema validator and C-mode config.
- [ ] Run the test and the existing Python unit suite; verify GREEN.
- [ ] Commit.

### Task 2: Build PDF text extraction and section slicing

**Files:**
- Create: `content-pipeline/extract_exam.py`
- Create: `content-pipeline/normalize.py`
- Create: `content-pipeline/tests/test_extract_exam.py`
- Create: `content-pipeline/fixtures/section-samples.json`

**Interfaces:**
- `extract_sections(text, year) -> dict[str, list[str]]`
- `normalize_prose(text) -> str`

- [ ] Write failing fixture tests for pre-2010 English I layout, 2010+ English II layout, duplicate answer-key pages, and exclusion of Writing.
- [ ] Verify RED.
- [ ] Implement section anchors and conservative slicing; never infer missing prose silently.
- [ ] Verify GREEN on fixtures and run a dry extraction report for every available year.
- [ ] Commit.

### Task 3: Add cloze reconstruction support

**Files:**
- Create: `content-pipeline/cloze.py`
- Create: `content-pipeline/tests/test_cloze.py`

**Interfaces:**
- `fill_cloze(article_text, answers, choices) -> str`
- Emits unresolved blanks explicitly rather than guessing.

- [ ] Write failing tests for numeric blanks, OCR variants such as `空 1 空`, and answer-key reconstruction.
- [ ] Verify RED.
- [ ] Implement deterministic answer insertion where answer data exists.
- [ ] If a year lacks a trustworthy answer key, retain extraction as `needs_answer_key` and continue other sections.
- [ ] Verify GREEN and commit.

### Task 4: Add canonical article builder and director fields

**Files:**
- Create: `content-pipeline/build_articles.py`
- Create: `content-pipeline/director_c.py`
- Create: `content-pipeline/tests/test_director_c.py`

**Interfaces:**
- `build_article(...) -> dict`
- `direct_article(article) -> dict`

- [ ] Write failing tests for discourse-function detection, prosody focus, micro-contrast density, stable narrator, dialogue role switching, and 1-4 actor default cap.
- [ ] Verify RED.
- [ ] Implement rule-based deterministic director defaults that encode C-mode behavior; strong acting requires evidence.
- [ ] Verify GREEN and commit.

### Task 5: Generalize runtime reader from one article to a catalog

**Files:**
- Create: `kaoyan-reader-v1/content/catalog.json`
- Modify: `kaoyan-reader-v1/app.js`
- Modify: `kaoyan-reader-v1/index.html`
- Create: `kaoyan-reader-v1/catalog.js`
- Create: `kaoyan-reader-v1/tests/catalog.test.js`

**Interfaces:**
- `loadCatalog()` and article selection by year/type/article ID.

- [ ] Write failing catalog/navigation tests.
- [ ] Verify RED with `npm test`.
- [ ] Implement year/type/article selectors without changing the established sentence-card/player behavior.
- [ ] Verify GREEN and commit.

### Task 6: Generalize Chatterbox batch renderer

**Files:**
- Create: `voice-pipeline/generate_batch.py`
- Modify: `voice-pipeline/render.py`
- Create: `voice-pipeline/tests/test_generate_batch.py`

**Interfaces:**
- `select_shard(items, shard_index, shard_count)`
- fingerprint cache, retry seeds, per-segment fail-soft status.

- [ ] Write failing tests for deterministic sharding, cache hits, retry isolation, and manifest merge behavior.
- [ ] Verify RED.
- [ ] Implement minimal batch orchestration using the existing Chatterbox renderer.
- [ ] Verify GREEN and commit.

### Task 7: Add parallel GitHub Actions generation/publish workflow

**Files:**
- Create: `.github/workflows/generate-kaoyan-batch.yml`
- Create: `.github/workflows/publish-kaoyan-batch.yml`

**Interfaces:**
- Matrix/shard generation artifacts and one validated publish stage.

- [ ] Add workflow validation tests/scripts first.
- [ ] Configure cached Python/model dependencies and shard inputs.
- [ ] Each shard uploads audio + status JSON even when individual segments fail.
- [ ] Publish job merges only validated manifests, commits assets to `kaoyan-reader-v1`, then updates `gh-pages`.
- [ ] Trigger a limited multi-article canary and verify success before expanding the matrix.
- [ ] Commit.

### Task 8: Produce all available years and run final QA

**Files:**
- Generate: `kaoyan-reader-v1/content/<year>/*.json`
- Generate: `kaoyan-reader-v1/audio/<year>/**`
- Generate: `reports/extraction/*.json`
- Generate: `reports/qa/*.json`
- Modify: `kaoyan-reader-v1/content/catalog.json`

- [ ] Run extraction across every available exam PDF; preserve per-year reports.
- [ ] Enrich only successfully extracted articles; unresolved cloze answer keys remain isolated, not guessed.
- [ ] Run schema/C-mode/content QA.
- [ ] Trigger sharded Chatterbox generation.
- [ ] Retry failed segments and merge valid outputs.
- [ ] Verify static catalog/content/audio completeness and GitHub Pages deployment.
- [ ] Report exact passed/retried/isolated counts; do not claim unresolved items as complete.
