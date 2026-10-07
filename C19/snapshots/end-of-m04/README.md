# ticket-api

A small web API that classifies support tickets. It runs in a container, alone or with a PostgreSQL database that keeps a history of the classifications.

## Run it in a container

You need Docker. The API listens on port 8000 in the container.

```sh
docker build -t ticket-api:1.1.0 .
docker run --rm -p 127.0.0.1:8000:8000 -e API_KEY=local-dev-key ticket-api:1.1.0
```

Check it: `curl http://127.0.0.1:8000/health` gives `{"status":"ok"}`.

## Run it with the database

```sh
cp .env.example .env                         # then change the password in .env
mkdir -p secrets
printf 'local-dev-key' > secrets/api_key.txt
docker compose up -d --build
```

- `docker compose down` stops and removes the containers. The data stays in the volume `ticket-api_pgdata`.
- `docker compose down --volumes` also deletes the data.

## Settings

| Setting | Required | Default | What it does |
|---|---|---|---|
| `API_KEY` or `API_KEY_FILE` | When `REQUIRE_API_KEY` is `true` | none | The key that clients send in `X-API-Key`. `API_KEY_FILE` is the path of a file that holds it. |
| `REQUIRE_API_KEY` | No | `false` | `true`: the API does not start without a key. |
| `DATABASE_URL` or `DATABASE_URL_FILE` | No | none | A PostgreSQL URL. Without it, history is off. |
| `ALLOWED_ORIGINS` | No | none | Sites that may call the API from a browser, separated by commas. |
| `SHOW_DOCS` | No | `true` | `false` hides `/docs`, `/redoc` and `/openapi.json`. |
| `CLASSIFIER_MODE`, `CLASSIFIER_TIMEOUT`, `LOG_LEVEL` | No | `keywords`, `2.0`, `INFO` | As in C16. |

Never put a key or a password in the Dockerfile, in `compose.yaml` or in Git. `.env` and `secrets/` are in `.gitignore` and `.dockerignore`.

## Work on the code

```sh
python3 -m venv .venv                # Windows: python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pytest
```

`requirements-run.txt` is the exact list of packages in the image. Make it again inside a container, so that it is the same on every computer:

```sh
docker run --rm python:3.14.8-slim-trixie sh -c 'pip install -q --root-user-action=ignore --disable-pip-version-check "fastapi[standard-no-fastapi-cloud-cli]==0.142.2" "psycopg[binary]==3.3.6" && pip freeze' > requirements-run.txt
```

## Deploy

`deploy/containerapp.yaml` has the Azure Container Apps settings: resources, environment values, health probes and scale limits. `deploy/local-cloud.yaml` runs the same settings on your computer. `DEPLOY.md` has the checklist and the resource inventory.
