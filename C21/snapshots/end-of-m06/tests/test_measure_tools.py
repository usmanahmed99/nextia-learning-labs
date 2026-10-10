"""The measuring tools of Module 1: percentiles, Server-Timing, the workload."""

from scripts import percentiles, workload
from ticket_api.timing import Timer, parse


def test_nearest_rank_percentiles():
    values = sorted(float(v) for v in range(1, 101))  # 1 ... 100 ms
    assert percentiles.nearest_rank(values, 50) == 50
    assert percentiles.nearest_rank(values, 95) == 95
    assert percentiles.nearest_rank(values, 99) == 99


def test_the_average_hides_the_slow_requests():
    rows = [{"start": str(i * 0.1), "status": "201", "ms": "100"} for i in range(95)]
    rows += [{"start": str(9.5 + i * 0.1), "status": "201", "ms": "5000"} for i in range(5)]
    s = percentiles.summarize(rows)
    assert s["p50_ms"] == 100 and s["p95_ms"] == 100 and s["p99_ms"] == 5000
    assert s["mean_ms"] == 345.0  # nobody waited 345 ms


def test_failed_requests_are_not_throughput():
    rows = [
        {"start": "0", "status": "201", "ms": "1000"},
        {"start": "0", "status": "503", "ms": "5"},
    ]
    s = percentiles.summarize(rows)
    assert s["ok"] == 1 and s["statuses"] == {"201": 1, "503": 1}


def test_server_timing_round_trip():
    t = Timer()
    with t("db"):
        pass
    with t("classify"):
        pass
    assert list(parse(t.header())) == ["db", "classify"]


def test_workload_of_the_small_data(conn):
    w = workload.describe(conn, factor=10)
    assert w["tickets"] == 200 and w["days"] == 14
    assert w["busiest_hour"] == 5
    assert round(w["chat_calls_per_minute"], 2) == round(5 * 10 / 60 * 2, 2)
