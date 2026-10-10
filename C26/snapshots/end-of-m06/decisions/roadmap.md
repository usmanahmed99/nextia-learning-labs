# Implementation roadmap

Each step starts when its signal says so, not on a date. Each step names the decisions it builds on.

## Release 1: the first usable assistant (Larkfield and Bramble Books)

- One modular application with the API and the ingestion worker (ADR-0001).
- PostgreSQL for records, vectors, the queue and the answer cache, with row-level security (ADR-0002).
- chat-small answers every question (ADR-0003).
- Managed PostgreSQL (ADR-0004) with point-in-time restore and the first restore test (ADR-0005).
- Done when: Q1 to Q8 are measured for two weeks and each one meets its target.

## Validation work (during release 1)

- Replace the assumed demand with the usage log: questions per user, customers per day, repeats (the cache hit share).
- Build an evaluation set for Bramble Books (Priya) and run it before every model or prompt change.
- Run the first restore test and write the real RTO into ADR-0005.
- Decide with Omar whether customers see the assistant on the home page (the high scenario). If yes, ask the provider for a higher quota before launch: the high scenario needs more than the quota in its busiest minute (ADR-0003).

## Release 2: the third and fourth shops

- Add a tenant with the tenant checklist (J5), no code change.
- Start when: a third shop signs; the cost model says the cost per tenant falls (fixed costs are shared).

## Later, only when a signal fires

The first three signals are printed by `python -m costmodel growth`; the others come from the logs, the evaluation set and the team list.

| Signal | Step | Decision to revisit |
|---|---|---|
| the busiest minute uses 70% of the provider quota | ask for a higher quota; queue answers for customers | ADR-0003 |
| the database uses 80% of its storage | a bigger storage size (a setting) | ADR-0004 |
| the monthly cost passes the budget (US$150) | find the biggest driver in the cost table first (today: the API replica) | the decision behind that driver |
| search p95 > 100 ms or 5 million chunks | tune the index; then consider a separate vector store | ADR-0002 |
| a new question set shows chat-strong 5 points better | switch routing on | ADR-0003 |
| more than 4 API replicas at the busiest minute, or ingestion needs a GPU, or a second team | split that part into its own service | ADR-0001 |
