"""Who is calling: check the access token of every request (Module 2 of the authentication course).

An access token is a JWT signed by the identity provider. The API trusts it only after every
check below passes, in this order:

1. it is a JWT at all                          malformed
2. its algorithm is on our allow-list (RS256)  algorithm_not_allowed  (never "none", never HS256)
3. it is an access token (typ at+jwt)          wrong_token_type       (an ID token is not one)
4. its key ID is one the provider publishes    unknown_key
5. the signature is right                      bad_signature
6. it has not expired, and is already valid    expired / not_yet_valid
7. the issuer is our provider                  wrong_issuer
8. the audience is this API (ticket-api)       wrong_audience
9. the claims we need are there                missing_claim

The provider's public keys (JWKS) are fetched once and kept for JWKS_CACHE_SECONDS; a token
with a key ID that is not in the cache makes the API fetch them again, at most once every
JWKS_MIN_REFRESH_SECONDS. The token never says which organization or role: the API reads
those from its own membership table (ticket_api/access.py).
"""

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import jwt

logger = logging.getLogger("ticket_api")

ALGORITHMS = ["RS256"]  # the allow-list: fixed here, never taken from the token
ACCESS_TOKEN_TYPES = {"at+jwt", "application/at+jwt"}


class TokenRejected(Exception):
    """The token failed a check. `code` names the check."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ProviderUnavailable(Exception):
    """The identity provider's keys cannot be fetched."""


@dataclass(frozen=True)
class Identity:
    """The caller, as a checked token says."""

    user_id: str  # the token's "sub": a stable ID from the provider
    kind: str  # "user", or "service" for a token an application got for itself
    client_id: str
    scopes: frozenset[str]
    token_id: str | None
    expires_at: datetime
    via: str = "token"  # "token" (Authorization header) or "session" (cookie, Module 3)


def fetch_json(url: str) -> dict:
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    return response.json()


class ProviderConfig:
    """The provider's discovery document and its keys, fetched over HTTP and cached.

    `internal_url` is where the API reaches the provider (in Docker Compose: http://idp:8400);
    the issuer is the address in the tokens and in the browser (http://localhost:8400)."""

    def __init__(
        self,
        issuer: str,
        *,
        internal_url: str | None = None,
        cache_seconds: float = 600,
        min_refresh_seconds: float = 10,
        fetch: Callable[[str], dict] = fetch_json,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.issuer = issuer.rstrip("/")
        self.internal_url = (internal_url or issuer).rstrip("/")
        self.cache_seconds = cache_seconds
        self.min_refresh_seconds = min_refresh_seconds
        self.fetch = fetch
        self.clock = clock
        self.fetches = 0  # how many times the keys were fetched (for the measurements)
        self._lock = threading.Lock()
        self._discovery: dict | None = None
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None

    def _internal(self, url: str) -> str:
        return self.internal_url + url[len(self.issuer) :] if url.startswith(self.issuer) else url

    def discovery(self) -> dict:
        if self._discovery is None:
            try:
                doc = self.fetch(f"{self.internal_url}/.well-known/openid-configuration")
            except (httpx.HTTPError, ValueError) as error:
                raise ProviderUnavailable(f"discovery: {error}") from error
            if doc.get("issuer", "").rstrip("/") != self.issuer:
                raise ProviderUnavailable(
                    f"the provider says its issuer is {doc.get('issuer')!r}, not {self.issuer!r}"
                )
            self._discovery = doc
        return self._discovery

    def endpoint(self, name: str) -> str:
        """An endpoint of the provider, at the address where the API can reach it."""
        return self._internal(self.discovery()[name])

    def _refresh(self) -> None:
        try:
            jwks = self.fetch(self.endpoint("jwks_uri"))
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailable(f"keys: {error}") from error
        keys = {}
        for data in jwks.get("keys", []):
            if data.get("kty") == "RSA" and data.get("kid"):
                keys[data["kid"]] = jwt.PyJWK(data, algorithm="RS256")
        self._keys, self._fetched_at = keys, self.clock()
        self.fetches += 1

    def key(self, kid: str) -> jwt.PyJWK | None:
        with self._lock:
            now = self.clock()
            if self._fetched_at is None or now - self._fetched_at > self.cache_seconds:
                self._refresh()  # the cache is empty or old
            elif kid not in self._keys and now - self._fetched_at >= self.min_refresh_seconds:
                self._refresh()  # a new key ID: maybe the provider rotated its keys
            return self._keys.get(kid)


class TokenValidator:
    def __init__(
        self,
        provider: ProviderConfig,
        audience: str = "ticket-api",
        leeway_seconds: float = 30,
        check_type: bool = True,
    ):
        self.provider = provider
        self.audience = audience
        self.leeway = leeway_seconds
        self.check_type = check_type

    def validate(self, token: str) -> Identity:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.DecodeError:
            raise TokenRejected("malformed", "The token is not a JWT.") from None
        if header.get("alg") not in ALGORITHMS:
            raise TokenRejected(
                "algorithm_not_allowed",
                f"The token's algorithm {header.get('alg')!r} is not allowed (only RS256).",
            )
        if self.check_type and header.get("typ") not in ACCESS_TOKEN_TYPES:
            raise TokenRejected(
                "wrong_token_type",
                "This is not an access token (an ID token is for the application, not the API).",
            )
        key = self.provider.key(header.get("kid", ""))
        if key is None:
            raise TokenRejected(
                "unknown_key", "The token was signed with a key the provider does not publish."
            )
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=ALGORITHMS,
                audience=self.audience,
                issuer=self.provider.issuer,
                leeway=self.leeway,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenRejected("expired", "The token has expired.") from None
        except jwt.ImmatureSignatureError:
            raise TokenRejected("not_yet_valid", "The token is not valid yet.") from None
        except jwt.InvalidAudienceError:
            message = f"The token is not for {self.audience}."
            raise TokenRejected("wrong_audience", message) from None
        except jwt.InvalidIssuerError:
            raise TokenRejected("wrong_issuer", "The token is from another issuer.") from None
        except jwt.MissingRequiredClaimError as error:
            raise TokenRejected("missing_claim", f"The token has no {error.claim} claim.") from None
        except jwt.InvalidSignatureError:
            raise TokenRejected("bad_signature", "The token's signature is not right.") from None
        except jwt.InvalidTokenError as error:
            raise TokenRejected("invalid", f"The token is not valid: {error}.") from None
        client_id = claims.get("client_id", "")
        return Identity(
            user_id=claims["sub"],
            kind="service" if claims["sub"] == client_id else "user",
            client_id=client_id,
            scopes=frozenset(claims.get("scope", "").split()),
            token_id=claims.get("jti"),
            expires_at=datetime.fromtimestamp(claims["exp"], UTC),
        )


def make_validator(settings) -> TokenValidator | None:
    """The validator from the settings, or None when OIDC_ISSUER is not set."""
    if not settings.oidc_issuer:
        return None
    provider = ProviderConfig(
        settings.oidc_issuer,
        internal_url=settings.oidc_internal_url,
        cache_seconds=settings.jwks_cache_seconds,
        min_refresh_seconds=settings.jwks_min_refresh_seconds,
    )
    return TokenValidator(provider, settings.oidc_audience, settings.token_leeway_seconds)
