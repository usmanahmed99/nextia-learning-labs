"""Exact latency percentiles from a load test's samples (one line per request).

    SAMPLES_CSV=run.csv locust -f loadtest/locustfile.py ... --headless
    python -m scripts.percentiles run.csv [--skip 5]

--skip leaves out the first seconds (the warm-up). Throughput counts only successful
requests (2xx): failed requests are not useful work. A percentile here is the nearest
rank: p95 is the time that 95 of 100 requests did not exceed.
"""

import argparse
import csv
import math
import statistics
import sys


def nearest_rank(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    k = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[k - 1]


def summarize(rows: list[dict], skip: float = 0.0) -> dict:
    if not rows:
        raise SystemExit("No samples.")
    t0 = min(float(r["start"]) for r in rows)
    rows = [r for r in rows if float(r["start"]) - t0 >= skip]
    starts = [float(r["start"]) for r in rows]
    ends = [float(r["start"]) + float(r["ms"]) / 1000 for r in rows]
    seconds = max(ends) - min(starts)
    ok = sorted(float(r["ms"]) for r in rows if 200 <= int(r["status"]) < 300)
    statuses: dict[str, int] = {}
    for r in rows:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    return {
        "requests": len(rows),
        "seconds": round(seconds, 1),
        "ok": len(ok),
        "statuses": dict(sorted(statuses.items())),
        "throughput_ok_per_s": round(len(ok) / seconds, 2) if seconds else 0.0,
        "mean_ms": round(statistics.fmean(ok), 1) if ok else None,
        "p50_ms": nearest_rank(ok, 50),
        "p95_ms": nearest_rank(ok, 95),
        "p99_ms": nearest_rank(ok, 99),
        "max_ms": ok[-1] if ok else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("samples")
    parser.add_argument("--skip", type=float, default=0.0, help="seconds of warm-up to leave out")
    args = parser.parse_args(argv)
    with open(args.samples, encoding="utf-8") as f:
        s = summarize(list(csv.DictReader(f)), args.skip)
    print(f"{s['requests']} requests in {s['seconds']} s; status codes {s['statuses']}")
    print(f"Successful: {s['ok']} = {s['throughput_ok_per_s']} per second")
    if s["ok"]:
        print(
            f"Latency of the successful requests: mean {s['mean_ms']} ms | p50 {s['p50_ms']} ms | "
            f"p95 {s['p95_ms']} ms | p99 {s['p99_ms']} ms | max {s['max_ms']} ms"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
