#!/usr/bin/env bash
# Creates (or updates) the labels the refine/implement workflow uses. Idempotent.
set -euo pipefail
gh label create refined --force --color 0e8a16 --description "Refined plan; ready for /implement" >/dev/null
gh label create in-progress --force --color fbca04 --description "Claimed by an /implement session" >/dev/null
