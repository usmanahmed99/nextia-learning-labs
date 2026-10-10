# How a change reaches production

## Branches

We use **mainline development**: `main` is always releasable, and every change reaches it through a pull request.

| Branch | Made from | Merges into | Used for |
|---|---|---|---|
| `main` | | | The current code. Every commit on `main` is built once, and the image can go to production. |
| `feature/<short-name>` | `main` | `main`, by pull request | Every normal change. Short-lived: one change, merged within a few days. |
| `hotfix/<version>` | the release tag, for example `v1.2.0` | `main`, by pull request, after the release | An urgent fix to the version in production, when `main` already has changes that are not ready. |

A pull request names its source and target: for example, `feature/eval-gate` into `main`, or `hotfix/1.2.1` into `main`.

Releases are Git tags on `main` (or on a hotfix branch): `v1.1.0`, `v1.2.0`, `v1.2.1`. The version follows semantic versioning: the last number for a fix, the middle one for a new feature that does not break clients, the first one for a breaking change.

## Checks

| Check | What it proves | When |
|---|---|---|
| Lint (`ruff check .`) | The code has no simple mistakes, such as an unused import or a name that does not exist | Every pull request and every push |
| Unit and contract tests (`pytest`) | Each part does what it must; the API contract has not changed by accident | Every pull request and every push |
| Database tests (`pytest`, with PostgreSQL) | The migrations apply, and the history works with a real database | Every pull request and every push |
| Security (`pip-audit`) | No package in the image has a known vulnerability | Every pull request and every push |
| AI evaluation gate (`python -m evaluation.run`) | The classifier is not worse than the one in production, and every must-pass ticket is right | Every pull request and every push |
| Image smoke check (`scripts/smoke.sh`) | The built image starts and answers, before it leaves the CI runner | Every pull request and every push |
| Deployment smoke check | This deployment, with these settings, works | After each deployment, in each environment |

`scripts/check.sh` runs the same checks on your computer.

## From commit to production

1. A pull request runs every check. It can merge only when they pass.
2. A push to `main` runs the checks again, builds the image once, smoke-checks it, and pushes it to `ghcr.io/usmanahmed99/ticket-api-ci` with the tag `sha-<commit>`. `build-info.json` records the digest, the commit and the run.
3. The Deploy workflow deploys that digest to **staging** and smoke-checks it.
4. A reviewer approves the **production** deployment in GitHub. The same digest goes to production and is smoke-checked again.

Nothing is built again after step 2. Staging and production run the same image; only their settings differ.

## Hotfix

Use a hotfix when production has a bug that cannot wait for the next normal release, and `main` already has changes that are not ready.

1. Make the branch from the tag that production runs: `git switch -c hotfix/1.2.1 v1.2.0`.
2. Write a test that fails because of the bug. Then fix it, with the smallest change. Change the version (`1.2.1`) and write `docs/releases/1.2.1.md`.
3. Push the branch. CI runs every check and builds the image. **No check is skipped for a hotfix.**
4. Tag the commit (`v1.2.1`) and push the tag. The Release workflow tags the image that CI built.
5. Deploy that digest with the Deploy workflow (**Run workflow**, with the digest and the reason). It goes through staging, then production after approval.
6. Merge the hotfix branch into `main` with a pull request, so the next release keeps the fix.

## Rollback

| What went wrong | What to roll back | How | Time in the test run |
|---|---|---|---|
| The new code | The application | Deploy the previous digest with the Deploy workflow | about 2 minutes, through staging |
| The new model or a new feature behind a flag | Only the flag | `az containerapp update --set-env-vars CLASSIFIER_VERSION=1.0` | under 1 minute |
| Data that a release wrote wrongly | Nothing: repair forward | A new migration that corrects the data (for example `003_backfill_score`) | one migration |

A rollback of the application does not change the database. Every migration must keep the previous version working (expand first, contract later), so a rollback stays possible. Restore a database backup only when data is lost, and say what is lost since the backup.

Before a rollback, check what it takes away: rolling back from 1.2.x to 1.1.0 removes `score` from the responses, and turns off keywords-1.1, because 1.1.0 does not know the flag.
