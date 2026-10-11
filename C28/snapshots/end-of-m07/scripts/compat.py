"""The compatibility matrix: which client, transport and protocol revision did we test, and what passed?

    python -m scripts.compat            a table
    python -m scripts.compat --json     the same as JSON

Each row runs the same checks against support-mcp: discovery, a valid call, a validation failure,
a resource read, the prompt, and (HTTP) a refused request without a token.
"""

import json
import sys
from importlib.metadata import version

import anyio
import httpx2
from mcp import Client, MCPError

from host import app as host_app
from host.models import MockModel
from idp import keys
from scripts.local_http import serve_http
from support_mcp.server import build_server

CHECKS = ["discovery", "valid_call", "validation_failure", "resource_read", "prompt", "host_answer"]


async def checks(client: Client) -> dict:
    out = {"protocol": client.protocol_version}
    tools = [t.name for t in (await client.list_tools()).tools]
    out["discovery"] = {"search_knowledge", "get_ticket"} <= set(tools)
    r = await client.call_tool("get_ticket", {"ticket_id": "T-30002"})
    out["valid_call"] = not r.is_error
    r = await client.call_tool("get_ticket", {"ticket_id": "30002"})
    out["validation_failure"] = bool(r.is_error)
    try:
        rr = await client.read_resource("policy://larkfield/gift-cards")
        out["resource_read"] = rr.contents[0].text.startswith("# Gift cards")
    except MCPError:
        out["resource_read"] = False
    p = await client.get_prompt("draft_reply", {"ticket_id": "T-30002"})
    out["prompt"] = "T-30002" in p.messages[0].content.text
    run = await host_app.ask(client, MockModel(), "What is the return window?", lambda n, a: False)
    out["host_answer"] = "policy://larkfield/" in run.answer
    return out


async def row(name: str, transport: str, target_factory, mode: str) -> dict:
    try:
        async with target_factory() as target:
            async with Client(target, mode=mode) as client:
                result = await checks(client)
    except Exception as e:  # a row that fails is a result too
        result = {"protocol": "-", "error": f"{type(e).__name__}: {e}"[:200]}
    return {"client": name, "transport": transport, "mode": mode} | result


class _Same:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *exc):
        return False


def matrix() -> list[dict]:
    sdk = f"MCP Python SDK {version('mcp')} Client"
    rows = []
    with serve_http() as url:
        tok = keys.access_token("usr-sam", "knowledge:read tickets:read", url)

        class Http:
            async def __aenter__(self):
                self.http, target = host_app.http_target(url, tok, "larkfield")
                await self.http.__aenter__()
                return target

            async def __aexit__(self, *exc):
                await self.http.__aexit__(*exc)

        async def all_rows():
            for mode in ("auto", "legacy"):
                rows.append(await row(sdk, "in-process", lambda: _Same(build_server()), mode))
                rows.append(
                    await row(sdk, "stdio", lambda: _Same(host_app.server_params("usr-sam", "larkfield")), mode)
                )
                rows.append(await row(sdk, "Streamable HTTP", Http, mode))

        anyio.run(all_rows)
        r = httpx2.post(
            url,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Accept": "application/json, text/event-stream"},
        )
        for x in rows:
            if x["transport"] == "Streamable HTTP":
                x["no_token_refused"] = r.status_code == 401
    return rows


def main(argv: list[str]) -> int:
    rows = matrix()
    if "--json" in argv:
        print(json.dumps(rows, indent=2))
        return 0
    cols = ["transport", "mode", "protocol", *CHECKS, "no_token_refused"]
    print(rows[0]["client"])
    print(" | ".join(cols))
    for x in rows:
        cells = []
        for c in cols:
            v = x.get(c, "-" if c == "no_token_refused" else x.get("error", "-"))
            cells.append(("pass" if v else "FAIL") if isinstance(v, bool) else str(v))
        print(" | ".join(cells))
    return 0 if all(all(x.get(c) is True for c in CHECKS) for x in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
