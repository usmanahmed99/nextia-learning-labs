"""See one request as JSON, and (optionally) send it with plain HTTP, without the SDK.

    python -m assistant.raw T-80008            print the request body that the assistant would send
    python -m assistant.raw T-80008 --send     send it to ASSISTANT_BASE_URL with httpx and print the response

--send needs a live provider (for example Ollama: ASSISTANT_BASE_URL=http://localhost:11434/v1 and
ASSISTANT_MODEL=gemma3:4b). The key is sent in a header and never printed.
"""

import json
import sys

import httpx

from .config import Settings
from .context import build_request
from .data import load_ticket


def main(argv: list[str]) -> int:
    settings = Settings.from_env()
    ticket = load_ticket(argv[0] if argv else "T-80008")
    body = build_request(ticket, settings.model, "v1")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    if "--send" not in argv:
        return 0
    if not settings.base_url:
        print("Set ASSISTANT_BASE_URL first (see .env.example).", file=sys.stderr)
        return 2
    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    response = httpx.post(settings.base_url.rstrip("/") + "/chat/completions", json=body, headers=headers,
                          timeout=settings.timeout_s)
    print(f"\nHTTP {response.status_code}")
    for name in ("content-type", "date", "x-request-id"):
        if name in response.headers:
            print(f"{name}: {response.headers[name]}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
