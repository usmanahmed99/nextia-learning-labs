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

## Run it in a container

You need Docker. The API listens on port 8000 in the container.

```sh
docker build -t ticket-api:1.0.0 .
docker run --rm -p 127.0.0.1:8000:8000 -e API_KEY=local-dev-key ticket-api:1.0.0
```

Check it: `curl http://127.0.0.1:8000/health` gives `{"status":"ok"}`.
