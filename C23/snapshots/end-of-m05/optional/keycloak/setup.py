"""Set up Keycloak (a real, open-source identity provider) for the ticket API, on your computer.

    docker run -d --name ticket-keycloak -p 127.0.0.1:8480:8080 \
        -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=<a password> \
        quay.io/keycloak/keycloak:26.8.0 start-dev
    KEYCLOAK_ADMIN_PASSWORD=<the same password> python optional/keycloak/setup.py

It makes, through Keycloak's admin REST API: a realm "helpdesk"; the client scopes
tickets:read, tickets:write and members:manage; an audience mapper that puts "ticket-api"
into the access tokens; the application "help-desk-web" (confidential, PKCE S256, the API's
redirect URI); and one made-up person, "sam", with a new random password. It prints the
settings for .env. Delete everything afterwards: docker rm -f ticket-keycloak

No account and no money: Keycloak runs only on your computer. "start-dev" is Keycloak's
development mode (plain HTTP, an in-memory database): never use it for real people.
"""

import os
import secrets
import sys

import httpx

BASE = os.environ.get("KEYCLOAK_URL", "http://127.0.0.1:8480")
REALM = "helpdesk"
REDIRECT = "http://127.0.0.1:8000/auth/callback"
AFTER_LOGOUT = "http://127.0.0.1:8000/app/"


def main() -> int:
    password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD")
    if not password:
        print("Set KEYCLOAK_ADMIN_PASSWORD (the password you gave the container).", file=sys.stderr)
        return 1
    token = httpx.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": password,
        },
    ).json()["access_token"]
    api = httpx.Client(
        base_url=f"{BASE}/admin/realms", timeout=20, headers={"Authorization": f"Bearer {token}"}
    )

    def ok(response: httpx.Response) -> httpx.Response:
        if response.status_code >= 400 and response.status_code != 409:  # 409: it exists
            raise SystemExit(
                f"{response.request.method} {response.request.url}: "
                f"{response.status_code} {response.text}"
            )
        return response

    ok(api.post("", json={"realm": REALM, "enabled": True, "accessTokenLifespan": 600}))
    for name in ("tickets:read", "tickets:write", "members:manage"):
        ok(
            api.post(
                f"/{REALM}/client-scopes",
                json={
                    "name": name,
                    "protocol": "openid-connect",
                    "attributes": {
                        "include.in.token.scope": "true",
                        "display.on.consent.screen": "false",
                    },
                },
            )
        )
    ok(
        api.post(
            f"/{REALM}/client-scopes",
            json={
                "name": "ticket-api-audience",
                "protocol": "openid-connect",
                "attributes": {"include.in.token.scope": "false"},
                "protocolMappers": [
                    {
                        "name": "audience ticket-api",
                        "protocol": "openid-connect",
                        "protocolMapper": "oidc-audience-mapper",
                        "config": {
                            "included.custom.audience": "ticket-api",
                            "access.token.claim": "true",
                            "id.token.claim": "false",
                        },
                    }
                ],
            },
        )
    )
    ok(
        api.post(
            f"/{REALM}/clients",
            json={
                "clientId": "help-desk-web",
                "name": "Help desk (web)",
                "protocol": "openid-connect",
                "publicClient": False,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "redirectUris": [REDIRECT],
                "attributes": {
                    "pkce.code.challenge.method": "S256",
                    "post.logout.redirect.uris": AFTER_LOGOUT,
                },
                # "basic" puts sub (the user ID) into the tokens: without it, the API refuses them.
                "defaultClientScopes": [
                    "basic",
                    "profile",
                    "email",
                    "ticket-api-audience",
                    "tickets:read",
                    "tickets:write",
                    "members:manage",
                ],
                "optionalClientScopes": ["offline_access"],
            },
        )
    )
    client = ok(api.get(f"/{REALM}/clients", params={"clientId": "help-desk-web"})).json()[0]
    secret = ok(api.get(f"/{REALM}/clients/{client['id']}/client-secret")).json()["value"]
    person_password = secrets.token_urlsafe(12)
    ok(
        api.post(
            f"/{REALM}/users",
            json={
                "username": "sam",
                "email": "sam@larkfield.example",
                "firstName": "Sam",
                "lastName": "Practice",
                "emailVerified": True,
                "enabled": True,
                "credentials": [{"type": "password", "value": person_password, "temporary": False}],
            },
        )
    )
    user = ok(api.get(f"/{REALM}/users", params={"username": "sam", "exact": "true"})).json()[0]
    print("Keycloak is ready. Put these lines in .env (instead of the practice provider's):")
    print(f"OIDC_ISSUER={BASE}/realms/{REALM}")
    print("OIDC_CLIENT_ID=help-desk-web")
    print(f"OIDC_CLIENT_SECRET={secret}")
    print("ACCESS_TOKEN_TYPES=JWT")
    print(f"\nSign in as sam with the password {person_password} (made up; shown once).")
    print(f"Keycloak's user ID for sam (the token's sub): {user['id']}")
    print("Give it a membership, for example:")
    print(
        f"  INSERT INTO users (user_id, name, email) VALUES ('{user['id']}', 'Sam (Keycloak)',"
        " 'sam.keycloak@larkfield.example');"
    )
    print(
        f"  INSERT INTO memberships (tenant_id, user_id, role) VALUES ('larkfield',"
        f" '{user['id']}', 'staff');"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
