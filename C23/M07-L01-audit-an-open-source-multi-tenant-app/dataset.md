# Dataset card: Gitea (the application under test)

Used by: the case study *Audit access control in an open-source multi-tenant app*, project
`gitea-access-audit` (starter.zip / finished.zip).

This case study audits an application, not a data file. The "dataset" is the open-source app
you run on your own computer. All users and records are made up by the project's seed script.

| Field | Value |
|---|---|
| Source | <https://github.com/go-gitea/gitea> (project site <https://about.gitea.com/>) |
| Publisher / creator | The Gitea Authors |
| Licence | MIT — <https://github.com/go-gitea/gitea/blob/v28.1.0/LICENSE> |
| Attribution text | "Gitea (c) The Gitea Authors, MIT licence." |
| Version | 28.1.0 (released 2026-10-06); tag commit `4ebd5e319b6a9e629bfd7a04292a6fe85b08dee9` |
| Image used | `gitea/gitea:28.1.0`, pinned by digest in `compose.yaml` |
| Image digest (SHA-256) | `f505a0d3a41323b786e05942fc7a4075e07ae7c169fd9485649aa55ee543a21a` |
| Size | one container, SQLite; about 120 MiB of memory in use (capped at 512 MB), ~70 MB image |

## What the app is

Gitea is a self-hosted Git service, like a small GitHub. It has **organizations** (tenants),
**teams** inside an organization that carry a role (read, write or admin), **members**,
private **repositories**, and records inside them: issues, comments and file attachments. A
**site administrator** can see every organization. This matches the course's model closely.

## Why this app

It is MIT-licensed, maintained, small enough to run in one container under 2 GB, and it has
every feature the audit needs: records with guessable global IDs, roles, file links, an export
(repository archive), token scopes, and a built-in audit log. The full comparison with other
candidates is in the author's `DATASET-RESEARCH.md`.

## The synthetic data

`python -m audit.seed` makes two organizations (`larkfield`, `bramble`), seven people with the
course's names and roles (Camille belongs to both with different roles), one private repository
per organization, two issues each, a comment and a file. Nothing is real. The people's tokens
are made on the local server and are for your own computer only.

## Changes we made

None to Gitea. We only change its settings through `compose.yaml` (install locked, registration
off, sign-in required to view, the audit log turned on — it is off by default).

## Limitations and cautions

- This is **not a full security audit of Gitea**. It tests the routes in `audit/matrix.py`
  with the course's three questions. A complete audit would also test cross-references,
  search, webhooks, notifications, packages, the web UI and the Git protocol.
- Run it only against your own local instance, with the synthetic users. Never point it at a
  server you do not own.
- The version is pinned. A newer Gitea may answer differently; re-pin and re-run before
  drawing conclusions.
