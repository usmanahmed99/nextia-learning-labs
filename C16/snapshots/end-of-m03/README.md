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
fastapi dev ticket_api/main.py       # http://127.0.0.1:8000
```
