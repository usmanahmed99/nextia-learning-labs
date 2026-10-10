# Authentication, Permissions and Multi-Tenant Applications

Files for the course [Authentication, Permissions and Multi-Tenant Applications](https://learning.nextia-ai.com/courses/auth/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project `ticket-api`: `start` (the end of the databases course; download it in the first lesson) and the project at the end of each module. Code MIT; data CC0. |
| [`data/`](data) | The second shop, Bramble Books (customers, tickets, messages, files, AI runs, documents and ticket vectors), and the made-up people with their memberships, with a [dataset card](data/dataset.md) and the builder that makes them again. CC0. |
| [`M07-L01-audit-an-open-source-multi-tenant-app/`](M07-L01-audit-an-open-source-multi-tenant-app) | Case study 1, [Audit access control in an open-source multi-tenant app](https://learning.nextia-ai.com/courses/auth/m07/audit-an-open-source-multi-tenant-app/): the project `gitea-access-audit` as `starter.zip` (you write the access matrix and its tests) and `finished.zip`, and a [dataset card](M07-L01-audit-an-open-source-multi-tenant-app/dataset.md) for the app under test, Gitea (MIT), which runs in Docker on your computer with made-up people. Code MIT. |
| [`M07-L02-add-sign-in-and-roles-to-an-existing-api/`](M07-L02-add-sign-in-and-roles-to-an-existing-api) | Case study 2, [Add sign-in and roles to an existing API](https://learning.nextia-ai.com/courses/auth/m07/add-sign-in-and-roles-to-an-existing-api/): the project `city-requests-api` as `starter.zip` (the data API without sign-in) and `finished.zip`, the database of NYC 311 requests of two city departments in `data/` (with `SHA256SUMS`; the project's `scripts/get_db.py` downloads it and checks it) and a [dataset card](M07-L02-add-sign-in-and-roles-to-an-existing-api/dataset.md). Data: NYC Open Data, no restrictions on use. Code MIT. |

You need no account, no key and no money. PostgreSQL (with pgvector), the object storage (Azurite) and the identity provider run on your computer. The identity provider in the project (`idp/`) is a mock for practice: it does not ask for a password. A real provider is optional: `optional/keycloak/` in the snapshots from Module 3 runs Keycloak in Docker on your computer.

All the people, shops, tickets and files are made up for the course. Every attempt in the course to read or change what a person may not is harmless and targets only your own practice app.

## Tested

Tested with Python 3.12 on macOS (Apple silicon), Docker Desktop, PostgreSQL 18.6 with pgvector 0.8.7 and Azurite 3.37.0, in a new virtual environment and a new database for each snapshot: every snapshot's tests pass, and the stage's first commands run. The optional Keycloak route was tested with Keycloak 26.8.0. Windows and Linux are not tested. The route without Docker is not tested.

The two case studies were run on macOS from a fresh copy of their zips, in a new virtual environment: the finished projects' tests pass.
