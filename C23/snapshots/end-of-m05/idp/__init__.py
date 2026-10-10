"""A small identity provider for practice: OpenID Connect on your own computer.

It is a MOCK. It shows a list of made-up people instead of asking for a password, and it
keeps codes and refresh tokens in memory. Everything else is done the standard way, so the
API and the browser see what a real provider sends: a discovery document, published keys
(JWKS), the authorization code flow with PKCE, signed ID and access tokens (RS256), refresh
tokens, and logout. The signing and the key handling use PyJWT and cryptography; there is no
hand-written cryptography here.

    python -m idp init            make the keys and the client secrets (once)
    python -m idp                 run it on http://localhost:8400
"""
