#!/usr/bin/env bash
# Tags a reviewed release on main and pushes the tag. The annotated tag's
# message lists the issues released since the previous tag.
#
# With --pr, tags the merge commit of a /review-issues fix PR, reading the
# version and the reviewed commit from the PR body's release-review marker.
# Otherwise tags the reviewed commit itself (a review with nothing to fix).
# Refuses if an issue PR merged between the reviewed commit and the target,
# since that work was never reviewed.
#
# usage: tag-release.sh --pr <pr-number>
#        tag-release.sh <version> <reviewed-commit>
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"
git fetch --quiet --tags origin main

if [[ "${1:-}" == --pr ]]; then
  pr="${2:?usage: tag-release.sh --pr <pr-number>}"
  read -r state target version reviewed < <(gh pr view "$pr" --json state,mergeCommit,body --jq '
    (.body | capture("<!-- release-review (?<v>v[0-9.]+) reviewed=(?<r>[0-9a-f]+) -->")) as $m
    | "\(.state) \(.mergeCommit.oid // "-") \($m.v) \($m.r)"') \
    || { echo "PR #$pr has no release-review marker." >&2; exit 1; }
  [[ "$state" == MERGED ]] || { echo "PR #$pr is $state; merge it first." >&2; exit 1; }
else
  pr=""
  version="${1:?usage: tag-release.sh <version> <reviewed-commit>}"
  reviewed="${2:?usage: tag-release.sh <version> <reviewed-commit>}"
  target="$reviewed"
fi
target="$(git rev-parse "$target^{commit}")"
reviewed="$(git rev-parse "$reviewed^{commit}")"

[[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "$version is not a vX.Y.Z version." >&2; exit 1; }
! git rev-parse -q --verify "refs/tags/$version" >/dev/null || { echo "$version already exists." >&2; exit 1; }
git merge-base --is-ancestor "$target" origin/main || { echo "$target is not on origin/main." >&2; exit 1; }
git merge-base --is-ancestor "$reviewed" "$target" || { echo "The reviewed commit $reviewed is not in $target." >&2; exit 1; }

last="$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' "$target" 2>/dev/null || true)"
if [[ -n "$last" && "$(printf '%s\n%s\n' "$last" "$version" | sort -V | tail -n1)" != "$version" ]]; then
  echo "$version is not newer than $last." >&2
  exit 1
fi

unreviewed="$("$here/review-range.sh" --list "$reviewed" "$target" | awk -F'\t' -v pr="$pr" '$1 != pr')"
if [[ -n "$unreviewed" ]]; then
  echo "These issue PRs merged after the review and were never reviewed; run /review-issues again:" >&2
  awk -F'\t' '{print "  PR #" $1 " (closes #" $2 ") " $3}' <<<"$unreviewed" >&2
  exit 1
fi

msg="$(mktemp)"
trap 'rm -f "$msg"' EXIT
released="$("$here/review-range.sh" --list "$last" "$target" | awk -F'\t' -v pr="$pr" '$1 != pr')"
{
  echo "Release $version"
  echo
  if [[ -n "$released" ]]; then
    echo "Issues:"
    awk -F'\t' '{gsub(",", ", #", $2); print "- #" $2 " " $3 " (PR #" $1 ")"}' <<<"$released"
  else
    echo "No issue work since ${last:-the start of the repo}."
  fi
  if [[ -n "$pr" ]]; then
    printf '\nRelease review fixes: PR #%s\n' "$pr"
  fi
} >"$msg"

git tag -a "$version" -F "$msg" "$target"
git push --quiet origin "refs/tags/$version"
echo "Tagged $version at $(git rev-parse --short "$target") and pushed it."
git tag -l --format='%(contents)' "$version"
