"""Try what a careless or curious user could try, against your own practice API.

    python -m scripts.attempts            run every attempt and print what the API answered
    python -m scripts.attempts --json     the same, as JSON

The attempts are made up for the course and harmless: they read and write made-up
records in your own database, through the API code in this folder (no server and no
network needed). Each person sends their own access token, made with the practice
provider's keys (python -m idp init first). If an attempt that should fail succeeds,
it may change a record; python -m scripts.load --reset puts the data back.
"""

import argparse
import json
import sys

from fastapi.testclient import TestClient

from scripts.practice import headers, local_app


def shop_of(ticket_id: str) -> str:
    return "bramble" if ticket_id.startswith("T-4") and len(ticket_id) == 7 else "larkfield"


def only(shop):
    def check(body):
        ids = [t["ticket_id"] for t in body.get("items", [])]
        others = [i for i in ids if shop_of(i) != shop]
        if others:
            return False, f"{len(others)} of {len(ids)} tickets are another shop's"
        return True, f"{len(ids)} tickets, all {shop}'s"

    return check


def no_staff_documents(body):
    staff = [r["doc_id"] for r in body.get("results", []) if r["access"] == "staff"]
    if staff:
        return False, f"staff-only documents: {staff}"
    return True, f"{len(body.get('results', []))} public documents, no staff-only one"


def bramble_attachment(client) -> str:
    """The ID of one of Bramble Books' files (looked up as Ines, who may see them)."""
    t = client.get("/v1/tenants/bramble/tickets/T-40001", headers=headers("usr-ines")).json()
    return t["attachments"][0]["attachment_id"]


def attempts(client) -> list[tuple]:
    """(person, user ID, what they try, method, path, body, extra headers, status, check)"""
    att = bramble_attachment(client)
    sam, ines, omar = "Sam (staff at Larkfield)", "Ines (owner at Bramble Books)", "Omar"
    return [
        (sam, "usr-sam", "read Bramble Books' ticket T-40001 through Larkfield's path",
         "GET", "/v1/tenants/larkfield/tickets/T-40001", None, {}, 404, None),
        (sam, "usr-sam", "read T-40001 through Bramble Books' path",
         "GET", "/v1/tenants/bramble/tickets/T-40001", None, {}, 404, None),
        (ines, "usr-ines", "list the tickets of her own shop",
         "GET", "/v1/tenants/bramble/tickets?limit=100", None, {}, 200, only("bramble")),
        (f"{omar} (read-only at Larkfield)", "usr-omar",
         "add a message to T-30002 (the page hides the button; he sends the request himself)",
         "POST", "/v1/tenants/larkfield/tickets/T-30002/messages",
         {"author": "agent", "body": "(attempt: a read-only member writes)"}, {}, 403, None),
        ("Tomás (no membership)", "usr-tomas", "read Larkfield's ticket T-30002",
         "GET", "/v1/tenants/larkfield/tickets/T-30002", None, {}, 404, None),
        (ines, "usr-ines", "find tickets similar to her ticket T-40001",
         "GET", "/v1/tenants/bramble/tickets/T-40001/similar?k=5", None, {}, 200,
         only("bramble")),
        (sam, "usr-sam",
         "choose Bramble Books with a header (X-Tenant-ID: bramble) on Larkfield's list",
         "GET", "/v1/tenants/larkfield/tickets?limit=100", None, {"X-Tenant-ID": "bramble"},
         200, only("larkfield")),
        ("Camille (read-only at Bramble Books)", "usr-camille",
         "add a message to Bramble Books' T-40001",
         "POST", "/v1/tenants/bramble/tickets/T-40001/messages",
         {"author": "agent", "body": "(attempt: read-only at this shop)"}, {}, 403, None),
        (sam, "usr-sam", "get a download link for a Bramble Books receipt, with its real ID",
         "GET", f"/v1/tenants/larkfield/attachments/{att}/download", None, {}, 404, None),
        (f"{omar} (read-only at Larkfield)", "usr-omar",
         "search the documents for the staff-only refund procedure",
         "GET", "/v1/tenants/larkfield/documents?q=refund approval", None, {}, 200,
         no_staff_documents),
    ]


def run() -> list[dict]:
    results = []
    with TestClient(local_app(), raise_server_exceptions=False) as client:
        for i, attempt in enumerate(attempts(client), 1):
            who, user, what, method, path, body, extra, expected, check = attempt
            response = client.request(method, path, json=body, headers={**headers(user), **extra})
            ok, detail = response.status_code == expected, ""
            data = response.json() if response.content else {}
            if ok and check:
                ok, detail = check(data)
            elif response.status_code >= 400:
                detail = f"{data['error']['code']}: {data['error']['message']}"
            results.append(
                {
                    "n": i,
                    "who": who,
                    "user": user,
                    "tries": what,
                    "request": f"{method} {path}",
                    "should_get": expected,
                    "got": response.status_code,
                    "result": "OK" if ok else ("ESCALATION" if expected == 403 else "LEAK"),
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
    print("Made-up attempts against your own practice API. Each person sends their own token.\n")
    for r in results:
        print(f"{r['n']}. {r['who']} tries to {r['tries']}.")
        print(f"   {r['request']}  ->  {r['got']}   (should get: {r['should_get']})")
        print(f"   {r['result']}" + (f": {r['detail']}" if r["detail"] else ""))
    bad = sum(r["result"] != "OK" for r in results)
    print(f"\n{bad} of {len(results)} attempts got what they should not get.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
