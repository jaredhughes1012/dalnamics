#!/usr/bin/env bash
# Replaces an existing issue's body with a refined plan and labels it refined.
#
# usage: issue-publish.sh <issue-number> <body-file> [new-title]
set -euo pipefail
n="$1" body="$2" title="${3:-}"
"$(dirname "$0")/labels.sh"
args=(--body-file "$body" --add-label refined)
[[ -n "$title" ]] && args+=(--title "$title")
gh issue edit "$n" "${args[@]}" >/dev/null
gh issue view "$n" --json number,url --jq '"#\(.number) \(.url)"'
