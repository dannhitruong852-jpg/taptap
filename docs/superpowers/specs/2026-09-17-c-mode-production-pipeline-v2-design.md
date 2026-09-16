# C Mode Production Pipeline V2 Design

Date: 2026-09-17
Status: approved architecture, implementation target
Branch: `c-mode-production-v2`
Scope: all future C-mode exam batches and release publication

## 1. Purpose

Convert the lessons from the 2003-2006 and 2007-2012 production runs into repository-enforced behavior. The production process must no longer depend on chat history, operator memory, or ad-hoc one-shot workflows. GitHub is the single source of truth.

The central rule is:

> A known failure mode is not considered fixed until it is encoded as an invariant, test, validator, or CI gate.

## 2. Canonical pipeline

All future batches use one canonical pipeline:

`draft -> validated -> frozen -> rendering -> merged -> release_candidate -> published`

The workflow stages are:

1. prepare batch manifest;
2. preflight validation;
3. canary validation on one representative year;
4. full-batch content validation;
5. freeze immutable content fingerprints;
6. parallel audio rendering by year/article/shard;
7. merge and technical QA;
8. release-candidate construction;
9. reader regression tests;
10. production integrity/release guard;
11. additive publication to production.

Skipping a state is forbidden. In particular, `rendering` cannot begin before `frozen`.

## 3. Repository as single source of truth

The following are versioned in GitHub:

- this architecture;
- `PRODUCTION_RULES.md` agent/operator contract;
- batch manifests;
- state machine code;
- validators;
- release guard;
- canonical GitHub Actions workflow;
- regression tests;
- freeze/release reports.

Chat history is not authoritative for production behavior.

## 4. Batch manifest and traceability

Every batch has a committed manifest containing at least:

- `batch_id`;
- `pipeline_version`;
- sorted unique `years`;
- source Git ref/SHA;
- current state;
- creation timestamp;
- freeze metadata;
- artifact metadata.

At freeze time the batch records content fingerprints. Audio production must be traceable to a frozen source/content identity and pipeline version.

## 5. Shift-left policy

Cheap validation happens before expensive audio rendering.

Before freeze, the full batch must validate:

- expected article inventory;
- article schema;
- source-scope verification;
- sentence/segment coverage;
- bilingual exact mappings;
- vocabulary occurrence mapping;
- actor-plan compatibility;
- discourse-function compatibility;
- C-mode density rules;
- browser-manifest contract inputs.

Any failure blocks freeze and therefore blocks TTS rendering.

## 6. Parallelism policy

Parallelism is required after inputs are frozen.

Pattern:

`1 canary -> full validation -> freeze -> N-way render`

Rendering is partitioned by `(year, article, shard)`. Failure of one render unit must not require rerunning unrelated successful units. Retries are bounded and deterministic where practical.

Parallelism before validation/freeze is prohibited when it can multiply an unverified shared defect.

## 7. Idempotency and retry behavior

A repeated run of the same frozen batch must:

- reuse unchanged fingerprints;
- skip already-complete artifacts when possible;
- retry only missing/failed units;
- never silently rewrite frozen content;
- produce the same release structure for the same frozen inputs.

## 8. Additive publication invariant

Production publication is additive by default.

The release candidate is compared against current production. Unless an explicit separately reviewed deletion migration exists:

- every existing production year must remain present;
- every existing article id must remain present;
- existing article routing fields (`year`, `content`, `manifest`) must not silently mutate;
- new years/articles may be added;
- publication starts from the current production tree, then overlays validated new assets.

Invariant:

`existingArticleIds ⊆ candidateArticleIds`

and

`existingYears ⊆ candidateYears`.

Violation blocks publish. This permanently prevents a repeat of the 2003-2006 disappearance caused by replacing production with a later-batch branch tree.

## 9. Production branch policy

No normal batch workflow may force-push an arbitrary source branch tree over `gh-pages`.

The publish job must:

1. fetch current `gh-pages`;
2. construct a release candidate from that production baseline;
3. overlay only validated batch assets and required reader changes;
4. run release guard and reader regression tests;
5. create a production commit on top of the current production commit;
6. push fast-forward when possible;
7. record the previous production SHA for rollback.

## 10. Rollback

Every publish report records:

- previous production SHA;
- new production SHA;
- batch id;
- source SHA;
- release guard report.

Rollback means moving production back to the recorded previous production commit through the controlled release path, not reconstructing files manually.

## 11. Observability

Every run must expose at minimum:

- batch id and pipeline version;
- current state/stage;
- requested years;
- total render units;
- completed/failed units;
- retry counts;
- freeze identity;
- release-candidate identity;
- production baseline SHA;
- publication result.

Machine-readable reports are artifacts; human-readable summaries are emitted into GitHub Actions job summaries.

## 12. Regression policy

Every previously observed production defect becomes a permanent regression case when it can be expressed deterministically. Required historical contracts include:

- no single-row collapse for article extraction;
- legacy discourse labels are normalized/validated;
- density rules are enforced;
- actor-plan mismatch blocks freeze;
- source-scope verification is required;
- bilingual exact-span mapping is complete;
- release cannot remove previously published years/articles.

## 13. Workflow policy

The repository must converge on a small number of durable workflows. New year-specific `*-once.yml` production workflows are prohibited except for emergency recovery and must not become the canonical path.

The durable canonical workflow is parameterized by a committed batch manifest, not by hard-coded year lists.

## 14. Definition of Done

A batch is complete only when all of the following are true:

- batch state is `published`;
- all mandatory gates passed;
- all required render units are complete;
- merged manifests report no missing segments;
- reader tests pass;
- bilingual/content contracts pass;
- release guard confirms no production regression;
- GitHub Pages deployment succeeds;
- production catalog contains all previous and new expected years/articles;
- release report records rollback metadata.

A green render job alone is not completion.

## 15. Operator/agent behavior

Any human or AI agent starting a future batch must first read `PRODUCTION_RULES.md` and this design. Agents must use the canonical workflow and may not substitute a custom production procedure without an explicit architecture change committed and reviewed in the repository.
