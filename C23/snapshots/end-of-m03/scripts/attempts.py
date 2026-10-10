"""Try what a careless or curious user could try, against your own practice API.

    python -m scripts.attempts            run every attempt and print what the API answered
    python -m scripts.attempts --json     the same, as JSON

The attempts are made up for the course and harmless: they read and write made-up
records in your own database, through the API code in this folder (no server and no
network needed). Attempt 3 adds one message to T-30002; python -m scripts.load --reset
puts the data back.

This version of the API knows one thing about a caller: whether it sent the API key.
So every attempt below is sent the same way, whoever is "behind" it.
"""

import argparse
import json
import sys

from fastapi.testclient import TestClient

from ticket_api.config import load_settings
from ticket_api.main import create_app

# (who, what they try, method, path, body, the answer they should get)
ATTEMPTS = [
    (
        "Sam (staff at Larkfield)",
        "read Bramble Books' ticket T-40001 by guessing its ID",
        "GET",
        "/v1/tickets/T-40001",
        None,
        404,
    ),
    (
        "Ines (owner at Bramble Books)",
        "list the tickets of her own shop",
        "GET",
        "/v1/tickets?limit=100",
        None,
        "only bramble",
    ),
    (
        "Omar (read-only at Larkfield)",
        "add a message to T-30002",
        "POST",
        "/v1/tickets/T-30002/messages",
        {"author": "agent", "body": "(attempt: a read-only member writes)"},
        403,
    ),
    (
        "Tomás (no membership)",
        "read Larkfield's ticket T-30002",
        "GET",
        "/v1/tickets/T-30002",
        None,
        404,
    ),
    (
        "Ines (owner at Bramble Books)",
        "find tickets similar to her ticket T-40001",
        "GET",
        "/v1/tickets/T-40001/similar?k=5",
        None,
        "only bramble",
    ),
]


def shop_of(ticket_id: str) -> str:
    return "bramble" if ticket_id.startswith("T-4") and len(ticket_id) == 7 else "larkfield"


def judge(expected, response) -> tuple[str, str]:
    """(result, detail): OK when the API answered as it should, else what went wrong."""
    body = response.json() if response.content else {}
    if expected == "only bramble":
        if response.status_code != 200:
            return "OK", f"answered {response.status_code}"
        ids = [t["ticket_id"] for t in body.get("items", [])]
        others = [i for i in ids if shop_of(i) != "bramble"]
        if others:
            return "LEAK", f"{len(others)} of {len(ids)} tickets are Larkfield's, e.g. {others[0]}"
        return "OK", f"{len(ids)} Bramble tickets"
    if response.status_code == expected:
        return "OK", ""
    if response.status_code in (200, 201):
        what = body.get("subject") or body.get("body") or ""
        kind = "ESCALATION" if expected == 403 else "LEAK"
        return kind, f'"{what[:50]}"' if what else ""
    return "OTHER", body.get("error", {}).get("code", "")


def run() -> list[dict]:
    settings = load_settings()
    headers = {"X-API-Key": settings.api_key} if settings.api_key else {}
    results = []
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        for i, (who, what, method, path, body, expected) in enumerate(ATTEMPTS, 1):
            response = client.request(method, path, json=body, headers=headers)
            result, detail = judge(expected, response)
            results.append(
                {
                    "n": i,
                    "who": who,
                    "tries": what,
                    "request": f"{method} {path}",
                    "should_get": expected,
                    "got": response.status_code,
                    "result": result,
                    "detail": detail,
                }
            )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    results = run()
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    print("Made-up attempts against your own practice API. Every request is sent the same way")
    print("(with the API key, if one is set): the API cannot tell who is calling.\n")
    for r in results:
        print(f"{r['n']}. {r['who']} tries to {r['tries']}.")
        print(f"   {r['request']}  ->  {r['got']}   (should get: {r['should_get']})")
        print(f"   {r['result']}" + (f": {r['detail']}" if r["detail"] else ""))
    bad = sum(r["result"] != "OK" for r in results)
    print(f"\n{bad} of {len(results)} attempts got what they should not get.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
