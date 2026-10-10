# Capacity recommendation: new tickets on Black Friday (worked example)

The worked example of the scaling course, Module 6. Every number comes from the course's measurements on one laptop (Apple M4, 10 cores, 16 GB, macOS; PostgreSQL 18.6 and Valkey 9.1.2 in Docker), with the **simulated** AI provider: its times and its quota (100 chat requests per minute) come from recorded calls to a real hosted model. Medians of 3 to 5 passes; the ranges are in the course's measurement logs.

## The question

Can the service accept Black Friday's tickets, and give each one its AI work, without losing tickets?

## The workload (from `docs/workload.md`)

- Busiest hour x 10 (Omar's assumption): 1,010 tickets = 0.28 per second; a burst: 90 tickets in one minute.
- Each ticket: 2 chat calls + 1 embedding call, about 2.2 s of provider time.
- The provider's quota: 100 chat requests per minute = **at most 50 tickets per minute** (0.83 per second), whatever our own capacity.

## What we measured

| Configuration | Workload | Result |
|---|---|---|
| Module 1 design (one transaction, waits for the provider in the request) | 4 users without pause, quota as recorded, 60 s | 1.54 tickets/s answered, p95 3.1 s; the provider refused 41–115 calls per pass, and those customers got **503** and their ticket was **not saved** |
| Async in the request (no queue) | 10 tickets/s for 30 s (a strong burst), quota as recorded | about 55 of 300 tickets saved; **about 245 lost** (503 `ai_busy`) |
| Queue, 2 workers, no bound | the same burst | all 300 accepted in about 12 ms each; the queue grew to 225–230 jobs and needed several minutes to empty at the quota's pace |
| Queue, 2 workers, bound 100 | the same burst | 172–173 accepted; the rest got **503 `queue_full` with Retry-After 88–128 s**; the queue peaked at 107 jobs |

## Recommendation

1. **Use the queue (INTAKE_MODE=queue) with 2 workers.** The ticket is saved at once; its AI work follows at the provider's pace. More workers do not help: the quota, not the workers, limits the AI work. With the quota on, the local autoscaler started 4 workers and then went back to 1 while up to 116 jobs waited for the quota (the oldest for 119 s): the jobs that wait for the quota are not "ready", so a queue-length signal of ready jobs does not see them. Watch the age of the oldest job.
2. **Bound the queue** at what the provider can do in the time customers accept for the first reply. With the quota's 50 tickets per minute and a 5-minute promise, that is about 250 jobs. Above it, refuse with Retry-After instead of making a promise we cannot keep.
3. **Keep the circuit breaker on.** In a 20-second simulated outage, the worker without it used all 5 attempts of every job (150 calls, 30 dead letters); with it, 8 calls, and all 30 jobs succeeded afterwards.

## The next bottleneck

The provider's quota. Before the next change, measure: the real provider's times under our load (the simulator does not slow down with load; the real provider was about 30% slower with 40 calls in flight), and the quota after an increase is granted.

## What this test does not say

It ran on one laptop with a simulated provider and the small data. It does **not** say how many tickets production hardware can handle, or how a real provider behaves on Black Friday. It shows the shape: where tickets are lost, and which limit comes first.
