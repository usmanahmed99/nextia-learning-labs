# Scaling APIs and AI Workloads

Files for the course [Scaling APIs and AI Workloads](https://learning.nextia-ai.com/courses/scaling/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project `ticket-api`: `start` (the end of the databases course; download it in the first lesson) and the project at the end of each module. Code MIT; data CC0. |
| [`data/`](data) | The recorded calls to a real hosted model that the simulated AI provider is calibrated from, with a [dataset card](data/dataset.md). CC0. |

You need no account, no key and no money. PostgreSQL, Valkey (the cache), the simulated AI provider and the load generator (Locust) all run on your computer. Run load tests only against your own services on your own computer. All of Larkfield's data is made up for the course: no real customer, ticket or file is in it.

## The simulated AI provider

The project has a small local service, `python -m simulator`, that answers like an OpenAI-compatible provider. It is not a model: its answers are simple (keywords choose the team; a reply comes from the recordings or from a template; a vector comes from the words of the text). Its **timing** and its **quota** are realistic: the times are drawn from 300 recorded real calls, and the quota (100 chat requests per minute, counted over about one minute) is what the real provider reported and enforced. The lessons say "simulated" every time they use it.

## Tested

Tested with Python 3.12 on macOS (Apple silicon), Docker Desktop (Engine 29.6.1), PostgreSQL 18.6 with pgvector 0.8.7 and Valkey 9.1.2, in a new virtual environment, a new database and an empty cache for each snapshot: every snapshot's tests pass, and the stage's first commands run. Windows and Linux are not tested. The route without Docker is not tested.
