# Benchmark result: <what you measured>

Copy this file for every measurement. A number without its workload and machine is not a result.

## The question

<One sentence: what you want to know. Example: "How many new tickets per second can one API process handle before p95 is over 5 seconds?">

## The machine

<The output of `python -m scripts.machine`, and what else was running. Close other heavy programs before you measure.>

## The workload

| | |
|---|---|
| Endpoint and request | <e.g. `POST /v1/tickets`, the practice data's tickets, picked with a fixed seed> |
| Load generator and command | <e.g. `locust -f loadtest/locustfile.py --headless -u 8 -r 8 -t 60s`> |
| Shape | <steady / ramp-up / burst / soak; users or arrival rate; duration; warm-up left out> |
| Dependencies | <database (size of the data), cache, AI provider: simulated (mode) or real> |
| Configuration | <processes, concurrency limits, pool size, queue bound, timeouts: everything you changed> |
| Passes | <how many, and how you summarize them (median of the passes)> |

## The results

| Configuration | Throughput (successful/s) | p50 ms | p95 ms | p99 ms | Errors (codes) | Resources (CPU, connections) | Cost per task |
|---|---|---|---|---|---|---|---|
| <baseline> | | | | | | | |
| <the change> | | | | | | | |

Variance: <the lowest and highest pass for the main number, e.g. "p95 between 2,410 and 2,630 ms in 5 passes">.

## What it means

- **What improved, and by how much:** <with the numbers above>.
- **What did not change or got worse:** <e.g. p99, errors, cost>.
- **The next bottleneck:** <what limits the system now, and the evidence>.
- **Limits of this test:** <what this local test cannot tell: production hardware, real traffic mix, real provider quotas, longer runs>.
