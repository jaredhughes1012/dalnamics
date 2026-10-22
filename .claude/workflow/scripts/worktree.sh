#!/usr/bin/env bash
# Creates a worktree on a new branch from origin/main, under the main checkout's
# worktrees/ (ignored by git and docker, visible in the editor), and installs
# the studio and e2e dependencies. Prints the path and branch. An issue gets
# branch issue/<n>-<slug> in worktrees/issue-<n>-<slug>; `fix` (for
# /review-issues) gets branch fix/<slug> in worktrees/fix-<slug>.
#
# usage: worktree.sh <issue-number>|fix <short-slug>
set -euo pipefail
n="$1" slug="$2"
root="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
if [[ "$n" == fix ]]; then
  branch="fix/$slug"
  dir="$root/worktrees/fix-$slug"
else
  branch="issue/$n-$slug"
  dir="$root/worktrees/issue-$n-$slug"
fi

git -C "$root" fetch --quiet origin main
git -C "$root" worktree add --quiet -b "$branch" "$dir" origin/main
(cd "$dir/studio" && pnpm install --frozen-lockfile --silent)
(cd "$dir/test/studio" && pnpm install --frozen-lockfile --silent)

echo "worktree: $dir"
echo "branch:   $branch"
