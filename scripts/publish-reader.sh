#!/usr/bin/env bash
# Update only the reader subtree on gh-pages. Never rewrite history or other projects.
set -euo pipefail
source_root=$(pwd)
pages_dir=$(mktemp -d)
rmdir "$pages_dir"
git fetch origin gh-pages
git worktree add --detach "$pages_dir" origin/gh-pages
cleanup() { git worktree remove --force "$pages_dir" >/dev/null 2>&1 || true; }
trap cleanup EXIT
mkdir -p "$pages_dir/kaoyan-reader-v1"
cp -a "$source_root/kaoyan-reader-v1/." "$pages_dir/kaoyan-reader-v1/"
touch "$pages_dir/.nojekyll"
git -C "$pages_dir" config user.name 'github-actions[bot]'
git -C "$pages_dir" config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git -C "$pages_dir" add kaoyan-reader-v1 .nojekyll
if ! git -C "$pages_dir" diff --cached --quiet; then
  git -C "$pages_dir" commit -m "publish: 2002 C acceptance candidate (run ${GITHUB_RUN_ID:-local})"
  git -C "$pages_dir" push origin HEAD:gh-pages
fi
# Token pushes do not automatically trigger Pages. Explicitly request its build.
gh api --method POST "repos/$GITHUB_REPOSITORY/pages/builds"
gh api "repos/$GITHUB_REPOSITORY/pages/builds/latest" --jq '{status,commit,error}'
