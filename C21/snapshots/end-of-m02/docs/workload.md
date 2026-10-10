# Workload model: new tickets on Black Friday

The worked example of the scaling course, Module 1. The numbers come from `python -m scripts.workload --factor 10` on the large practice data (300,000 made-up tickets over one year) and from the recorded calls to the AI provider. The factor 10 is Omar's estimate, not data: write it down as an assumption.

| Quantity | Normal day | Black Friday (x 10, assumed) | Where it comes from |
|---|---|---|---|
| Tickets per day | 822 on average, 899 on the busiest day | about 9,000 | `scripts.workload` |
| Tickets in the busiest hour | 101 | 1,010 = 0.28 per second | `scripts.workload` |
| Tickets in the busiest minute (a burst) | 9 | 90 = 1.5 per second | `scripts.workload` |
| Ticket text | median 125 characters (about 31 tokens), longest 196 | the same | `scripts.workload` |
| AI work per ticket | 2 chat calls (classify, draft a reply) + 1 embedding call | the same | `ticket_api/intake.py` |
| Time of the AI work, one ticket alone | about 2.2 s (classify 0.9 s + reply 1.1 s + embedding 0.2 s, medians) | longer when the provider is busy | the recorded calls |
| Provider quota (chat model) | 100 requests per minute | the same: it does not grow with our traffic | the provider's headers |
| What users expect | <write Omar's answer here: e.g. "the ticket is saved at once; the first reply within 5 minutes"> | | Omar |

What it means before any test:

- **Average load is small.** 0.28 tickets per second needs about 34 chat calls per minute: inside the quota.
- **Bursts are not.** 90 tickets in one minute need 180 chat calls: almost twice the quota. Without a plan, about half of those tickets get an error.
- **The AI work is slow compared with everything else.** One ticket waits about 2.2 s for the provider and a few milliseconds for the database.

The load tests of the course send this workload (and larger ones) to the service on your computer, never to a service that you do not own.
