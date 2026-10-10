# Optional: a real identity provider (Keycloak)

The course's practice provider (`python -m idp`) is a mock. To see the same API work with a real
identity provider without an account or money, run [Keycloak](https://www.keycloak.org/)
(Apache-2.0) in Docker on your computer, then delete it.

This route was tested with Keycloak 26.8.0 on macOS (Apple silicon).

1. Start Keycloak (choose your own admin password):

   ```sh
   docker run -d --name ticket-keycloak -p 127.0.0.1:8480:8080 \
     -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=choose-one \
     quay.io/keycloak/keycloak:26.8.0 start-dev
   ```

2. Set up the realm, the application and one made-up person (about one minute after step 1):

   ```sh
   KEYCLOAK_ADMIN_PASSWORD=choose-one python optional/keycloak/setup.py
   ```

   On Windows PowerShell: `$env:KEYCLOAK_ADMIN_PASSWORD="choose-one"; python optional/keycloak/setup.py`.

3. Put the four lines it prints into `.env` (instead of the practice provider's `OIDC_ISSUER`
   and `OIDC_CLIENT_SECRET`), and run the two `INSERT` statements it prints in `psql`. Keycloak
   gives Sam a new user ID, so he needs his own membership.
4. Start the API (`fastapi dev`), open http://127.0.0.1:8000/app/ and sign in as `sam` with the
   password that step 2 printed. Check the settings with `python -m scripts.check_identity`.
5. Delete everything: `docker rm -f ticket-keycloak`, and put the practice lines back in `.env`.

What is different from the practice provider (all seen in the tested run):

- Keycloak's access tokens have `typ: JWT` in their header, not `at+jwt`. With the API's
  default, the sign-in fails: "This is not an access token". Set `ACCESS_TOKEN_TYPES=JWT`: the
  audience check still refuses an ID token (its audience is `help-desk-web`, not `ticket-api`).
- Keycloak puts the audience `ticket-api` into access tokens only with an audience mapper
  (`setup.py` makes one), and `sub` only with its `basic` client scope.
- Keycloak checks that a PKCE verifier has 43 to 128 characters. The API's first version used
  32; the practice provider did not check, Keycloak refused the code. The practice provider
  checks it now too.
- Keycloak builds its issuer from the address you use (`http://127.0.0.1:8480/realms/helpdesk`
  in the tested run). Use the same address everywhere: in `.env`, in the browser, and in
  `setup.py` (`KEYCLOAK_URL`).

`start-dev` is Keycloak's development mode (plain HTTP, an in-memory database). Never use it for
real people.
