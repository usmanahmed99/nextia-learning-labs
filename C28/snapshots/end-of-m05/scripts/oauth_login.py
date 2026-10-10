"""The official MCP authorization flow, end to end, with the SDK's OAuth client (no browser).

    python -m scripts.oauth_login [--user usr-sam]

It starts the practice identity provider and the HTTP server (free ports, inside this script),
then connects with the MCP Python SDK's OAuthClientProvider, which does every step itself:
401 from the server -> protected resource metadata -> the provider's metadata -> client
registration -> the authorization code flow with PKCE (S256) and the resource -> the token ->
the MCP request again, with the token. The sign-in page is skipped with login_hint (a practice
shortcut: a real application opens the page in the person's browser).
"""

import argparse
import sys
import urllib.parse

import anyio
import httpx2
from mcp import Client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.auth.oauth2 import AuthorizationCodeResult
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from idp import app as idp_app
from idp import keys
from scripts.local_http import free_port, serve_app, serve_http

REDIRECT = "http://127.0.0.1:8765/callback"


class Memory(TokenStorage):
    def __init__(self):
        self.tokens, self.client = None, None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client = client_info


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m scripts.oauth_login")
    p.add_argument("--user", default="usr-sam")
    a = p.parse_args(argv)
    idp_port = free_port()
    keys.ISSUER = f"http://127.0.0.1:{idp_port}"
    steps: list[str] = []
    location: dict = {}

    async def redirect_handler(url: str) -> None:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        steps.append(
            f"authorize: client {q['client_id'][0]}, scope '{q.get('scope', [''])[0]}', "
            f"resource {q.get('resource', ['-'])[0]}, PKCE {q.get('code_challenge_method', ['-'])[0]}"
        )
        r = httpx2.get(url + "&login_hint=" + a.user)  # the practice shortcut: no sign-in page
        location["url"] = r.headers["location"]

    async def callback_handler():
        q = urllib.parse.parse_qs(urllib.parse.urlparse(location["url"]).query)
        steps.append("callback: got an authorization code")
        return AuthorizationCodeResult(code=q["code"][0], state=q.get("state", [None])[0])

    async def log_request(r):
        steps.append(f"{r.method} {r.url.path}{'  (with a token)' if 'authorization' in r.headers else ''}")

    async def log_response(r):
        steps[-1] += f" -> {r.status_code}"

    with serve_app(idp_app.app, idp_port), serve_http() as url:
        idp_app.RESOURCES.add(url)

        async def go():
            storage = Memory()
            auth = OAuthClientProvider(
                server_url=url,
                client_metadata=OAuthClientMetadata(
                    client_name="support-host",
                    redirect_uris=[REDIRECT],
                    grant_types=["authorization_code"],
                    response_types=["code"],
                    token_endpoint_auth_method="none",
                    scope="knowledge:read tickets:read",
                ),
                storage=storage,
                redirect_handler=redirect_handler,
                callback_handler=callback_handler,
            )
            http = httpx2.AsyncClient(
                auth=auth,
                headers={"X-Support-Tenant": "larkfield"},
                event_hooks={"request": [log_request], "response": [log_response]},
            )
            async with http, Client(streamable_http_client(url, http_client=http)) as client:
                r = await client.call_tool("get_ticket", {"ticket_id": "T-30002"})
                return r, storage.tokens

        result, tokens = anyio.run(go)
    port = url.split(":")[2].split("/")[0]
    for s in steps:
        print(s.replace(f":{port}", ":<server>").replace(f":{idp_port}", ":<provider>"))
    print(f"token: {tokens.token_type}, expires in {tokens.expires_in} s, scope '{tokens.scope}'")
    print(f"get_ticket T-30002 -> {'error' if result.is_error else 'ok'}: {result.structured_content['subject']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
