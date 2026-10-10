#!/usr/bin/env bash
# Stop a local environment. Add --volumes to delete its database too.
#   scripts/stop-local.sh staging [--volumes]
set -euo pipefail
environment=${1:?Give the environment: staging or production}
shift
# compose.yaml needs IMAGE to read the file, but "down" does not use it.
IMAGE=unused docker compose -f deploy/local/compose.yaml \
  --env-file "deploy/local/$environment.env" --env-file .env down "$@"
