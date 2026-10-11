# ADR-0001: One modular application with a background worker

## Status

Accepted. Kwame, with Amira.

## Context

The assistant has an interactive part (answers, J1 and J2) and a slow part (ingestion, J3). Tomás proposed separate services (an answer service, an ingestion service, a search service) on Kubernetes. Demand is small and uncertain: 1,465 questions a day in the base scenario, 0.58 requests in flight at the busiest minute (cost model, from measured times). One developer (Amira) maintains it (Q6).

## Options

1. One application, two processes: the API and an ingestion worker from the same code, the queue in PostgreSQL. One deployment, one set of tests.
2. Three services with their own deployments and an HTTP or message link between them. Each can scale alone; three pipelines, three sets of logs, network calls that can fail between them.
3. Kubernetes with the three services. All of option 2, plus a cluster to run.

## Decision

Option 1: one modular application (modules `answers`, `ingestion`, `search`, `tenants`) that runs as an API process and a worker process.

## Consequences

- One deployment and one test suite; the modules call each other as functions, not over the network.
- The worker can still run on its own and scale to zero, because it reads jobs from the queue.
- A split later is cheaper because the modules already have clear boundaries.

## Revisit when

- Ingestion needs a different machine (for example a GPU) or a different release rhythm from the API, or
- the API needs more than 4 replicas at the busiest minute, or
- a second team owns part of the code.
