#!/usr/bin/env bash
# Prints the context a refinement needs: the issue being refined (if a number is
# given), every other open issue, and the heading outline of docs/*.md.
#
# usage: context.sh [issue-number]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

n="${1:-}"

if [[ -n "$n" ]]; then
  echo "# Issue #$n"
  echo
  gh issue view "$n" --json number,title,state,labels,body,comments --jq '
    "Title: \(.title)\nState: \(.state)\nLabels: \(.labels | map(.name) | join(", "))\n\n\(.body)\n"
    + (.comments | map("\n### Comment by \(.author.login)\n\n\(.body)\n") | join(""))'
  echo
fi

echo "# Other open issues"
echo
gh issue list --state open --limit 200 --json number,title,labels,body --jq "
  map(select(.number != ${n:-0}))
  | if length == 0 then \"(none)\" else
      map(\"## #\(.number) \(.title) [\(.labels | map(.name) | join(\", \"))]\n\n\(.body)\n\") | join(\"\n\")
    end"
echo

echo "# Docs outline"
for f in docs/*.md; do
  echo
  echo "## $f"
  grep -E '^#{1,3} ' "$f" || true
done
