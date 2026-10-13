#!/usr/bin/env bash
# Lists the issues referenced in an issue's "## Depends on" section with their
# state. Exits 1 if any dependency is not closed as completed.
#
# usage: deps.sh <issue-number>
set -euo pipefail
n="$1"
deps="$(gh issue view "$n" --json body --jq .body \
  | awk '/^## /{in_section = ($0 ~ /^## Depends on/)} in_section' \
  | grep -oE '#[0-9]+' | tr -d '#' | sort -un || true)"

if [[ -z "$deps" ]]; then
  echo "No dependencies."
  exit 0
fi

blocked=0
for d in $deps; do
  line="$(gh issue view "$d" --json number,title,state,stateReason \
    --jq '"#\(.number) \(.state)\(if .stateReason then "/" + .stateReason else "" end) \(.title)"')"
  if [[ "$line" == *" CLOSED/COMPLETED "* ]]; then
    echo "done     $line"
  else
    echo "BLOCKING $line"
    blocked=1
  fi
done
exit "$blocked"
