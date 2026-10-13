#!/usr/bin/env bash
# Removes the in-progress label, for a session that abandons an issue.
#
# usage: release.sh <issue-number>
set -euo pipefail
gh issue edit "$1" --remove-label in-progress >/dev/null
echo "Released #$1."
