# C19 snapshots: ticket-api-ci at the end of each module

Each folder is the project of [CI/CD, Testing and Safe Releases](https://learning.nextia-ai.com/courses/cicd/) at the end of one module. It is the reference repository [usmanahmed99/ticket-api-ci](https://github.com/usmanahmed99/ticket-api-ci) at one commit.

| Snapshot | Commit | Use it to start | What it has |
|---|---|---|---|
| [`end-of-m01`](end-of-m01) | [`da4e3f3`](https://github.com/usmanahmed99/ticket-api-ci/tree/da4e3f3) | Module 2 | C18's project, plus `docs/release-process.md`: branches, checks and promotion. |
| [`end-of-m02`](end-of-m02) | [`c862935`](https://github.com/usmanahmed99/ticket-api-ci/tree/c862935) | Module 3 | The CI pipeline `.github/workflows/ci.yml` (lint, tests, pip-audit; build, smoke-test and push the image), `scripts/check.sh`, `scripts/smoke.sh`, ruff settings. |
| [`end-of-m03`](end-of-m03) | [`92fff66`](https://github.com/usmanahmed99/ticket-api-ci/tree/v1.1.0) (v1.1.0) | Module 4 | The Deploy and Release workflows, the local environments in `deploy/local/`, `scripts/promote-local.sh`, the 1.1.0 release notes. |
| [`end-of-m04`](end-of-m04) | [`c3c7135`](https://github.com/usmanahmed99/ticket-api-ci/tree/v1.2.0) (v1.2.0) | Module 5 | The AI evaluation gate (`evaluation/`), classifier keywords-1.1 behind `CLASSIFIER_VERSION`, migrations, the `score` field, database tests. It still has the bug that Module 5 fixes. |
| [`end-of-m05`](end-of-m05) | [`30e0c7e`](https://github.com/usmanahmed99/ticket-api-ci/tree/30e0c7e) | The final assignment | Hotfix 1.2.1 merged back, migration 003, the hotfix and rollback procedures. |

In `end-of-m03` and `end-of-m04`, `deploy/local/compose.yaml` has `platform: linux/amd64`, as the lessons teach. The real repository added it later, in [pull request #6](https://github.com/usmanahmed99/ticket-api-ci/pull/6).

## What a snapshot does not have

- **GitHub settings.** A snapshot has files only. Make the settings again in your repository: the ruleset on `main` (Module 2), the environments `staging` and `production` with their variables, secret and required reviewer, and the repository variables (Module 3).
- **Images, containers, databases and cloud resources.** Your pipeline builds the images; Module 3 makes the environments.
- `.env`, `secrets/` and `.venv`. Make them as the project's `README.md` and the lessons say.

## Use a snapshot

1. Get the files (clone this repository, or download it as a ZIP file), as in [the C18 snapshots](../../C18/snapshots#use-a-snapshot).
2. In your own repository `ticket-api-ci`, make a new branch, for example `git switch -c restore-end-of-m03`.
3. Copy the snapshot's files over your project. Keep your `.git` folder: `cp -R nextia-learning-labs/C19/snapshots/end-of-m03/. ticket-api-ci/` (Windows: `Copy-Item -Recurse -Force nextia-learning-labs\C19\snapshots\end-of-m03\* ticket-api-ci\`).
4. Check the difference with `git status` and `git diff`, commit, push, and open a pull request. Your pipeline checks it like any other change.

## Tested

The snapshots are exported with `git archive` from the reference repository, whose CI ran green on each of these commits on 2026-10-07 (`end-of-m01` has no pipeline yet).
