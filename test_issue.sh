#!/usr/bin/env bash
# Starts an issue's worktree for manual testing: brings up its compose stack
# (`make up`) and runs the studio dev server (`make run-studio`) in the
# background. Container names and ports are fixed, so only one stack can run at
# a time: a previous test session is cleaned up first, and any other compose
# stack holding the same container names (e.g. the main checkout's) is stopped
# and recorded so cleanup_test.sh can restart it.
#
# usage: test_issue.sh <issue-number>
set -euo pipefail
n="${1:?usage: test_issue.sh <issue-number>}"
here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$(git -C "$here" rev-parse --path-format=absolute --git-common-dir)")"
state="$root/worktrees/.test-session"
restore="$root/worktrees/.test-restore"
log="$root/worktrees/.test-studio.log"
studio_port=5173

shopt -s nullglob
dirs=("$root"/worktrees/issue-"$n"-*/)
(( ${#dirs[@]} == 1 )) || { echo "Expected one worktree for #$n in $root/worktrees, found ${#dirs[@]}." >&2; exit 1; }
dir="${dirs[0]%/}"

[[ -f "$state" ]] && "$here/cleanup_test.sh"

if lsof -nP -iTCP:"$studio_port" -sTCP:LISTEN >/dev/null; then
  echo "Port $studio_port is already in use; stop that dev server first:" >&2
  lsof -nP -iTCP:"$studio_port" -sTCP:LISTEN >&2
  exit 1
fi

config="$(cd "$dir" && docker compose config --format json)"
project="$(jq -r .name <<<"$config")"

# Stop other stacks that own our container names, remembering which of their
# services were running.
: >"$restore"
for name in $(jq -r '.services[].container_name // empty' <<<"$config"); do
  other="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "$name" 2>/dev/null)" || continue
  [[ -n "$other" && "$other" != "$project" ]] || continue
  grep -q "^$other	" "$restore" && continue
  wd="$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' "$name")"
  running="$(docker ps --filter "label=com.docker.compose.project=$other" --format '{{.Label "com.docker.compose.service"}}' | tr '\n' ' ')"
  echo "Stopping compose project $other ($wd) to free container names."
  docker compose -p "$other" down
  [[ -n "$running" ]] && printf '%s\t%s\t%s\n' "$other" "$wd" "$running" >>"$restore"
done

printf 'dir=%q\nproject=%q\n' "$dir" "$project" >"$state"

(cd "$dir" && make up)

[[ -d "$dir/studio/node_modules" ]] || (cd "$dir/studio" && pnpm install --frozen-lockfile --silent)

# Job control gives the dev server its own process group, so cleanup can stop
# make, pnpm, and vite together.
set -m
(cd "$dir" && exec nohup make run-studio) </dev/null >"$log" 2>&1 &
pgid=$!
set +m
printf 'studio_pgid=%q\n' "$pgid" >>"$state"

for _ in $(seq 60); do
  curl -sf -o /dev/null "http://localhost:$studio_port" && break
  kill -0 "$pgid" 2>/dev/null || { echo "Studio dev server exited:" >&2; tail -n 30 "$log" >&2; exit 1; }
  sleep 0.5
done

echo
echo "Testing #$n from $dir"
echo "  studio: http://localhost:$studio_port (log: $log)"
echo "  api:    http://localhost:8080"
echo "Stop with: $here/cleanup_test.sh"
