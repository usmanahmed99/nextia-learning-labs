# ticket-api

A small web API that classifies support tickets.

## Set up

```sh
python3 -m venv .venv                # Windows: python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
```

## Run

```sh
fastapi dev                          # http://127.0.0.1:8000
```

## Deployed practice service

- Address: https://ticket-api.fastapicloud.dev (deleted)
- Smoke check:

  ```sh
  postman collection run postman/ticket-api.postman_collection.json -e postman/deployed.postman_environment.json --env-var "apiKey=<the key>"
  ```

- The API key is not in this project. Ask the owner, or set a new one with
  `fastapi cloud env set API_KEY --secret --value-stdin`.
