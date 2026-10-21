#!/usr/bin/env bash
# Stops what test_issue.sh started: the studio dev server and the worktree's
# compose stack, including its volumes, and deletes the harwood0 emulator's
# credentials, which belonged to that stack. Then restarts the services of any
# stack test_issue.sh stopped to free the container names.
#
# usage: cleanup_test.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$(git -C "$here" rev-parse --path-format=absolute --git-common-dir)")"
state="$root/worktrees/.test-session"
restore="$root/worktrees/.test-restore"

[[ -f "$state" ]] || { echo "No test session is running."; exit 0; }
studio_pgid=""
. "$state"

if [[ -n "$studio_pgid" ]] && kill -0 -- "-$studio_pgid" 2>/dev/null; then
  echo "Stopping studio dev server."
  kill -TERM -- "-$studio_pgid" 2>/dev/null || true
  for _ in $(seq 20); do
    kill -0 -- "-$studio_pgid" 2>/dev/null || break
    sleep 0.5
  done
  kill -KILL -- "-$studio_pgid" 2>/dev/null || true
fi

echo "Stopping compose project $project ($dir)."
docker compose -p "$project" down -v --remove-orphans

if [[ -f "$restore" ]]; then
  while IFS=$'\t' read -r other wd services; do
    if [[ -d "$wd" ]]; then
      echo "Restarting $services in compose project $other ($wd)."
      # shellcheck disable=SC2086 # services is a space-separated list
      (cd "$wd" && docker compose -p "$other" up -d --wait $services) || echo "Failed to restart $other." >&2
    else
      echo "Not restarting $other: $wd no longer exists." >&2
    fi
  done <"$restore"
fi

rm -rf "$root/worktrees/.test-harwood0"
rm -f "$state" "$restore"
