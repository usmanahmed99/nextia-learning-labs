# Databases and Storage for AI Applications

Files for the course [Databases and Storage for AI Applications](https://learning.nextia-ai.com/courses/databases/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project `ticket-api`: `start` (download it in the first lesson) and the project at the end of each module. Code MIT; data CC0. |
| [`data/`](data) | Larkfield's made-up help-desk data, with a [dataset card](data/dataset.md): the small data (every file), the generator of the large data, and the vectors of the large data. CC0. |
| [`optional/orm/`](optional/orm) | An optional comparison: the same ticket page with SQLAlchemy, an ORM. Not needed for the course. MIT. |

You need no account and no key. PostgreSQL (with pgvector) and the object storage (Azurite) run on your computer, in Docker or without it. All the data is made up for the course: no real customer, ticket or file is in it.

## The large data

The large data (300,000 tickets) is 234 MB of CSV files, too large for this repository. Your computer makes it: `python -m scripts.load --size large` runs `data/generate.py` (about 15 seconds; no network) and checks every file against `data/large/SHA256SUMS`. The same command always makes the same bytes. Only its ticket vectors (15 MB) come from here, from [`data/large/`](data/large): an embedding model made them, and the loader downloads them once and checks their SHA-256.

## Tested

Tested on 2026-10-09 and 2026-10-10 with Python 3.12 on macOS (Apple silicon), Docker Desktop 4.81.0, PostgreSQL 18.6 with pgvector 0.8.7 and Azurite 3.37.0, in a new virtual environment and a new database for each snapshot: every snapshot's tests pass, and the stage's first commands run. Windows and Linux are not tested. The route without Docker is not tested.
