# Identity configuration

What the identity provider must know about the API, and what the API must know about the
provider. The two sides must match exactly: one character of difference in a redirect URI or
an issuer stops every sign-in. Check them with `python -m scripts.check_identity`.

## At the provider: the application registration

| Setting | The practice provider (`.idp/clients.json`) | Why |
|---|---|---|
| Client ID | `help-desk-web` | names the application in every request |
| Client type | confidential (it has a secret) | the API is a backend: it can keep a secret |
| Client secret | made by `python -m idp init`, written to `.env` | proves that a token request comes from the API |
| Redirect URI | `http://127.0.0.1:8000/auth/callback` | the only address that may receive codes |
| Post-logout redirect URI | `http://127.0.0.1:8000/app/` | where the provider sends the browser after sign-out |
| Grant types | authorization code, refresh token | the browser sign-in and its renewal |
| PKCE | required, S256 | a stolen code is useless without the verifier |
| Scopes | `openid profile email offline_access tickets:read tickets:write members:manage` | what the application may ask for |
| Audience of the access tokens | `ticket-api` | the tokens are for this API only |
| Signing | RS256, keys published at `/jwks.json` | the API checks signatures with the public key |

Two more applications are registered for the course: `ticket-cli` (public, PKCE, for
`python -m scripts.login`) and `export-worker` (client credentials: a service's own token).

## At the API: `.env`

| Variable | Practice value | Meaning |
|---|---|---|
| `OIDC_ISSUER` | `http://localhost:8400` | must equal the provider's `issuer`, character by character |
| `OIDC_INTERNAL_URL` | (empty) | where the API reaches the provider, if not at the issuer's address (in Docker: `http://idp:8400`) |
| `OIDC_AUDIENCE` | `ticket-api` | the audience every access token must have |
| `OIDC_CLIENT_ID` | `help-desk-web` | |
| `OIDC_CLIENT_SECRET` | (from `python -m idp init`) | never committed |
| `OIDC_REDIRECT_URI` | `http://127.0.0.1:8000/auth/callback` | must be registered at the provider |
| `ACCESS_TOKEN_TYPES` | `at+jwt,application/at+jwt` | the `typ` header of an access token; `JWT` for Keycloak and Microsoft Entra ID |
| `TOKEN_LEEWAY_SECONDS` | `30` | clock difference the API accepts on `exp` and `nbf` |
| `JWKS_CACHE_SECONDS` | `600` | how long the provider's keys are kept |
| `JWKS_MIN_REFRESH_SECONDS` | `10` | an unknown key ID makes the API fetch the keys again, at most this often |
| `SESSION_KEY` | (from `python -m idp init`) | encrypts the refresh tokens of the sessions |
| `SESSION_COOKIE_SECURE` | `false` on your computer, `true` on a server | a Secure cookie is meant for HTTPS only; Chrome and Firefox also send it to `127.0.0.1` over HTTP, Safari does not |
| `SESSION_IDLE_MINUTES`, `SESSION_MAX_HOURS` | `30`, `8` | when a session ends |
| `ALLOWED_ORIGINS` | (empty) | other sites whose JavaScript may call the API (CORS) |

## A real provider

- **Keycloak** (open source, in Docker, no account): tested with the course. See
  `optional/keycloak/README.md`. Its access tokens say `typ: JWT`, so set `ACCESS_TOKEN_TYPES=JWT`.
- **Microsoft Entra ID** (free tier): described from Microsoft's documentation, **not tested**.
  The same settings have other names: an *app registration* (the client ID), a *client secret*
  (under Certificates & secrets), a *redirect URI* of the type Web, and *Expose an API* with an
  *Application ID URI* (the audience, for example `api://ticket-api`) and its scopes (for
  example `tickets.read`). The issuer is `https://login.microsoftonline.com/<directory ID>/v2.0`
  when the registration asks for version 2 access tokens (in its manifest). Its access tokens
  say `typ: JWT` and put the scopes in `scp`, which the API reads too. The person's ID is `oid`
  (the same in every application) or `sub` (different per application); this API uses `sub`.

## Open provider-specific choices

- Which claim is the person's stable ID (`sub`, or Entra ID's `oid`), and how existing
  memberships move when it changes.
- Scope names (some providers do not allow `:`), and whether the provider puts the audience in
  access tokens by default (Keycloak needs an audience mapper).
- Logout: whether the provider supports RP-initiated logout and back-channel logout.
- Multi-factor sign-in and account recovery: the provider's job, not the API's.
