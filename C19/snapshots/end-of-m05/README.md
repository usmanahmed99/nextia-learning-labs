# ticket-api-ci

The reference project of [CI/CD, Testing and Safe Releases](https://learning.nextia-ai.com/courses/) (Nextia Learning, C19): the ticket API from C16 and C18, with a GitHub Actions pipeline that checks every change, builds one image per commit and promotes it to staging and production.

| Path | What it is |
|---|---|
| `.github/workflows/ci.yml` | Lint, unit/contract/database tests, pip-audit and the AI evaluation gate; then build, smoke-test and push the image, with `build-info.json` |
| `.github/workflows/deploy.yml`, `deploy-to.yml` | Promote one digest: staging, then production after approval. Each environment signs in to Azure with its own identity (OIDC) |
| `.github/workflows/release.yml` | A `v*` tag gives the tested image its version tag and makes the GitHub release; nothing is built again |
| `evaluation/` | The labelled tickets, the thresholds, the baseline and `python -m evaluation.run` |
| `migrations/`, `ticket_api/migrate.py` | Numbered SQL migrations and the runner |
| `deploy/local/`, `scripts/promote-local.sh` | Staging and production on your computer, each with its own database |
| `scripts/check.sh`, `scripts/smoke.sh` | The CI checks on your computer; the smoke check of a running API |
| `docs/release-process.md`, `docs/releases/` | Branches, checks, promotion, hotfix, rollback; the release notes |

The releases [v1.1.0](../../releases/tag/v1.1.0), [v1.2.0](../../releases/tag/v1.2.0) and [v1.2.1](../../releases/tag/v1.2.1), the pull requests and the workflow runs are the real ones that the course shows. The Azure practice resources were deleted after the test run on 2026-10-07, so the deployment URLs in the environments no longer answer.
