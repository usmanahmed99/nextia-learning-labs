# Handoff: access control of the ticket API

For the team that runs the ticket API with more than one organization. Everything here can be
checked with a command; the commands are in the last section.

## 1. The model

- **Who:** a user ID (`sub`) from an access token checked on every request (issuer, audience
  `ticket-api`, signature with the provider's published keys, expiry, algorithm RS256 only),
  or from a browser session that the API made after the same checks.
- **Where:** the organization in the path, `/v1/tenants/{tenant}/...`, and the caller's
  membership in it, read from the database on every request. Never from a header or a body.
- **What:** the membership's role (`owner`, `staff`, `read_only`) and the token's scopes. The
  matrix is `docs/access-matrix.md`; the code is `ticket_api/access.py`.
- **Not a member:** `404 Not found.`, the same answer as for an organization that does not
  exist. A member whose role is too small: `403`.
- **Second lock:** PostgreSQL row-level security (`migrations/017`): each transaction runs as
  the role `ticket_app` for one organization (`DB_ROW_SECURITY=true`).

## 2. Identity configuration

See `docs/identity-config.md` (both sides of the registration, and `.env`). The practice
setup uses the local mock provider; Keycloak was tested as a real provider; Microsoft Entra ID
is described, not tested.

## 3. Sessions and tokens over time

| Credential | Lifetime | What ends it early |
|---|---|---|
| Access token | 10 minutes (+30 s leeway) | nothing: the API cannot recall a token. Membership checks make it useless for an organization at once. |
| Refresh token | 8 hours, one use each (rotation) | logout (revoked at the provider), a disabled account, a reused old token (the whole family ends) |
| Browser session | 30 minutes idle, 8 hours at most | logout, a failed refresh (checked every 10 minutes), the end of either clock |
| Support access | at most 60 minutes | revocation; it opens `ticket.read` only, and every use is recorded |
| Invitation | 72 hours (at most 168), one use | revocation |

## 4. Tests and evidence

- `python -m pytest`: every test, including the access-control matrix (`tests/test_access_matrix.py`:
  7 people x 2 organizations x 11 routes, another organization's record IDs, and 5 kinds of bad
  identity on every route).
- `python -m scripts.matrix_report`: runs the matrix and writes `docs/test-report.md`.
- `python -m scripts.attempts`: the made-up attempts of the course (all must be refused).
- `python -m scripts.audit --check`: no token or secret in the audit events.
- `python -m scripts.lifecycle all`: how long access lasts after each kind of change.

## 5. Open choices

- The real provider, and its claims: see "Open provider-specific choices" in
  `docs/identity-config.md`.
- Caching roles (`MEMBERSHIP_CACHE_SECONDS`): off. On, it keeps a removed member in for as long
  as the cache keeps the entry.
- The audit log's retention, and who outside the organization may read it.
- What a deleted organization's AI-run costs need: they stay, with no ticket and no text.
