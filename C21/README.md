# Scaling APIs and AI Workloads

Files for the course [Scaling APIs and AI Workloads](https://learning.nextia-ai.com/courses/scaling/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project `ticket-api`: `start` (the end of the databases course; download it in the first lesson) and the project at the end of each module. Code MIT; data CC0. |
| [`data/`](data) | The recorded calls to a real hosted model that the simulated AI provider is calibrated from, with a [dataset card](data/dataset.md). CC0. |
| [`M07-L01-capacity-plan-from-a-public-traffic-trace/`](M07-L01-capacity-plan-from-a-public-traffic-trace) | Case study 1, [Capacity plan from a public traffic trace](https://learning.nextia-ai.com/courses/scaling/m07/capacity-plan-from-a-public-traffic-trace/): a notebook and its solution, the arrival times of San Francisco's 311 requests of 2025 and of June 2026 (PDDL 1.0) with a [dataset card](M07-L01-capacity-plan-from-a-public-traffic-trace/dataset.md), and `replay_trace.py`, which sends a part of the trace to the course project on your computer. Code MIT. |
| [`M07-L02-queue-and-cache-for-an-open-data-api/`](M07-L02-queue-and-cache-for-an-open-data-api) | Case study 2, [Queue and cache for an open-data API](https://learning.nextia-ai.com/courses/scaling/m07/queue-and-cache-for-an-open-data-api/): the project `city-requests-scaling` as `starter.zip` (the files you write are missing) and `finished.zip` (the whole project), with a [dataset card](M07-L02-queue-and-cache-for-an-open-data-api/dataset.md). The project downloads New York City's 311 street-repair requests (NYC Open Data) from this repository and checks their SHA-256. Code MIT. |

The case studies use real open data, not Larkfield's, and need an internet connection for their setup steps. The notebook checks the SHA-256 of every file that it downloads.

You need no account, no key and no money. PostgreSQL, Valkey (the cache), the simulated AI provider and the load generator (Locust) all run on your computer. Run load tests only against your own services on your own computer. All of Larkfield's data is made up for the course: no real customer, ticket or file is in it.

## The simulated AI provider

The project has a small local service, `python -m simulator`, that answers like an OpenAI-compatible provider. It is not a model: its answers are simple (keywords choose the team; a reply comes from the recordings or from a template; a vector comes from the words of the text). Its **timing** and its **quota** are realistic: the times are drawn from 300 recorded real calls, and the quota (100 chat requests per minute, counted over about one minute) is what the real provider reported and enforced. The lessons say "simulated" every time they use it.

## Tested

Tested with Python 3.12 on macOS (Apple silicon), Docker Desktop (Engine 29.6.1), PostgreSQL 18.6 with pgvector 0.8.7 and Valkey 9.1.2, in a new virtual environment, a new database and an empty cache for each snapshot: every snapshot's tests pass, and the stage's first commands run. Windows and Linux are not tested. The route without Docker is not tested.

The case-study notebook and its solution ran from a fresh start in a new virtual environment. The case-study project ran from fresh copies of its starter and finished stages, with a new database and an empty cache: its tests pass, and the commands on its page run.
