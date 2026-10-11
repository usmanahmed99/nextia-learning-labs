"""Who may do what? Send real requests to the HTTP server as different callers and see which check
refuses each one. Everything runs on your computer, with made-up people and synthetic data.

    python -m scripts.attempts            the table
    python -m scripts.attempts --json     every attempt with the server's answer

The server runs inside this script (a free port) with a practice signing key, like the tests.
"""

import argparse
import json
import sys
import time

import anyio
import httpx2
from mcp import Client, MCPError

from host import app as host_app
from idp import keys
from scripts.local_http import serve_http
from support_mcp import writes

READ = "knowledge:read tickets:read"
ALL = "knowledge:read tickets:read refunds:propose"

# (who, organization header, token kind, scopes)
CALLERS = [
    ("usr-grace", "larkfield", "valid", ALL),
    ("usr-sam", "larkfield", "valid", ALL),
    ("usr-sam", "larkfield", "valid", "knowledge:read"),
    ("usr-omar", "larkfield", "valid", ALL),
    ("usr-camille", "larkfield", "valid", ALL),
    ("usr-camille", "bramble", "valid", ALL),
    ("usr-ines", "bramble", "valid", ALL),
    ("usr-ines", "larkfield", "valid", ALL),
    ("usr-tomas", "larkfield", "valid", ALL),
    ("usr-sam", "larkfield", "none", READ),
    ("usr-sam", "larkfield", "wrong_audience", READ),
    ("usr-sam", "larkfield", "expired", READ),
]

REQUESTS = [
    ("search policies", "tool", "search_knowledge", {"query": "refund double charge"}),
    ("read a Larkfield ticket", "tool", "get_ticket", {"ticket_id": "T-30002"}),
    ("read a Bramble ticket", "tool", "get_ticket", {"ticket_id": "T-40003"}),
    ("read the staff-only procedure", "resource", "policy://larkfield/refund-approval-procedure", None),
    (
        "propose a 25-dollar refund",
        "tool",
        "propose_refund",
        {"ticket_id": "T-30002", "amount": 25, "reason": "Charged twice"},
    ),
    (
        "propose a 450-dollar refund",
        "tool",
        "propose_refund",
        {"ticket_id": "T-30002", "amount": 450, "reason": "Charged twice"},
    ),
]


def which_check(status: str, message: str) -> str:
    m = message.lower()
    for key, name in [
        ("http 401", "token (signature, issuer, audience, expiry)"),
        ("http 403", "scope (the token does not allow it)"),
        ("no access to this organization", "membership (no membership here)"),
        ("insufficient_scope", "scope (the token does not allow it)"),
        ("cannot propose", "role (the membership's role)"),
        ("not_found", "organization-scoped lookup (not in this organization)"),
        ("resource not found", "role (the membership's role)"),  # the staff-only document: hidden from read_only
        ("over_limit", "business limit (the agent's refund limit)"),
        ("pending_approval", "allowed, but only proposed: a person must approve"),
    ]:
        if key in m:
            return name
    return "allowed" if status == "ok" else "other"


def token_for(url: str, user: str, kind: str, scopes: str) -> str | None:
    if kind == "none":
        return None
    if kind == "wrong_audience":
        return keys.access_token(user, scopes, "ticket-api")
    if kind == "expired":
        return keys.access_token(user, scopes, url, now=time.time() - 3600)
    return keys.access_token(user, scopes, url)


async def attempt(url: str, tok: str | None, tenant: str, req) -> tuple[str, str]:
    label, kind, name, args = req
    http, target = host_app.http_target(url, tok or "", tenant)
    try:
        async with http, Client(target) as client:
            try:
                if kind == "tool":
                    r = await client.call_tool(name, args)
                    text = r.content[0].text if r.content else ""
                    if r.is_error:
                        return "tool_error", text
                    return "ok", json.dumps(r.structured_content) if r.structured_content else text
                r = await client.read_resource(name)
                return "ok", r.contents[0].text[:60]
            except MCPError as e:
                return "refused", f"{e.error.code} {e.error.message}"
    except Exception:  # the HTTP layer refused before MCP (401)
        r = httpx2.post(
            url,
            headers={
                "Accept": "application/json, text/event-stream",
                **({"Authorization": f"Bearer {tok}"} if tok else {}),
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        return "refused", f"HTTP {r.status_code} {r.headers.get('www-authenticate', '')}"


def run_all() -> list[dict]:
    rows = []
    with serve_http() as url:
        for user, tenant, kind, scopes in CALLERS:
            for req in REQUESTS:
                tok = token_for(url, user, kind, scopes)
                status, message = anyio.run(attempt, url, tok, tenant, req)
                rows.append(
                    {
                        "user": user,
                        "tenant": tenant,
                        "token": kind,
                        "scopes": scopes,
                        "request": req[0],
                        "status": status,
                        "check": which_check(status, message),
                        "answer": message[:300],
                    }
                )
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.attempts")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    rows = run_all()
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    last = None
    for r in rows:
        who = f"{r['user']} @ {r['tenant']} (token: {r['token']}, scopes: {r['scopes']})"
        if who != last:
            print(f"\n{who}")
            last = who
        print(f"  {r['request']:<32} {r['status']:<10} {r['check']}")
    allowed = sum(r["status"] == "ok" for r in rows)
    print(f"\n{len(rows)} attempts: {allowed} allowed, {len(rows) - allowed} refused on the server.")
    print(f"Refunds recorded: {len(writes.refunds())} (proposals only wait for an owner).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
