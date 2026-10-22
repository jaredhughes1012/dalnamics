#!/usr/bin/env bash
# Stops what run_local.sh started, from whichever checkout it ran in: the studio
# dev server and that checkout's compose stack. A worktree's stack goes with its
# volumes and the harwood0 emulator's credentials, which belonged to it; the
# main checkout's keeps both. Then restarts the services of any stack
# run_local.sh stopped to free the container names.
#
# usage: ./cleanup_local.sh
set -euo pipefail
cd "$(dirname "$0")"
session="$(git rev-parse --path-format=absolute --git-common-dir)/run-local"
state="$session/session"
restore="$session/restore"

[[ -f "$state" ]] || { echo "Nothing is running."; exit 0; }
studio_pgid="" harwood0_state=""
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

# The main checkout's git dir is the shared one; a linked worktree's isn't. A
# checkout that no longer exists was a removed worktree.
worktree=1
if [[ -d "$dir" && "$(git -C "$dir" rev-parse --absolute-git-dir)" == "$(git -C "$dir" rev-parse --path-format=absolute --git-common-dir)" ]]; then
  worktree=0
fi

if (( worktree )); then
  echo "Stopping compose project $project ($dir) and removing its volumes."
  docker compose -p "$project" down -v --remove-orphans
  [[ -n "$harwood0_state" ]] && rm -rf "$harwood0_state"
else
  echo "Stopping compose project $project ($dir)."
  docker compose -p "$project" down --remove-orphans
fi

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

rm -f "$state" "$restore"
