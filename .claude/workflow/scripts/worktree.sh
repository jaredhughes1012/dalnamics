#!/usr/bin/env bash
# Creates a worktree for an issue on a new branch from origin/main, beside the
# main checkout (outside it, so docker build contexts and tooling never see it),
# and installs the studio and e2e dependencies. Prints the path and branch.
#
# usage: worktree.sh <issue-number> <short-slug>
set -euo pipefail
n="$1" slug="$2"
root="$(git rev-parse --show-toplevel)"
branch="issue/$n-$slug"
dir="$(dirname "$root")/$(basename "$root").worktrees/issue-$n-$slug"

git -C "$root" fetch --quiet origin main
git -C "$root" worktree add --quiet -b "$branch" "$dir" origin/main
(cd "$dir/studio" && pnpm install --frozen-lockfile --silent)
(cd "$dir/test/studio" && pnpm install --frozen-lockfile --silent)

echo "worktree: $dir"
echo "branch:   $branch"
