"""How long does one local tool call take? stdio against Streamable HTTP, on this computer.

    python -m scripts.latency [--calls 200] [--passes 3]

It measures, with the SDK's client: get_ticket called again and again over one connection
(after a few warm-up calls), and the time to start a stdio server and get the discovery answer.
Times are for this computer only; they change with the computer and its load.
"""

import argparse
import json
import platform
import statistics
import sys
import time

import anyio
from mcp import Client

from host import app as host_app
from idp import keys
from scripts.local_http import serve_http


def pct(xs, p):
    xs = sorted(xs)
    return xs[max(0, min(len(xs) - 1, round(p / 100 * len(xs) + 0.5) - 1))]


async def calls(client: Client, n: int) -> list[float]:
    for _ in range(5):
        await client.call_tool("get_ticket", {"ticket_id": "T-30002"})
    out = []
    for _ in range(n):
        t = time.perf_counter()
        await client.call_tool("get_ticket", {"ticket_id": "T-30002"})
        out.append((time.perf_counter() - t) * 1000)
    return out


async def stdio_pass(n):
    async with Client(host_app.server_params("usr-sam", "larkfield")) as c:
        return await calls(c, n)


async def http_pass(url, tok, n):
    http, target = host_app.http_target(url, tok, "larkfield")
    async with http, Client(target) as c:
        return await calls(c, n)


async def start_times(k):
    out = []
    for _ in range(k):
        t = time.perf_counter()
        async with Client(host_app.server_params("usr-sam", "larkfield")) as c:
            await c.list_tools()
        out.append((time.perf_counter() - t) * 1000)
    return out


def summary(xs):
    return {
        "n": len(xs),
        "median_ms": round(statistics.median(xs), 2),
        "p95_ms": round(pct(xs, 95), 2),
        "min_ms": round(min(xs), 2),
        "max_ms": round(max(xs), 2),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.latency")
    p.add_argument("--calls", type=int, default=200)
    p.add_argument("--passes", type=int, default=3)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    res = {
        "machine": f"{platform.machine()} {platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "passes": [],
    }
    with serve_http() as url:
        tok = keys.access_token("usr-sam", "knowledge:read tickets:read", url)
        for _ in range(a.passes):
            s = anyio.run(stdio_pass, a.calls)
            h = anyio.run(http_pass, url, tok, a.calls)
            res["passes"].append({"stdio": summary(s), "http": summary(h)})
    res["start_stdio_server"] = summary(anyio.run(start_times, 10))
    res["stdio_median_ms"] = statistics.median(x["stdio"]["median_ms"] for x in res["passes"])
    res["http_median_ms"] = statistics.median(x["http"]["median_ms"] for x in res["passes"])
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    print(f"{a.calls} get_ticket calls per pass, {a.passes} passes, on {res['machine']}")
    for i, x in enumerate(res["passes"], 1):
        print(
            f"pass {i}: stdio median {x['stdio']['median_ms']} ms (p95 {x['stdio']['p95_ms']}), "
            f"HTTP median {x['http']['median_ms']} ms (p95 {x['http']['p95_ms']})"
        )
    print(f"median of the passes: stdio {res['stdio_median_ms']} ms, HTTP {res['http_median_ms']} ms")
    s = res["start_stdio_server"]
    print(f"start a stdio server and list its tools: median {s['median_ms']} ms (10 starts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
