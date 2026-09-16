# C Mode V2 Batch Manifests

Every future C-mode production batch must have a committed manifest in this directory.

Create one with:

```bash
python -m production_v2.cli_manifest create \
  --batch-id 2013-2018 \
  --years 2013,2014,2015,2016,2017,2018 \
  --source-ref <SOURCE_GIT_SHA> \
  --output batch-manifests/2013-2018.json
```

Then review the declared `expected_articles` for each year, validate it, and commit it before running `C Mode Production Pipeline V2`.

Do not use an uncommitted manifest as the authoritative production input.

The manifest records intent; runtime state transitions and freeze/release evidence are emitted as workflow artifacts/reports rather than rewriting the original committed input during the run.
