#!/usr/bin/env bash
# Claims a refined issue for an /implement session by adding the in-progress
# label. Fails if the issue is closed, unrefined, or already claimed.
#
# usage: claim.sh <issue-number>
set -euo pipefail
n="$1"
"$(dirname "$0")/labels.sh"
read -r state labels < <(gh issue view "$n" --json state,labels --jq '"\(.state) ,\(.labels | map(.name) | join(",")),"')
[[ "$state" == OPEN ]] || { echo "#$n is $state." >&2; exit 1; }
[[ "$labels" == *,refined,* ]] || { echo "#$n is not refined; run /refine $n first." >&2; exit 1; }
[[ "$labels" != *,in-progress,* ]] || { echo "#$n is already in progress in another session." >&2; exit 1; }
gh issue edit "$n" --add-label in-progress >/dev/null
echo "Claimed #$n."
