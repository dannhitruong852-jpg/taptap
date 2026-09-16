# C Mode Production Rules

This file is the repository-level operating contract for all future C-mode production batches.

## Authority

- GitHub repository state is the single source of truth.
- Chat history, operator memory, and ad-hoc instructions are not authoritative production specifications.
- Before starting or modifying a batch, read this file and `docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md`.

## Canonical state sequence

`draft -> validated -> frozen -> rendering -> merged -> release_candidate -> published`

Skipping states is forbidden.

In particular:

- no audio rendering before `frozen`;
- no publish before `release_candidate`;
- no release candidate before merge/QA succeeds.

## Mandatory production behavior

- Use the canonical V2 workflow.
- Use a committed batch manifest.
- Run one canary before broad fan-out.
- Validate the entire batch before freeze.
- Freeze content fingerprints before rendering.
- Parallelize only frozen render units.
- Retry only failed/missing units when possible.
- Keep all release validation machine-readable.
- Start publication from current production, then overlay validated additions.
- Preserve all previously published years/articles unless a separately reviewed deletion migration exists.
- Record rollback metadata for every production publish.

## Prohibited behavior

Do not:

- invent a new year-specific canonical workflow for each batch;
- create a new `*-once.yml` as the normal production path;
- start large TTS fan-out on unvalidated content;
- mutate frozen content during rendering;
- force-push an arbitrary working branch tree over `gh-pages`;
- replace the production catalog with a batch-only catalog;
- ignore a failed mandatory gate and continue manually;
- declare completion from render success alone.

Emergency recovery workflows may exist, but they are not canonical and must not be reused as the normal path.

## Permanent regression rule

When a deterministic production bug occurs:

1. identify root cause;
2. add a regression test/invariant/gate;
3. prove the test fails without the fix when feasible;
4. implement the fix;
5. prove the test passes;
6. only then treat the defect as learned by the system.

A note saying “remember next time” is not a fix.

## Release invariants

Unless an explicit deletion migration is approved:

- `existingYears` must be a subset of `candidateYears`;
- `existingArticleIds` must be a subset of `candidateArticleIds`;
- existing article routing fields (`year`, `content`, `manifest`) must not silently change;
- current production assets must remain intact while new validated assets are added.

Violation blocks publication.

## Definition of Done

A batch is done only when:

- all required gates pass;
- batch state reaches `published`;
- all render units required by the frozen manifest are complete;
- merged manifests contain no missing segments;
- Reader tests pass;
- content/bilingual/actor/source-scope/C-mode contracts pass;
- release guard passes against current production;
- GitHub Pages deployment succeeds;
- current production contains all previous content plus the new batch;
- release report records the previous production SHA for rollback.
