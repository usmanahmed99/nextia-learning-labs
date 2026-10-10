# ticket-api: one API, two organizations, signed-in people

The project of [Authentication, Permissions and Multi-Tenant Applications](https://learning.nextia-ai.com/courses/auth/) (Nextia Learning). It is the ticket API of the API, Docker, CI/CD and databases courses. In this course it serves two shops, Larkfield and Bramble Books, from one database: people sign in through an identity provider, every request is checked on the server (who, in which organization, with which role), and tests try every person against every route.

All the people, shops, tickets and files are made up for the course. The identity provider in `idp/` is a mock for practice: it does not ask for a password.

## What you need

- Python 3.12 or later.
- PostgreSQL 18 with pgvector, and Azurite (the files), in Docker: as in the databases course. Without Docker, see [Without Docker](#without-docker).

You do not need an account, a key or money.

## Set up

macOS and Linux:

```sh
cp .env.example .env              # then change the password in .env (three places)
docker compose up -d db azurite   # PostgreSQL with pgvector; Azurite for the files
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.load            # the migrations, then the data of both shops
python -m idp init                # the practice provider's keys and secrets (into .env)
python -m pytest
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env       # then change the password in .env (three places)
docker compose up -d db azurite
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.load
python -m idp init
python -m pytest
```

Then run the provider and the API, each in its own terminal (venv active in both):

```sh
python -m idp                     # the practice identity provider on http://localhost:8400
fastapi dev                       # the API on http://127.0.0.1:8000
```

Open http://127.0.0.1:8000/app/ and sign in as one of the made-up people. Or get a token on the command line and call the API with it:

```sh
python -m scripts.login --user usr-sam
curl -H "Authorization: Bearer $(python -m scripts.login --user usr-sam --print-access-token)" http://127.0.0.1:8000/v1/me
```

PowerShell: `$t = python -m scripts.login --user usr-sam --print-access-token; curl.exe -H "Authorization: Bearer $t" http://127.0.0.1:8000/v1/me`.

**Reset:** `python -m scripts.load --reset` loads the data of both shops again. `python -m idp init --force` makes new keys and secrets. `docker compose down --volumes` deletes the database and the files.

## The people

| User ID | Name | Larkfield | Bramble Books |
|---|---|---|---|
| `usr-grace` | Grace | owner | – |
| `usr-sam` | Sam | staff | – |
| `usr-omar` | Omar | read_only | – |
| `usr-camille` | Camille | staff | read_only |
| `usr-ines` | Ines | – | owner |
| `usr-tomas` | Tomás | – | – |
| `usr-kwame` | Kwame | platform administrator: no organization | |

## Commands

| Command | What it does | Module |
|---|---|---|
| `python -m scripts.load [--size large] [--reset]` | the migrations and the data of both shops | 1 |
| `python -m scripts.access_matrix [--user usr-camille]` | what each role and each person may do | 1 |
| `python -m scripts.attempts` | made-up attempts to read or change what a person may not | 1, 4 |
| `python -m idp init` / `python -m idp` | set up and run the practice identity provider | 2 |
| `python -m scripts.login --user usr-sam` | sign in step by step (authorization code with PKCE) | 2 |
| `python -m scripts.token decode --user usr-sam` | look inside a token | 2 |
| `python -m scripts.token cases` | made-up bad tokens, and the check that refuses each | 2 |
| `python -m idp rotate-key`, `disable usr-sam`, `users` | change the provider's keys and people | 2, 5 |
| `python -m scripts.check_identity` | check the sign-in settings against the provider | 3 |
| `python -m scripts.leak_demo all` | what leaks without the organization in a search, a cache key or a file link | 4 |
| `python -m scripts.rls_demo` | row-level security, step by step | 4 |
| `python -m scripts.bench [--row-security off]` | measure the ticket list | 4 |
| `python -m scripts.worker [--once]` | run the background jobs | 5 |
| `python -m scripts.lifecycle all` | how long access lasts after a change | 5 |
| `python -m scripts.audit [--check]` | the audit events | 5, 6 |
| `python -m scripts.matrix_report` | the access-control test report (`docs/test-report.md`) | 6 |

The databases course's commands still work (`scripts.explain`, `scripts.backup`, `scripts.scan`, ...).

## Without Docker

As in the databases course: PostgreSQL 18 and pgvector from their installers, a `tickets` role with `SUPERUSER` (practice only: the migrations create the `vector` extension and the role `ticket_app`), and Azurite with `npm install -g azurite`. This route is not tested.

## Files

| Path | What it is |
|---|---|
| `idp/` | the practice identity provider (discovery, keys, sign-in, tokens) |
| `ticket_api/` | the API; from this course: `access.py` (the matrix), `auth.py` (token checks), `sessions.py` and `login.py` (browser sign-in), `tenancy.py` (the check before every route), `members.py`, `jobs.py`, `worker.py`, `admin.py`, `audit.py` |
| `migrations/` | 013–019: organizations and people, tenant columns, sessions, indexes, row-level security, jobs, audit |
| `data/` | the made-up data: Larkfield (`small/`, `large/`), Bramble Books (`bramble/`), the people (`identity/`) |
| `docs/` | the access matrix, the identity configuration, the handoff and the test report |
| `optional/keycloak/` | the same API with a real identity provider (Keycloak, in Docker) |

Code: MIT licence. Data: CC0.
