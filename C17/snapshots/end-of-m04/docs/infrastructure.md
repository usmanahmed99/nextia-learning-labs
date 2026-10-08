# Infrastructure decision: escalation-service

Where Larkfield's escalation model runs, and why. Written by Amira on 2026-10-08
(Module 4 of the deployment course), with Priya (model), Grace (help desk) and Omar (product).
Change this file when one of its numbers changes.

## What the model needs

- Model: logistic regression with preprocessing, 28 weights. `model.joblib` is 5,354 bytes; the bundle is 45.1 kB.
- Time for one warm request on a laptop (Server-Timing): frame 0.66 ms, prepare 1.38 ms, model 0.05 ms. The whole request takes about 3 ms. The model is less than 2% of it.
- Memory: about 190 MiB for each worker (Python, scikit-learn, pandas, NumPy, SciPy, FastAPI). The libraries, not the model, set the size.
- A GPU would make only the model step faster (0.05 ms). Not needed.

## The load

- About 45 tickets a day (July: 1,400 tickets in 31 days), mostly from 07:00 to 22:00. The busiest hour had about 3 tickets on an average day.
- Online: an agent waits for the score when the ticket opens. Budget: p95 under 50 ms, network included (Online inference). Without an answer, the page opens without a score, and the nightly batch scores the ticket.

## The options (30 days, compute only)

Prices from the Azure Retail Prices API on 2026-10-08, canadacentral, USD, pay-as-you-go. Check again before deploying.

| Option | Cost for 30 days | Notes |
|---|---|---|
| Job on a schedule (batch) | about US$0 (free grant) | Nobody waits. Does not serve the help desk. Already used for the nightly file. |
| Azure Container Apps, 0.5 vCPU / 1 GiB, 1 replica | US$13.39 idle to US$46.87 always active | Scale to zero is possible, but the first request then waits for a cold start. |
| Azure ML managed online endpoint, 1 x Standard_D2as_v4 | US$77.04 | No scale to zero. Microsoft recommends 3 instances for production: US$231.12. |
| Managed endpoint with a GPU, 1 x Standard_NC4as_T4_v3 | US$420.48 | Saves about 0.05 ms per request. |

## The decision

- CPU only.
- One container on Azure Container Apps, as in the Docker course: 0.5 vCPU and 1 GiB, one worker (`WORKERS=1`).
  Checked on 2026-10-08 after the benchmark: no change (see below).
- At least one replica from 07:00 to 22:00, so that agents do not wait for a cold start.
- The bundle is baked into the image: each image holds the code and the model that were tested together.
- Revisit if: the load grows past what one worker serves inside the budget, the model becomes a neural network, or Larkfield serves several models (then compare a managed endpoint again).

## Check before we deploy

- [x] Memory per worker in a container with a limit (Container resource settings).
- [x] Cold start at 0.5 CPU (Container resource settings).
- [x] p50, p95 and throughput with a fixed workload (Benchmark the service).
- [ ] The cold start and the latency in the cloud, with the network (to measure after the first deployment).

## Measured on a laptop (2026-10-08)

Workload: `bench/bench.py`, 1,000 July tickets in file order, one ticket per request, 50 warm-up requests.
Computer: Apple silicon laptop, Docker Desktop, other programs running. Each number is the middle of five runs.

| Configuration | Concurrency 1: p50 / p95 / req/s | Concurrency 8: p50 / p95 / req/s | Memory |
|---|---|---|---|
| 1 worker, 1 CPU | 4.1 / 6.1 ms / 222 | 31.6 / 72.5 ms / 216 | 155 MiB |
| 1 worker, 0.5 CPU | 4.1 / 44.1 ms / 112 | 88.6 / 196.2 ms / 82 | 155 MiB |

- Cold start (docker run to /ready, image on the computer): 1 CPU 2.0 s, 0.5 CPU 3.5 s (median of 8 runs).
- Bottleneck: one worker uses one CPU. More requests at once only wait longer; throughput stays near 220 requests per second.
- At 0.5 CPU, p95 was 44 ms even with one request at a time, because the CPU limit pauses a busy container (throttling). The benchmark kept the service busy all the time. Larkfield's 45 tickets a day leave it idle almost all the time, so this is not the load we serve. We keep 0.5 vCPU, and we watch p95 in production (Module 5). If the load grows to keep the CPU busy, we move to 1 vCPU (US$28.94 to US$101.30 for 30 days).
- For the 50 ms budget, the open question is the network between the help desk and the service, which this benchmark does not include.
- Not measured here: the cloud network, the cloud's CPUs and the image download. Do not use these numbers as cloud numbers.
