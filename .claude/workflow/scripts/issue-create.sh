#!/usr/bin/env bash
# Creates a new refined issue from a plan file and prints "#<number> <url>".
#
# usage: issue-create.sh <title> <body-file>
set -euo pipefail
title="$1" body="$2"
"$(dirname "$0")/labels.sh"
url="$(gh issue create --title "$title" --body-file "$body" --label refined)"
echo "#${url##*/} $url"
