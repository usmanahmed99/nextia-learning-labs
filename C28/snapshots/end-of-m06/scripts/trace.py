"""See the real MCP messages: start the local server and talk to it by hand, one JSON line at a time.

    python -m scripts.trace discovery          the discovery requests and their answers
    python -m scripts.trace valid-call         one tool call that works
    python -m scripts.trace --list             every scenario
    python -m scripts.trace all --save traces  save each scenario as traces/<name>.jsonl

No SDK on the client side here: the messages are written by hand, so you see exactly what
travels on stdin (→, client to server) and stdout (←, server to client). The server's logs
go to stderr; this script shows them as "log" lines.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

VERSION = "2026-07-28"
CLIENT = {"name": "trace-script", "version": "1.0"}


def meta(version: str = VERSION) -> dict:
    """The envelope that every request carries in protocol 2026-07-28 (no handshake, no session)."""
    return {
        "io.modelcontextprotocol/protocolVersion": version,
        "io.modelcontextprotocol/clientInfo": CLIENT,
        "io.modelcontextprotocol/clientCapabilities": {},
    }


def req(i: int, method: str, params: dict | None = None, version: str = VERSION) -> dict:
    return {"jsonrpc": "2.0", "id": i, "method": method, "params": {**(params or {}), "_meta": meta(version)}}


def call(i: int, name: str, arguments: dict) -> dict:
    return req(i, "tools/call", {"name": name, "arguments": arguments})


SCENARIOS = {
    "discovery": [
        req(1, "server/discover"),
        req(2, "tools/list"),
        req(3, "resources/list"),
        req(4, "resources/templates/list"),
        req(5, "prompts/list"),
    ],
    "valid-call": [call(1, "get_ticket", {"ticket_id": "T-30002"})],
    "search": [call(1, "search_knowledge", {"query": "return a damaged item", "limit": 2})],
    "validation-failure": [call(1, "get_ticket", {"ticket_id": "30002"})],
    "unknown-tool": [call(1, "delete_ticket", {"ticket_id": "T-30002"})],
    "other-tenant": [call(1, "get_ticket", {"ticket_id": "T-40003"})],
    "resource-read": [
        req(1, "resources/read", {"uri": "policy://larkfield/gift-cards"}),
        req(2, "resources/read", {"uri": "policy://bramble/returns-policy"}),
    ],
    "prompt": [req(1, "prompts/get", {"name": "draft_reply", "arguments": {"ticket_id": "T-30002"}})],
    "write-refused": [call(1, "propose_refund", {"ticket_id": "T-30002", "amount": 25, "reason": "Charged twice"})],
    "version-mismatch": [req(1, "server/discover", version="2099-01-01")],
    "no-envelope": [{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}],
    "legacy-handshake": [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": CLIENT},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ],
    "legacy-old-version": [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-01-01", "capabilities": {}, "clientInfo": CLIENT},
        },
    ],
}


def run(name: str, messages: list[dict], env: dict | None = None, timeout: float = 15.0) -> list[dict]:
    """Start the server, send each message, wait for the answer to each request; return the events."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1", **(env or {})}
    proc = subprocess.Popen(
        [sys.executable, "-m", "support_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
    )
    events: list[dict] = []
    t0 = time.perf_counter()

    def ms() -> float:
        return round((time.perf_counter() - t0) * 1000, 1)

    def read_stderr():
        for line in proc.stderr:
            events.append({"t_ms": ms(), "dir": "log", "text": line.rstrip("\n")})

    threading.Thread(target=read_stderr, daemon=True).start()
    try:
        for m in messages:
            line = json.dumps(m, ensure_ascii=False)
            events.append({"t_ms": ms(), "dir": "->", "bytes": len(line.encode()) + 1, "message": m})
            proc.stdin.write(line + "\n")
            proc.stdin.flush()
            if "id" not in m:  # a notification: no answer
                continue
            deadline = time.perf_counter() + timeout
            while time.perf_counter() < deadline:
                out = proc.stdout.readline()
                if not out:
                    break
                answer = json.loads(out)
                events.append({"t_ms": ms(), "dir": "<-", "bytes": len(out.encode()), "message": answer})
                if answer.get("id") == m["id"]:
                    break
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    time.sleep(0.05)
    return sorted(events, key=lambda e: e["t_ms"])


def show(name: str, events: list[dict], width: int = 300) -> None:
    print(f"== {name}")
    for e in events:
        if e["dir"] == "log":
            print(f"   log {e['text'][:width]}")
        else:
            text = json.dumps(e["message"], ensure_ascii=False)
            print(f"{e['t_ms']:7.1f} ms {e['dir']} {text[:width]}{' …' if len(text) > width else ''}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.trace")
    p.add_argument("scenario", nargs="?", default="discovery")
    p.add_argument("--list", action="store_true")
    p.add_argument("--save", metavar="DIR")
    p.add_argument("--width", type=int, default=300)
    a = p.parse_args(argv)
    if a.list:
        print("\n".join(SCENARIOS))
        return 0
    names = list(SCENARIOS) if a.scenario == "all" else [a.scenario]
    for name in names:
        events = run(name, SCENARIOS[name])
        show(name, events, a.width)
        if a.save:
            out = Path(a.save)
            out.mkdir(parents=True, exist_ok=True)
            with (out / f"{name}.jsonl").open("w", encoding="utf-8") as f:
                for e in events:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
