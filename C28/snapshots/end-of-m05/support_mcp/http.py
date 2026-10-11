"""Remote access: the same server over Streamable HTTP, protected by access tokens.

The MCP server is an OAuth resource server. It does not sign anyone in: the identity provider
(the authorization server) does. For every request the server:
1. reads the bearer token (none, or not valid: HTTP 401 with a WWW-Authenticate header that
   points to this server's protected resource metadata, RFC 9728);
2. checks it: RS256 signature with the provider's published key, typ at+jwt, issuer, audience
   (this server's own URL: a token for another API is refused), expiry;
3. then each handler finds the organization (X-Support-Tenant header) and the role (membership
   table) and checks the scope (identity.py).
The token is never passed on to another service (no token passthrough).

    python -m support_mcp --http          (http://127.0.0.1:8000/mcp)
"""

import os
import time

import anyio
import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings

from support_mcp import logs
from support_mcp.server import build_server

ISSUER = os.environ.get("OIDC_ISSUER", "http://127.0.0.1:8400")
RESOURCE_URL = os.environ.get("MCP_RESOURCE_URL", "http://127.0.0.1:8000/mcp")
JWKS_URL = os.environ.get("OIDC_JWKS_URL", f"{ISSUER}/jwks.json")
LEEWAY_SECONDS = 30
ACCESS_TOKEN_TYPES = {"at+jwt", "application/at+jwt"}
READ_SCOPES = ("knowledge:read", "tickets:read")


class JwtVerifier:
    """Checks an access token and returns who it is for, or None (the SDK then answers 401)."""

    def __init__(
        self, issuer: str = ISSUER, audience: str = RESOURCE_URL, jwks_url: str = JWKS_URL, jwks: dict | None = None
    ):
        self.issuer, self.audience = issuer, audience
        # The provider's public keys, fetched from its JWKS URL and kept 10 minutes (or given, in tests).
        self.keys = jwt.PyJWKSet.from_dict(jwks) if jwks else None
        self.jwks = None if jwks else jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=600)
        self.log = logs.get_logger()

    def _key(self, token: str):
        if self.keys is None:
            return self.jwks.get_signing_key_from_jwt(token).key
        kid = jwt.get_unverified_header(token).get("kid")
        for k in self.keys.keys:
            if k.key_id == kid:
                return k.key
        raise jwt.PyJWKClientError("unknown_key")

    def check(self, token: str) -> AccessToken:
        """Raises jwt.InvalidTokenError (with the reason) or returns the token's facts."""
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256":
            raise jwt.InvalidAlgorithmError("algorithm_not_allowed")
        if header.get("typ") not in ACCESS_TOKEN_TYPES:
            raise jwt.InvalidTokenError("wrong_token_type")
        key = self._key(token)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            leeway=LEEWAY_SECONDS,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return AccessToken(
            token=token,
            client_id=claims.get("client_id", ""),
            scopes=claims.get("scope", "").split(),
            expires_at=claims["exp"],
            resource=self.audience,
            subject=claims["sub"],
            claims={"iss": claims["iss"]},
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        started = time.perf_counter()
        try:
            return await anyio.to_thread.run_sync(self.check, token)
        except (jwt.InvalidTokenError, jwt.PyJWKClientError) as e:
            reason = {
                jwt.InvalidAudienceError: "wrong_audience",
                jwt.InvalidIssuerError: "wrong_issuer",
                jwt.ExpiredSignatureError: "expired",
                jwt.InvalidSignatureError: "bad_signature",
                jwt.ImmatureSignatureError: "not_yet_valid",
                jwt.MissingRequiredClaimError: "missing_claim",
                jwt.DecodeError: "malformed",
            }.get(type(e), str(e) if str(e) in ("algorithm_not_allowed", "wrong_token_type") else "invalid")
            if isinstance(e, jwt.PyJWKClientError):
                reason = "unknown_key"
            self.log.event("token_refused", reason=reason, ms=logs.ms_since(started))
            return None


def build_app(
    verifier: JwtVerifier | None = None, knowledge=None, issuer: str = ISSUER, resource_url: str = RESOURCE_URL
):
    mcp = build_server(
        knowledge,
        transport="http",
        token_verifier=verifier or JwtVerifier(issuer, resource_url),
        # Every token must carry the read scopes; the resource metadata advertises only these, so a
        # client asks for no more (least privilege). The write scope is granted separately.
        auth=AuthSettings(
            issuer_url=issuer,
            resource_server_url=resource_url,
            required_scopes=list(READ_SCOPES),
            validate_token_resource=False,  # the verifier checks the audience itself
        ),
    )
    return mcp.streamable_http_app()
