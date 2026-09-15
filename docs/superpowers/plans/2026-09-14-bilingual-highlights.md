# Unified Bilingual Highlights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Chinese level-6+ vocabulary emphasis a reviewed, year-neutral production contract for 2002-2006 now and all future years.

**Architecture:** Store canonical reviewed mappings per year under `content-pipeline/curated/bilingual-highlights/<year>.json`; compile them into `kaoyan-reader-v1/content/<year>/bilingual-highlights.json`; load mappings through the article selection loader instead of a hardcoded 2002 promise; validate exact English/Chinese offsets and coverage before publication.

**Tech Stack:** Python 3.11 content pipeline, static JSON, vanilla ES modules, Node `node:test`.

**Spec:** `docs/superpowers/specs/2026-09-14-reader-bilingual-highlights-persistent-audio-cache-design.md`

## Global Constraints

- Runtime must not use AI, fuzzy translation, dictionary lookup, or year-specific rendering branches.
- Existing English, Chinese translation wording, vocabulary levels, C-mode direction, actor assignment, and audio must remain unchanged.
- Only vocab occurrences with `level >= 6` are required for bilingual emphasis.
- Invalid/stale mapping offsets must fail build-time QA.
- Required coverage is 100% except explicit reviewed exceptions with a non-empty reason.

---

### Task 1: Year-neutral bilingual mapping loader

**Files:**
- Modify: `kaoyan-reader-v1/catalog.js`
- Modify: `kaoyan-reader-v1/app.js`
- Test: `kaoyan-reader-v1/tests/catalog.test.js`
- Test: `kaoyan-reader-v1/tests/reader-interaction.test.js`

**Interfaces:**
- Produces: `bilingualHighlightsPath(entry) -> string`
- Produces: `createSelectionLoader(...)(entry) -> {content, manifest, bilingual}` where `bilingual` is the year mapping document or `{version:1,articles:{}}` on 404.
- Consumes: catalog entry `year` and `id`.

- [ ] **Step 1: Write the failing loader test**

Add a test asserting that a 2003 entry requests `./content/2003/bilingual-highlights.json`, returns its mapping document, and does not request `./content/2002/bilingual-highlights.json`.

```js
const entry={id:'2003-text1',year:2003,content:'./content/2003/c/text1.json',manifest:'./audio/2003/v4/c-text1/manifest.json'};
const requested=[];
const fetcher=async path=>{requested.push(path);return {ok:true,json:async()=>path.includes('bilingual-highlights')?{version:1,articles:{text1:{s01:[]}}}:path.includes('manifest')?{sentences:{},segments:{}}:{article_id:'text1',sentences:[]}}};
const loaded=await createSelectionLoader(fetcher,{audioVersion:'v4'})(entry);
assert.equal(requested.includes('./content/2003/bilingual-highlights.json'),true);
assert.deepEqual(loaded.bilingual.articles.text1.s01,[]);
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd kaoyan-reader-v1 && npm test -- --test-name-pattern='bilingual'`
Expected: FAIL because the loader does not request or return year mappings.

- [ ] **Step 3: Implement the minimal loader change**

Add:

```js
export function bilingualHighlightsPath(entry){
  return `./content/${entry.year}/bilingual-highlights.json`;
}
```

Update `createSelectionLoader` to fetch content, manifest, and mapping in parallel; mapping 404/error degrades to `{version:1,articles:{}}`.

Update `app.js` so `openArticle()` reads `loaded.bilingual`, indexes `articles[loaded.content.article_id] || {}`, and removes the global hardcoded 2002 bilingual promise.

- [ ] **Step 4: Run focused reader tests**

Run: `cd kaoyan-reader-v1 && npm test -- --test-name-pattern='bilingual|selection'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add kaoyan-reader-v1/catalog.js kaoyan-reader-v1/app.js kaoyan-reader-v1/tests/catalog.test.js kaoyan-reader-v1/tests/reader-interaction.test.js
git commit -m "feat: load bilingual highlights by exam year"
```

---

### Task 2: Canonical mapping validator and compiler

**Files:**
- Create: `content-pipeline/bilingual_highlights.py`
- Modify: `content-pipeline/build_curated_year.py`
- Create: `content-pipeline/tests/test_bilingual_highlights.py`
- Modify: `content-pipeline/tests/test_build_curated_year.py`

**Interfaces:**
- Produces: `validate_bilingual_highlights(year_doc: dict, article_docs: list[dict]) -> dict`
- Produces QA fields: `required_occurrences`, `mapped_occurrences`, `reviewed_exceptions`, `errors`.
- Compiler input: `content-pipeline/curated/bilingual-highlights/<year>.json`.
- Compiler output: `kaoyan-reader-v1/content/<year>/bilingual-highlights.json` and `reports/bilingual-highlights/<year>.json`.

- [ ] **Step 1: Write failing validator tests**

Cover exact English match, exact Chinese match, nonexistent sentence, out-of-range span, missing level-6+ occurrence, and explicit exception with non-empty reason.

```python
def test_missing_level6_occurrence_is_an_error():
    article={"article_id":"text1","sentences":[{"id":"s01","en":"A difficult term.","zh":"一个难词。","vocab":[{"word":"difficult","level":6,"start":2,"end":11}]}]}
    mapping={"version":1,"year":2003,"articles":{"text1":{"s01":[]}},"exceptions":[]}
    report=validate_bilingual_highlights(mapping,[article])
    assert report["mapped_occurrences"] == 0
    assert any(e["code"]=="unmapped_required_occurrence" for e in report["errors"])
```

- [ ] **Step 2: Run validator tests and verify RED**

Run: `PYTHONPATH=voice-pipeline:content-pipeline python -m unittest content-pipeline/tests/test_bilingual_highlights.py -v`
Expected: FAIL because module/function does not exist.

- [ ] **Step 3: Implement strict validator**

Mapping schema:

```json
{
  "version": 1,
  "year": 2003,
  "articles": {
    "text1": {
      "s03": [
        {"en_start":77,"en_end":86,"en_text":"espionage","zh_spans":[{"start":12,"end":16,"text":"间谍活动"}]}
      ]
    }
  },
  "exceptions": [
    {"article_id":"text1","sentence_id":"s08","en_start":10,"en_end":20,"reason":"translation restructures the concept without a clean contiguous Chinese span"}
  ]
}
```

Validator must key required occurrences by `(article_id, sentence_id, start, end)`, verify exact source slices, and require every level-6+ occurrence to be either mapped exactly once or covered by an exact exception.

- [ ] **Step 4: Integrate into `build_curated_year.py`**

After `docs, rows = build_year(source)`, load the year mapping source, validate against `docs`, raise `ValueError` when report errors are non-empty, then write the canonical mapping and QA report.

- [ ] **Step 5: Run content-pipeline tests**

Run: `PYTHONPATH=voice-pipeline:content-pipeline python -m unittest content-pipeline/tests/test_bilingual_highlights.py content-pipeline/tests/test_build_curated_year.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add content-pipeline/bilingual_highlights.py content-pipeline/build_curated_year.py content-pipeline/tests/test_bilingual_highlights.py content-pipeline/tests/test_build_curated_year.py
git commit -m "feat: validate bilingual vocabulary mappings"
```

---

### Task 3: Migrate 2002 to the unified mapping contract

**Files:**
- Create: `content-pipeline/curated/bilingual-highlights/2002.json`
- Create/replace generated: `kaoyan-reader-v1/content/2002/bilingual-highlights.json`
- Test: `kaoyan-reader-v1/tests/playback.test.js` or `reader-interaction.test.js`

**Interfaces:**
- Consumes existing: `kaoyan-reader-v1/content/2002/bilingual-highlights.json` legacy semantics.
- Produces unified mapping keyed by article id expected by `loaded.content.article_id`.

- [ ] **Step 1: Add a failing 2002 compatibility test**

Assert a known 2002 mapped occurrence renders `<strong class="vocab zh-vocab"` after going through the new year-neutral loader.

- [ ] **Step 2: Verify RED against the not-yet-migrated loader/data combination**

Run: `cd kaoyan-reader-v1 && npm test -- --test-name-pattern='2002.*bilingual'`
Expected: FAIL until the source mapping is copied/migrated to the canonical source path and article keys match the loader contract.

- [ ] **Step 3: Copy the reviewed 2002 occurrence mappings into the canonical source file**

Preserve every existing exact `en_start/en_end/en_text/zh_spans` entry byte-for-byte in meaning and offsets; add `year: 2002` and `exceptions: []` only if validation proves full required coverage, otherwise add explicit reviewed exceptions with reasons.

- [ ] **Step 4: Run 2002 validator and reader tests**

Run the Python validator test for year 2002, then `cd kaoyan-reader-v1 && npm test`.
Expected: PASS with existing 2002 visuals intact.

- [ ] **Step 5: Commit**

```bash
git add content-pipeline/curated/bilingual-highlights/2002.json kaoyan-reader-v1/content/2002/bilingual-highlights.json kaoyan-reader-v1/tests
git commit -m "data: migrate 2002 bilingual highlights to unified contract"
```

---

### Task 4: Author reviewed 2003-2006 bilingual mappings

**Files:**
- Create: `content-pipeline/curated/bilingual-highlights/2003.json`
- Create: `content-pipeline/curated/bilingual-highlights/2004.json`
- Create: `content-pipeline/curated/bilingual-highlights/2005.json`
- Create: `content-pipeline/curated/bilingual-highlights/2006.json`
- Generated: `kaoyan-reader-v1/content/<year>/bilingual-highlights.json`
- Generated QA: `reports/bilingual-highlights/<year>.json`

**Interfaces:**
- Required occurrence source: compiled article sentence `vocab` entries with `level >= 6`.
- Mapping output must use exact sentence offsets and exact Chinese slices.

- [ ] **Step 1: Compile each year and emit a deterministic missing-occurrence report**

Run for 2003-2006 and collect every required occurrence as `(year, article_id, sentence_id, en_start, en_end, en_text, meaning, zh)`.

- [ ] **Step 2: Author occurrence-specific Chinese spans**

For each required occurrence, select the faithful contiguous Chinese phrase in the existing `zh` string and store its exact offsets/text. Do not rewrite the translation. If no faithful contiguous span exists, record an exception with a concrete reason.

- [ ] **Step 3: Run strict coverage QA year by year**

Run:

```bash
for year in 2003 2004 2005 2006; do python content-pipeline/build_curated_year.py --year "$year"; done
```

Expected for every year: validator reports `errors=[]` and `required_occurrences == mapped_occurrences + reviewed_exceptions`.

- [ ] **Step 4: Spot-check rendering of all four years**

Add/extend a Node test that loads one mapped sentence from each year and asserts the exact Chinese phrase is wrapped by `zh-vocab` while surrounding Chinese remains unchanged.

- [ ] **Step 5: Commit**

```bash
git add content-pipeline/curated/bilingual-highlights/2003.json content-pipeline/curated/bilingual-highlights/2004.json content-pipeline/curated/bilingual-highlights/2005.json content-pipeline/curated/bilingual-highlights/2006.json kaoyan-reader-v1/content reports/bilingual-highlights kaoyan-reader-v1/tests
git commit -m "data: add reviewed bilingual highlights for 2003-2006"
```

---

### Task 5: Make bilingual coverage a publication gate

**Files:**
- Modify: `.github/workflows/reader-tests.yml`
- Modify: `.github/workflows/publish-kaoyan-batch.yml`

**Interfaces:**
- Consumes: `reports/bilingual-highlights/<year>.json`.
- Gate condition: no errors and complete required coverage for every published year that uses the unified contract.

- [ ] **Step 1: Add a failing CI contract assertion**

In the workflow validation script, assert each report has `errors == []` and complete coverage. Verify locally/CI that the check fails when a fixture mapping is removed in the validator test.

- [ ] **Step 2: Add the gate to reader CI and publish validation**

Compile 2003-2006 before `npm test`; validate reports before publishing candidate content.

- [ ] **Step 3: Run full reader/content contract suite**

Run: `cd kaoyan-reader-v1 && npm test`

Run: `PYTHONPATH=voice-pipeline:content-pipeline python -m unittest content-pipeline/tests/test_bilingual_highlights.py content-pipeline/tests/test_build_curated_year.py -v`

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/reader-tests.yml .github/workflows/publish-kaoyan-batch.yml
git commit -m "ci: gate publication on bilingual highlight coverage"
```
