#!/usr/bin/env bash
# Creates a worktree for an issue on a new branch from origin/main, under the
# main checkout's worktrees/ (ignored by git and docker, visible in the editor),
# and installs the studio and e2e dependencies. Prints the path and branch.
#
# usage: worktree.sh <issue-number> <short-slug>
set -euo pipefail
n="$1" slug="$2"
root="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
branch="issue/$n-$slug"
dir="$root/worktrees/issue-$n-$slug"

git -C "$root" fetch --quiet origin main
git -C "$root" worktree add --quiet -b "$branch" "$dir" origin/main
(cd "$dir/studio" && pnpm install --frozen-lockfile --silent)
(cd "$dir/test/studio" && pnpm install --frozen-lockfile --silent)

echo "worktree: $dir"
echo "branch:   $branch"
