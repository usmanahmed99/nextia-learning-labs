# Remote deployment design (worked example)

## Local (stdio) and remote (Streamable HTTP) compared

| Question | Local: stdio | Remote: Streamable HTTP |
|---|---|---|
| Who starts the server? | The AI application, as a child process | You, as a web service at one URL |
| Who is the caller? | The person who started it (from the environment) | The user named in a validated access token |
| How many users? | One | Many, at the same time |
| Network | None: stdin and stdout | HTTPS in production (HTTP only on 127.0.0.1 for practice) |
| Where do secrets live? | The person's computer | The server; the client holds only the user's token |

## Request flow

1. The client sends a request without a token. The server answers **401** with `WWW-Authenticate: Bearer … resource_metadata="…/.well-known/oauth-protected-resource/mcp"`.
2. The client reads the protected resource metadata (RFC 9728): the resource URL and its authorization server.
3. The client reads the authorization server's metadata (RFC 8414), registers if needed (RFC 7591), and signs the person in with the authorization code flow and PKCE (S256), asking for this resource (`resource=` the server's URL, RFC 8707) and the scopes it needs.
4. The client sends every request with `Authorization: Bearer <token>` and the organization in `X-Support-Tenant`.
5. The server checks the token (signature, `typ`, issuer, **audience = its own URL**, expiry), then the membership (organization and role) and the scope, for every request.

## Decisions

- **Organization from the connection, never from the model.** The host sets `X-Support-Tenant`; no tool takes an organization argument.
- **Role from the server's membership table, never from the token.** The token carries no organization and no role.
- **No token passthrough.** The server never forwards the user's token. If it had to call another API, it would use its own credential for that API.
- **Production needs:** HTTPS, a real identity provider, a token lifetime of minutes, logs without tokens, a rate limit per caller.
