"""Signing ID tokens and access tokens (JWT, RS256) with the provider's active key."""

import time
import uuid

import jwt

from idp.store import Store

ACCESS_TOKEN_TYPE = "at+jwt"  # RFC 9068: an access token says that it is one


class Signer:
    def __init__(
        self,
        store: Store,
        issuer: str,
        audience: str = "ticket-api",
        access_seconds: int = 600,
        id_seconds: int = 600,
    ):
        self.store = store
        self.issuer = issuer
        self.audience = audience
        self.access_seconds = access_seconds
        self.id_seconds = id_seconds

    def _sign(self, claims: dict, typ: str) -> str:
        kid = self.store.keys()["active"]
        return jwt.encode(
            claims, self.store.private_key(kid), algorithm="RS256", headers={"kid": kid, "typ": typ}
        )

    def access_token(
        self, sub: str, client_id: str, scope: str, now: float | None = None, **extra
    ) -> str:
        """For the API (audience ticket-api): who the caller is and what the application may do.
        No organization and no role: the API takes those from its own membership table."""
        now = int(now if now is not None else time.time())
        claims = {
            "iss": self.issuer,
            "sub": sub,
            "aud": self.audience,
            "exp": now + self.access_seconds,
            "nbf": now,
            "iat": now,
            "jti": uuid.uuid4().hex,
            "client_id": client_id,
            "scope": scope,
            **extra,
        }
        return self._sign(claims, ACCESS_TOKEN_TYPE)

    def id_token(
        self,
        user: dict,
        client_id: str,
        nonce: str | None,
        auth_time: int,
        now: float | None = None,
    ) -> str:
        """For the application that asked for the sign-in (audience = its client ID): who
        signed in. It is not for calling an API."""
        now = int(now if now is not None else time.time())
        claims = {
            "iss": self.issuer,
            "sub": user["sub"],
            "aud": client_id,
            "exp": now + self.id_seconds,
            "iat": now,
            "auth_time": auth_time,
            "name": user["name"],
            "email": user["email"],
            "email_verified": True,
        }
        if nonce:
            claims["nonce"] = nonce
        return self._sign(claims, "JWT")
