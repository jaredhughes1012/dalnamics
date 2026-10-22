#!/usr/bin/env bash
# Prints what a /review-issues run covers: the last release tag (the newest
# vX.Y.Z tag on main), the candidate next versions, any release review still in
# flight, and every merged PR that closed an issue since the last release, with
# the issues it closed and the files it changed outside harwood0/. Commits that
# didn't come from such a PR (CAD and utility work) aren't listed.
#
# With --list, prints only "<pr>\t<issue numbers>\t<pr title>" per PR instead.
#
# usage: review-range.sh [--list] [<from-ref> [<to-ref>]]
#   from-ref defaults to the last release tag; an empty from-ref, or no tag,
#   puts everything in range. to-ref defaults to origin/main.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

list=0
[[ "${1:-}" == --list ]] && { list=1; shift; }

git fetch --quiet --tags origin main
last="$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' origin/main 2>/dev/null || true)"
from="${1-$last}"
to="$(git rev-parse "${2:-origin/main}")"

# Merged PRs whose merge commit is in from..to and that closed at least one issue.
in_range() {
  git merge-base --is-ancestor "$1" "$to" 2>/dev/null || return 1
  [[ -z "$from" ]] || ! git merge-base --is-ancestor "$1" "$from"
}
prs="$(gh pr list --state merged --base main --limit 500 \
  --json number,title,mergeCommit,closingIssuesReferences \
  --jq 'map(select(.closingIssuesReferences | length > 0))
        | sort_by(.number)[]
        | [.number, .mergeCommit.oid, (.closingIssuesReferences | map(.number | tostring) | join(",")), .title]
        | @tsv')"

rows=""
while IFS=$'\t' read -r pr oid issues title; do
  [[ -n "$pr" ]] && in_range "$oid" && rows+="$pr"$'\t'"$oid"$'\t'"$issues"$'\t'"$title"$'\n'
done <<<"$prs"

if (( list )); then
  printf '%s' "$rows" | cut -f1,3,4
  exit 0
fi

if [[ -n "$last" ]]; then
  IFS=. read -r major minor patch <<<"${last#v}"
  echo "Last release: $last ($(git rev-parse --short "$last^{commit}"))"
  echo "Next version: patch v$major.$minor.$((patch + 1)), minor v$major.$((minor + 1)).0, major v$((major + 1)).0.0"
else
  echo "Last release: none"
  echo "Next version: v0.1.0 (first release)"
fi
echo "Reviewing:    ${from:-<root>}..origin/main ($(git rev-parse --short "$to"))"
echo

# A release review is in flight when a fix/release-* PR is open, or merged but
# its version isn't tagged yet (tag-release.sh --pr <n> finishes it).
pending="$(gh pr list --state all --limit 50 --json number,state,headRefName,body \
  --jq 'map(select(.headRefName | startswith("fix/release-")) | select(.state != "CLOSED"))[]
        | [.number, .state, .headRefName, (first((.body // "") | capture("<!-- release-review (?<v>v[0-9.]+) ").v) // "")] | @tsv')"
while IFS=$'\t' read -r pr state branch version; do
  [[ -n "$pr" ]] || continue
  [[ "$state" == MERGED ]] && git rev-parse -q --verify "refs/tags/$version" >/dev/null && continue
  echo "Pending review: PR #$pr ($branch, $state) for $version"
done <<<"$pending"

if [[ -z "$rows" ]]; then
  echo "No merged issue PRs in range."
  exit 0
fi

while IFS=$'\t' read -r pr oid issues title; do
  [[ -n "$pr" ]] || continue
  echo "## PR #$pr $title ($(git rev-parse --short "$oid"))"
  for i in ${issues//,/ }; do
    echo "closes #$i $(gh issue view "$i" --json title --jq .title)"
  done
  echo "files:"
  git diff --name-only "$oid^1" "$oid" | grep -v '^harwood0/' | sed 's/^/  /' || echo "  (none outside harwood0/)"
  echo
done <<<"$rows"
