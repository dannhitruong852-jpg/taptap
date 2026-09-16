# C Mode Production Pipeline V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ad-hoc year-specific C-mode production with one versioned, testable, additive, rollback-aware canonical pipeline.

**Architecture:** Introduce a repository-level production contract, a small Python core for state/manifest/release invariants, a committed batch-manifest format, and one parameterized GitHub Actions workflow. Expensive audio rendering is gated behind full validation and content freeze; publication always starts from current production and must pass an additive release guard.

**Tech Stack:** Python 3.11+, `unittest`, GitHub Actions, existing `content-pipeline`, existing `voice-pipeline`, Git.

**Spec:** `docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md`

## Global Constraints

- Do not modify `main`.
- `gh-pages` publication must be additive; no arbitrary source-tree force-push.
- `rendering` cannot start before `frozen`.
- Every known deterministic historical defect must be represented by a test or gate.
- Canonical workflow is manifest-driven, not year-list hard-coded.
- Existing 2002-2012 production is the baseline that must not regress.

---

### Task 1: Repository production contract

**Files:**
- Create: `PRODUCTION_RULES.md`
- Create: `docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md`

**Produces:** Human/agent rules that define the canonical path and prohibited shortcuts.

- [ ] Record single-source-of-truth rule.
- [ ] Record mandatory state sequence and freeze gate.
- [ ] Record additive release invariant.
- [ ] Record prohibition on year-specific canonical workflows and production force-push.
- [ ] Record Definition of Done.

### Task 2: State machine and batch manifest core

**Files:**
- Create: `production_v2/__init__.py`
- Create: `production_v2/pipeline_state.py`
- Create: `production_v2/manifest.py`
- Test: `production_v2/tests/test_pipeline_state.py`
- Test: `production_v2/tests/test_manifest.py`

**Interfaces:**
- Produces: `can_transition(current, target) -> bool`
- Produces: `next_state(current) -> str | None`
- Produces: `build_manifest(batch_id, years, source_ref, created_at=None) -> dict`
- Produces: `validate_manifest(doc) -> list[str]`

- [ ] Write failing state-machine tests.
- [ ] Run tests and observe missing implementation failure.
- [ ] Implement deterministic state transitions.
- [ ] Run state tests green.
- [ ] Write failing manifest tests.
- [ ] Implement required fields and validation.
- [ ] Run manifest tests green.

### Task 3: Additive release guard

**Files:**
- Create: `production_v2/release_guard.py`
- Create: `production_v2/cli_release_guard.py`
- Test: `production_v2/tests/test_release_guard.py`

**Interfaces:**
- Produces: `compare_catalogs(old_catalog, new_catalog) -> dict`
- CLI exits non-zero when existing years/articles disappear or routing fields mutate.

- [ ] Write failing additive-release tests.
- [ ] Prove missing historical year fails.
- [ ] Prove changed existing routing fails.
- [ ] Implement minimal comparison logic.
- [ ] Run tests green.

### Task 4: Manifest CLI and state advancement

**Files:**
- Create: `production_v2/cli_manifest.py`
- Test: `production_v2/tests/test_manifest_cli.py`

**Interfaces:**
- `create --batch-id --years --source-ref --output`
- `validate --manifest`
- `advance --manifest --to --output`

- [ ] Write CLI tests with temporary files.
- [ ] Require legal transitions only.
- [ ] Implement atomic JSON output.
- [ ] Run tests green.

### Task 5: Freeze fingerprints and production matrix

**Files:**
- Create: `production_v2/freeze.py`
- Create: `production_v2/matrix.py`
- Test: `production_v2/tests/test_freeze.py`
- Test: `production_v2/tests/test_matrix.py`

**Interfaces:**
- Freeze hashes canonical content files and records SHA-256 by article.
- Matrix emits deterministic `(year, article, shard)` units from the committed manifest and catalog/content inventory.

- [ ] Write deterministic fingerprint tests.
- [ ] Write deterministic matrix tests.
- [ ] Implement freeze report creation.
- [ ] Implement matrix JSON output.
- [ ] Run tests green.

### Task 6: Batch validation gate

**Files:**
- Create: `production_v2/validate_batch.py`
- Test: `production_v2/tests/test_validate_batch.py`

**Interfaces:**
- `validate_batch(manifest, repo_root, phase) -> report`
- `phase=preflight|freeze|release`

- [ ] Encode article inventory/file presence checks.
- [ ] Encode manifest sentence/missing-segment checks for release phase.
- [ ] Reuse existing project validators where available rather than duplicating C-mode semantics.
- [ ] Fail closed on missing required evidence.
- [ ] Run tests green.

### Task 7: Canonical GitHub Actions pipeline

**Files:**
- Create: `.github/workflows/c-mode-production-v2.yml`
- Create: `production_v2/tests/test_workflow_contract.py`

**Interfaces:**
- Input: committed `batch_manifest` path.
- Optional input: publish boolean.
- Jobs: prepare -> canary -> validate -> freeze -> voicepack -> render -> merge -> release_guard -> publish.

- [ ] Write workflow contract test first.
- [ ] Require `needs` dependencies that physically prevent render before freeze and publish before release guard.
- [ ] Generate matrices from manifest output.
- [ ] Preserve current actor/Chatterbox production setup.
- [ ] Publish from current `gh-pages` baseline, never arbitrary source HEAD.
- [ ] Store rollback SHA and release report.

### Task 8: Historical regression suite

**Files:**
- Create or extend tests under `production_v2/tests/` and existing relevant test suites.

- [ ] Add production-catalog preservation regression.
- [ ] Reference existing source-scope, bilingual, actor-plan, discourse/density, and single-row regressions from the canonical preflight.
- [ ] Ensure failure in any mandatory contract blocks freeze.

### Task 9: Verification and migration readiness

**Files:**
- Modify only documentation/status metadata if needed.

- [ ] Run `python -m unittest discover -s production_v2/tests -v`.
- [ ] Run existing Reader tests: `cd kaoyan-reader-v1 && npm test`.
- [ ] Run existing content-pipeline unit tests used by current production gates.
- [ ] Validate canonical workflow syntax/contracts.
- [ ] Dry-run release guard against current 2002-2012 catalog as both baseline and candidate.
- [ ] Dry-run a synthetic candidate that removes 2003 and prove it is rejected.
- [ ] Do not publish or regenerate audio during V2 framework implementation.

### Task 10: Future batch operating procedure

**Files:**
- Create: `docs/production/C_MODE_PRODUCTION_V2.md`

- [ ] Document exact operator commands/inputs.
- [ ] Document canary choice.
- [ ] Document failure/retry semantics.
- [ ] Document how to inspect run state and reports.
- [ ] Document rollback procedure.
- [ ] State that future agents must use this canonical workflow rather than inventing a new one.
