#!/usr/bin/env bash
# Deploy one image to a local environment, then smoke-check it.
#   scripts/promote-local.sh staging    ghcr.io/<you>/ticket-api-ci@sha256:...
#   scripts/promote-local.sh production ghcr.io/<you>/ticket-api-ci@sha256:...
# Needs .env (POSTGRES_PASSWORD) and secrets/<environment>_api_key.txt.
set -euo pipefail

environment=${1:?Give the environment: staging or production}
export IMAGE=${2:?Give the image with its digest}
settings="deploy/local/$environment.env"
[ -f "$settings" ] || { echo "No settings file $settings"; exit 1; }

docker compose -f deploy/local/compose.yaml --env-file "$settings" --env-file .env up -d --wait
port=$(grep '^PORT=' "$settings" | cut -d= -f2)
scripts/smoke.sh "http://127.0.0.1:$port" "$(cat "secrets/${environment}_api_key.txt")"
echo "$environment now runs $IMAGE"
