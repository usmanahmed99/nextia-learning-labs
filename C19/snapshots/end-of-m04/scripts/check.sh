#!/usr/bin/env bash
# Run the same checks as the CI pipeline, on your computer, in the same order.
# Use it before you push. Needs the virtual environment (requirements-lock.txt)
# and Docker. Database tests run only when TEST_DATABASE_URL is set.
set -euo pipefail

step() { printf '\n== %s\n' "$1"; }

step "Lint"
ruff check .

step "Tests"
python -m pytest -q --junitxml=reports/junit.xml

step "Security: known vulnerabilities in the image's packages"
pip-audit -r requirements-run.txt --progress-spinner off

step "AI evaluation gate"
python -m evaluation.run --classifier 1.1

step "Build the image"
docker build -q -t ticket-api:check . >/dev/null

step "Smoke check of the image"
docker run -d --rm --name ticket-api-check -p 127.0.0.1:8099:8000 -e API_KEY=check-key ticket-api:check >/dev/null
trap 'docker stop ticket-api-check >/dev/null' EXIT
for _ in $(seq 1 20); do curl -fs http://127.0.0.1:8099/health >/dev/null && break; sleep 0.5; done
scripts/smoke.sh http://127.0.0.1:8099 check-key

printf '\nAll checks passed.\n'
