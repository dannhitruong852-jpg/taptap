# C Mode Production V2 Operating Procedure

This is the canonical operating procedure for future C-mode batches.

Read first:

1. `PRODUCTION_RULES.md`
2. `docs/superpowers/specs/2026-09-17-c-mode-production-pipeline-v2-design.md`
3. the committed batch manifest for the run

Do not invent a replacement workflow for a new year range.

## 1. Prepare a batch manifest

Create the manifest with the repository CLI, for example:

```bash
python -m production_v2.cli_manifest create \
  --batch-id 2013-2018 \
  --years 2013,2014,2015,2016,2017,2018 \
  --source-ref <SOURCE_GIT_SHA> \
  --output batch-manifests/2013-2018.json
```

Review `expected_articles` before committing. The default future-year inventory is:

- `cloze`
- `text1`
- `text2`
- `text3`
- `text4`
- `partb`
- `translation`

If an exam year legitimately has a different structure, edit that year's declared inventory explicitly in the manifest. The validator treats the committed manifest as the expected contract; it does not silently guess missing articles.

Validate locally:

```bash
python -m production_v2.cli_manifest validate --manifest batch-manifests/2013-2018.json
python -m unittest discover -s production_v2/tests -v
```

Commit the manifest before production starts.

## 2. First run: release-candidate mode

Trigger GitHub Actions workflow:

`C Mode Production Pipeline V2`

Inputs:

- `batch_manifest`: committed manifest path
- `publish`: `false`
- `shards`: normally `3`

Recommended first production run always uses `publish=false`.

The pipeline then executes:

`prepare -> canary -> validate -> freeze -> voicepack -> render -> merge -> release_guard`

No production branch is modified in release-candidate mode.

## 3. Canary

The first year in the manifest is the canary.

The canary exists to prove the shared production logic before full fan-out. It is not a serial-production requirement. Once the canary and full-batch validation pass, all frozen render units may run in parallel.

If the canary fails, fix the shared/root cause before allowing the full batch to progress.

## 4. Full validation and freeze

Before any expensive render job begins, the workflow validates the declared batch inventory and content contracts.

Freeze produces:

- validated batch manifest;
- exact content snapshot;
- SHA-256 content fingerprints;
- `freeze_id`;
- deterministic render matrix.

After this point, render jobs consume the frozen artifact. They do not rebuild content independently.

## 5. Parallel rendering and retries

The render matrix is generated from the manifest and catalog. Units are `(year, article, shard)`.

The normal rule is:

- successful unit: keep/reuse it;
- failed unit: retry that unit/job only;
- do not rerun unrelated successful years/articles unless their frozen input changed.

Render cache keys include `freeze_id`, year, article, and shard.

## 6. Merge and release candidate

Each year is merged independently after all required render units succeed.

Mandatory technical checks include:

- merge report is `complete_candidate`;
- technical QA passed;
- no missing article assets;
- no `missing_segments` in browser manifests.

The release candidate starts from the current `gh-pages` production commit and overlays validated batch assets. It never starts from an arbitrary development branch tree.

## 7. Additive release guard

Before publication, V2 compares the current production catalog with the candidate catalog.

Without an explicit deletion migration, publication is rejected when:

- an existing year disappears;
- an existing article ID disappears;
- an existing article changes its `year`, `content`, or `manifest` routing unexpectedly.

This is the permanent regression guard for the historical 2003-2006 disappearance incident.

## 8. Publication

After a successful release-candidate run, trigger the same canonical workflow with the same committed manifest and:

- `publish=true`

Publication performs the release guard and Reader regression tests again immediately before committing.

It also checks that current `gh-pages` still equals the exact production baseline that was validated. If another deployment changed production in the meantime, publication stops rather than overwriting it.

The publish step uses a normal fast-forward push. The canonical V2 path does not force-push an arbitrary working tree over `gh-pages`.

## 9. Pages verification and Definition of Done

A successful Git push is not sufficient.

After publication, `verify_pages` waits for the `pages build and deployment` workflow whose `head_sha` exactly matches the new production SHA.

The batch is not considered fully published until that Pages workflow completes successfully.

## 10. State model

Legal states are:

`draft -> validated -> frozen -> rendering -> merged -> release_candidate -> published`

The CLI rejects skipped transitions.

The release report records the final published state and state history.

## 11. Rollback

Every release candidate records `previous_production_sha`.

If rollback is required:

1. identify the previous production SHA from `reports/production-v2-release.json`;
2. do not reconstruct old files manually;
3. use a controlled rollback/release operation based on that exact known-good production commit;
4. verify GitHub Pages deployment for the rollback SHA.

A rollback must preserve auditability and must not be implemented as an unrelated branch overwrite.

## 12. Observability

For each run inspect:

- workflow run status;
- batch id;
- canary year;
- freeze id;
- render matrix/failures;
- merged-year artifacts;
- release guard report;
- release validation report;
- baseline production SHA;
- new production SHA when published;
- matching Pages deployment result.

Artifacts and job summaries are the operational evidence. Do not infer completion from a spinning/green-looking UI alone.

## 13. Historical regressions

The canonical validation phase runs V2 regression tests and existing applicable historical production tests. Any deterministic bug discovered in future production must be added to this permanent suite before the bug is considered learned by the system.

## 14. Future-agent rule

When asked to produce a future range such as 2013-2018 or 2019-2024, an agent must not redesign the production process.

The agent's job is:

1. inspect repository state;
2. prepare/review the batch manifest;
3. run the canonical V2 workflow;
4. diagnose a failing gate at its root cause;
5. add a regression if a new deterministic defect is found;
6. retry only the smallest necessary failed unit;
7. publish only through the guarded additive release path;
8. verify the matching Pages deployment before claiming completion.
