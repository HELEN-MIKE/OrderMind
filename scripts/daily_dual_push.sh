#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

branch="${ORDERMIND_SYNC_BRANCH:-main}"
commit_message="${ORDERMIND_COMMIT_MESSAGE:-chore: daily project sync $(date +%Y-%m-%d)}"

git remote get-url origin >/dev/null
git remote get-url gitee >/dev/null

has_worktree_changes=0
if ! git diff --quiet || ! git diff --cached --quiet; then
  has_worktree_changes=1
fi

if [ -n "$(git ls-files --others --exclude-standard)" ]; then
  has_worktree_changes=1
fi

if [ "$has_worktree_changes" -eq 1 ]; then
  python3 -m unittest discover -s tests -v
  python3 -m compileall ordermind run_app.py scripts
  python3 scripts/release_check.py

  git add -- .

  if ! git diff --cached --quiet; then
    git commit -m "$commit_message"
  fi
fi

failed_remotes=()

for remote in origin gitee; do
  if ! git push "$remote" "$branch"; then
    failed_remotes+=("$remote")
  fi
done

if [ "${#failed_remotes[@]}" -gt 0 ]; then
  printf 'Failed to push to: %s\n' "${failed_remotes[*]}" >&2
  exit 1
fi
