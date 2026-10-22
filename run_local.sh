#!/usr/bin/env bash
# Runs this checkout (the main checkout or a worktree, whichever this script is
# in) locally: brings up its compose stack (`make up`) and runs the studio dev
# server (`make run-studio`) in the background. Container names and ports are
# fixed, so only one checkout's stack can run at a time: a previous session,
# from any checkout, is cleaned up first, and any other compose stack holding
# the same container names is stopped and recorded so cleanup_local.sh can
# restart it. If the api seeds a dev device registration code, it also prints a
# command that starts the harwood0 emulator registered with that code.
#
# usage: ./run_local.sh
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
cd "$dir"
# Session files live in the shared git dir, so every checkout sees the session.
session="$(git rev-parse --path-format=absolute --git-common-dir)/run-local"
state="$session/session"
restore="$session/restore"
log="$session/studio.log"
# Emulator credentials belong to this checkout's database, so they live in its
# own git dir, and cleanup_local.sh deletes them along with a worktree's volumes.
harwood0_state="$(git rev-parse --absolute-git-dir)/run-local-harwood0"
studio_port=5173

mkdir -p "$session"
[[ -f "$state" ]] && "$dir/cleanup_local.sh"

if lsof -nP -iTCP:"$studio_port" -sTCP:LISTEN >/dev/null; then
  echo "Port $studio_port is already in use; stop that dev server first:" >&2
  lsof -nP -iTCP:"$studio_port" -sTCP:LISTEN >&2
  exit 1
fi

config="$(docker compose config --format json)"
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

printf 'dir=%q\nproject=%q\nharwood0_state=%q\n' "$dir" "$project" "$harwood0_state" >"$state"

make up

[[ -d studio/node_modules ]] || (cd studio && pnpm install --frozen-lockfile --silent)

# Job control gives the dev server its own process group, so cleanup can stop
# make, pnpm, and vite together.
set -m
exec nohup make run-studio </dev/null >"$log" 2>&1 &
pgid=$!
set +m
printf 'studio_pgid=%q\n' "$pgid" >>"$state"

for _ in $(seq 60); do
  curl -sf -o /dev/null "http://localhost:$studio_port" && break
  kill -0 "$pgid" 2>/dev/null || { echo "Studio dev server exited:" >&2; tail -n 30 "$log" >&2; exit 1; }
  sleep 0.5
done

echo
echo "Running $dir"
echo "  studio: http://localhost:$studio_port (log: $log)"
echo "  api:    http://localhost:8080"

dev_code="$(jq -r '.services.api.environment.DEV_REGISTRATION_CODE // empty' <<<"$config")"
if [[ -n "$dev_code" && -d harwood0 ]]; then
  echo
  echo "To start the harwood0 emulator registered to the first dev user (dev@dalnamics.local), from $dir:"
  printf '  (cd harwood0 && HARWOOD0_MQTT_URL=mqtt://localhost:1883 HARWOOD0_REGISTRATION_CODE=%q HARWOOD0_STATE_DIR=%q make api-sim)\n' \
    "$dev_code" "$harwood0_state"
fi

echo
echo "Stop with: ./cleanup_local.sh"
