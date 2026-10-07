#!/usr/bin/env bash
# Smoke check of a running ticket API: the main paths, and one failure path.
#   scripts/smoke.sh <base URL> <API key>
# Exits with 1 when a check fails. Prints no secret.
set -uo pipefail

url=${1:?Give the base URL, for example https://ticket-api-staging...}
key=${2:?Give the API key}
failed=0

check() {  # name, expected status, curl arguments...
  local name=$1 expected=$2; shift 2
  local status
  status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@")
  if [ "$status" = "$expected" ]; then
    echo "ok    $name ($status)"
  else
    echo "FAIL  $name: expected $expected, got $status"
    failed=1
  fi
}

check "health" 200 "$url/health"
check "ready" 200 "$url/ready"
check "classify with the key" 200 -X POST "$url/v1/classify" \
  -H 'Content-Type: application/json' -H "X-API-Key: $key" -d '{"subject":"Parcel lost"}'
check "classify without a key" 401 -X POST "$url/v1/classify" \
  -H 'Content-Type: application/json' -d '{"subject":"Parcel lost"}'

exit $failed
