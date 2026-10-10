"""Helpers for the course's scripts: the API in this process, and access tokens made with the
practice provider's keys in .idp/ (python -m idp init first). No server and no network:
the API reads the provider's public keys straight from .idp/.

    from scripts.practice import local_app, token
    client = TestClient(local_app())
    client.get("/v1/me", headers={"Authorization": f"Bearer {token('usr-sam')}"})

The tokens are real (signed with the provider's key, checked by the API like any other);
they are made here instead of through a sign-in, so that a script can act as each person.
"""

import os
from dataclasses import replace

from idp.store import Store
from idp.tokens import Signer
from ticket_api.config import load_settings

ALL_SCOPES = "tickets:read tickets:write members:manage"


def issuer() -> str:
    return os.environ.get("OIDC_ISSUER") or "http://localhost:8400"


def store() -> Store:
    s = Store()
    if not s.exists():
        raise SystemExit("The practice provider has no keys yet. Run: python -m idp init")
    return s


def token(user: str, scope: str = ALL_SCOPES, **claims) -> str:
    return Signer(store(), issuer()).access_token(user, "ticket-cli", scope, **claims)


def headers(user: str, scope: str = ALL_SCOPES) -> dict:
    return {"Authorization": f"Bearer {token(user, scope)}"}


def connect(app) -> None:
    """Point the app's token checks at the keys in .idp/ (instead of the running provider)."""
    s, base = store(), issuer()
    docs = {"/.well-known/openid-configuration": {"issuer": base, "jwks_uri": f"{base}/jwks.json"}}
    app.state.validator.provider.fetch = lambda url: docs.get(url.removeprefix(base)) or s.jwks()


def local_app(**changes):
    from ticket_api.main import create_app

    settings = replace(load_settings(), oidc_issuer=issuer(), **changes)
    app = create_app(settings)
    connect(app)
    return app
