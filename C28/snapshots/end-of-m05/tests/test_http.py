"""Remote access: Streamable HTTP with access tokens. Every refusal happens on the server."""

import time

import anyio
import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import Client, MCPError

from host import app as host_app
from idp import keys
from support_mcp.http import JwtVerifier, build_app
from tests.conftest import Served, free_port

ISSUER = keys.ISSUER


@pytest.fixture
def server():
    port = free_port()
    url = f"http://127.0.0.1:{port}/mcp"
    verifier = JwtVerifier(ISSUER, url, jwks=keys.jwks())
    with Served(build_app(verifier, issuer=ISSUER, resource_url=url), port):
        yield url


def token(url, user="usr-sam", scope="knowledge:read tickets:read", **kw):
    return keys.access_token(user, scope, kw.pop("audience", url), **kw)


def call(url, tok, tenant, name, args):
    async def go():
        http, target = host_app.http_target(url, tok, tenant)
        async with http, Client(target) as client:
            try:
                r = await client.call_tool(name, args)
                return ("error" if r.is_error else "ok"), r.content[0].text
            except MCPError as e:
                return "refused", e.error.message

    return anyio.run(go)


def post(url, tok=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return httpx2.post(url, headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})


def test_no_token_gets_401_and_where_to_sign_in(server):
    r = post(server)
    assert r.status_code == 401
    assert 'resource_metadata="' in r.headers["www-authenticate"]
    meta = httpx2.get(server.replace("/mcp", "/.well-known/oauth-protected-resource/mcp")).json()
    assert meta["resource"] == server and meta["authorization_servers"] == [ISSUER]


@pytest.mark.parametrize("case", ["wrong_audience", "expired", "other_issuer", "other_key", "alg_none", "garbage"])
def test_bad_tokens_get_401(server, case):
    if case == "wrong_audience":  # a token for another API (the ticket API): never accepted here
        tok = token(server, audience="ticket-api")
    elif case == "expired":
        tok = token(server, now=time.time() - 3600)
    elif case == "other_issuer":
        tok = jwt.encode(
            {"iss": "http://evil.example", "sub": "usr-sam", "aud": server, "exp": time.time() + 600},
            keys._private()[1],
            algorithm="RS256",
            headers={"kid": keys._private()[0], "typ": "at+jwt"},
        )
    elif case == "other_key":
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        tok = jwt.encode(
            {"iss": ISSUER, "sub": "usr-sam", "aud": server, "exp": time.time() + 600},
            other,
            algorithm="RS256",
            headers={"kid": keys._private()[0], "typ": "at+jwt"},
        )
    elif case == "alg_none":
        tok = jwt.encode(
            {"iss": ISSUER, "sub": "usr-sam", "aud": server, "exp": time.time() + 600},
            None,
            algorithm="none",
            headers={"typ": "at+jwt"},
        )
    else:
        tok = "abc.def"
    assert post(server, tok).status_code == 401


def test_a_member_reads_their_organization(server):
    assert call(server, token(server), "larkfield", "get_ticket", {"ticket_id": "T-30002"})[0] == "ok"


def test_another_organization_is_refused_on_the_server(server):
    # Ines is an owner at Bramble Books only. The host could send any header: the server checks.
    status, message = call(server, token(server, "usr-ines"), "larkfield", "get_ticket", {"ticket_id": "T-30002"})
    assert status == "refused" and "no access to this organization" in message


def test_a_made_up_organization_gets_the_same_answer(server):
    a = call(server, token(server, "usr-ines"), "larkfield", "search_knowledge", {"query": "returns"})
    b = call(server, token(server, "usr-ines"), "nowhere", "search_knowledge", {"query": "returns"})
    assert a == b == ("refused", "forbidden: you have no access to this organization")


def test_a_cross_tenant_id_is_not_found(server):
    # Camille is a member of both, but this connection is for Larkfield.
    status, message = call(server, token(server, "usr-camille"), "larkfield", "get_ticket", {"ticket_id": "T-40003"})
    assert status == "error" and "not_found" in message
    assert call(server, token(server, "usr-camille"), "bramble", "get_ticket", {"ticket_id": "T-40003"})[0] == "ok"


def test_a_token_without_the_read_scopes_is_refused_before_mcp(server):
    r = post(server, token(server, scope="knowledge:read"))  # no tickets:read
    assert r.status_code == 403 and 'error="insufficient_scope"' in r.headers["www-authenticate"]


def test_the_resource_metadata_advertises_only_the_read_scopes(server):
    meta = httpx2.get(server.replace("/mcp", "/.well-known/oauth-protected-resource/mcp")).json()
    assert meta["scopes_supported"] == ["knowledge:read", "tickets:read"]  # not refunds:propose


def test_someone_without_any_membership_is_refused(server):
    assert (
        call(server, token(server, "usr-tomas"), "larkfield", "search_knowledge", {"query": "returns"})[0] == "refused"
    )
