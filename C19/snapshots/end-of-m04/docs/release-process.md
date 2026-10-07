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
