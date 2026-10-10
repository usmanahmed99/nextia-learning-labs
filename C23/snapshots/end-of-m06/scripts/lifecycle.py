"""How long does access last after it should end? Measure it, one change at a time.

    python -m scripts.lifecycle remove             Grace removes Camille: tokens, jobs, cache
    python -m scripts.lifecycle role               Sam becomes read-only
    python -m scripts.lifecycle invitation         an invitation that expired, then a new one
    python -m scripts.lifecycle membership-cache   the same removal with roles cached for 30 s
    python -m scripts.lifecycle token              an access token after the person is disabled
    python -m scripts.lifecycle all                all of the above (not the deletion)
    python -m scripts.lifecycle delete-tenant      Kwame deletes Bramble Books (then: load --reset)
    add --json to print the measurements as JSON

Every step uses the API code in this folder, with the made-up people and data (constructed
for the course). Each command puts back what it changed, except delete-tenant.
"""

import argparse
import json
import sys
import time

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from scripts.practice import headers, local_app, store, token
from ticket_api.config import load_settings
from ticket_api.db import Database
from ticket_api.worker import run_once

L = "/v1/tenants/larkfield"
B = "/v1/tenants/bramble"


def ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def sql(statement: str, params=()) -> list[dict]:
    with psycopg.connect(load_settings().database_url, row_factory=dict_row) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else []


def restore_member(user: str, tenant: str, role: str) -> None:
    sql(
        "INSERT INTO memberships (tenant_id, user_id, role) VALUES (%s, %s, %s)"
        " ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role",
        (tenant, user, role),
    )


def remove(client: TestClient, say) -> dict:
    camille = headers("usr-camille")
    grace = headers("usr-grace")
    out = {}
    say("Camille (staff at Larkfield) has a valid access token, a queued export, and a cached")
    say("answer (similar tickets of T-30002). Grace removes her from Larkfield.")
    assert client.get(f"{L}/tickets/T-30002/similar", headers=camille).status_code == 200
    job = client.post(f"{L}/exports", json={}, headers=camille).json()["job_id"]
    t0 = time.perf_counter()
    client.delete(f"{L}/members/usr-camille", headers=grace)
    out["removed_ms"] = ms(t0)
    t1 = time.perf_counter()
    r = client.get(f"{L}/tickets/T-30002", headers=camille)
    out["next_request"] = {"status": r.status_code, "ms_after_removal": ms(t1)}
    say(f"  next request with the same token: {r.status_code} ({r.json()['error']['message']})")
    r = client.get(f"{L}/tickets/T-30002/similar", headers=camille)
    out["cached_answer"] = r.status_code
    say(f"  the cached similar tickets: {r.status_code} (the check runs before the cache)")
    me = client.get("/v1/me", headers=camille).json()
    out["token_still_valid_for_me"] = True
    say(
        f"  the token itself is still valid: /v1/me answers, memberships"
        f" {[m['tenant_id'] for m in me['memberships']]}"
    )
    settings = load_settings()
    outcome = run_once(Database(settings.database_url, pool=False))
    reason = sql("SELECT reason FROM jobs WHERE job_id = %s", (job,))[0]["reason"]
    out["queued_job"] = {"outcome": dict(outcome).get(job), "reason": reason}
    say(f"  her queued export, run now: {dict(outcome).get(job)} ({reason})")
    r = client.get(f"{B}/tickets/T-40001", headers=camille)
    out["other_membership"] = r.status_code
    say(f"  her other membership (read-only at Bramble Books): {r.status_code}")
    restore_member("usr-camille", "larkfield", "staff")
    return out


def role(client: TestClient, say) -> dict:
    sam, grace = headers("usr-sam"), headers("usr-grace")
    body = {"author": "agent", "body": "(lifecycle demo)"}
    before = client.post(f"{L}/tickets/T-30002/messages", json=body, headers=sam).status_code
    client.patch(f"{L}/members/usr-sam", json={"role": "read_only"}, headers=grace)
    after = client.post(f"{L}/tickets/T-30002/messages", json=body, headers=sam)
    say(
        f"Sam writes as staff: {before}. Grace makes him read-only. Sam writes again:"
        f" {after.status_code} ({after.json()['error']['message']})"
    )
    restore_member("usr-sam", "larkfield", "staff")
    sql("DELETE FROM messages WHERE body = '(lifecycle demo)'")
    sql(
        "UPDATE tickets t SET message_count = (SELECT count(*) FROM messages m"
        " WHERE m.ticket_id = t.ticket_id) WHERE ticket_id = 'T-30002'"
    )
    return {"before": before, "after": after.status_code}


def invitation(client: TestClient, say) -> dict:
    grace, tomas = headers("usr-grace"), headers("usr-tomas")
    invite = client.post(
        f"{L}/invitations",
        headers=grace,
        json={"email": "tomas@larkfield.example", "role": "read_only", "expires_in_hours": 72},
    ).json()
    say(f"Grace invites tomas@larkfield.example (read-only), valid until {invite['expires_at']}.")
    sql(
        "UPDATE invitations SET created_at = created_at - interval '4 days',"
        " expires_at = expires_at - interval '4 days' WHERE invitation_id = %s",
        (invite["invitation_id"],),
    )
    say("  (constructed: the clock moves four days on)")
    late = client.post("/v1/invitations/accept", json={"code": invite["code"]}, headers=tomas)
    say(f"  Tomás accepts: {late.status_code} {late.json()['error']['code']}")
    fresh = client.post(
        f"{L}/invitations",
        headers=grace,
        json={"email": "tomas@larkfield.example", "role": "read_only"},
    ).json()
    ok = client.post("/v1/invitations/accept", json={"code": fresh["code"]}, headers=tomas)
    see = client.get(f"{L}/tickets/T-30002", headers=tomas).status_code
    say(f"  a new invitation: {ok.status_code} {ok.json()}; he reads T-30002: {see}")
    sql("DELETE FROM memberships WHERE user_id = 'usr-tomas'")
    sql("DELETE FROM invitations WHERE email = 'tomas@larkfield.example'")
    return {"expired": late.json()["error"]["code"], "new": ok.status_code, "reads": see}


def membership_cache(_, say, seconds: float = 30) -> dict:
    say(f"The same removal, with MEMBERSHIP_CACHE_SECONDS={seconds:g} (constructed setting):")
    with (
        TestClient(
            local_app(membership_cache_seconds=seconds), raise_server_exceptions=False
        ) as cached,
        TestClient(local_app(), raise_server_exceptions=False) as plain,
    ):
        camille = headers("usr-camille")
        cached.get(f"{L}/tickets/T-30002", headers=camille)  # the role is now cached
        plain.delete(f"{L}/members/usr-camille", headers=headers("usr-grace"))
        t0 = time.perf_counter()
        while cached.get(f"{L}/tickets/T-30002", headers=camille).status_code == 200:
            time.sleep(0.5)
        stale = round(time.perf_counter() - t0, 1)
    restore_member("usr-camille", "larkfield", "staff")
    say(f"  Camille kept reading Larkfield's tickets for {stale} s after her removal.")
    return {"cache_seconds": seconds, "stale_access_s": stale}


def token_lifetime(client: TestClient, say, seconds: int = 5) -> dict:
    leeway = load_settings().token_leeway_seconds
    say(f"An access token that expires {seconds} s after it was made; the person is disabled at")
    say(f"the provider at once. The API checks only the token (leeway {leeway:g} s):")
    short = token("usr-sam", exp=int(time.time()) + seconds)
    provider = store()
    provider.set_disabled("usr-sam", True)  # python -m idp disable usr-sam
    try:
        t0 = time.perf_counter()
        bearer = {"Authorization": f"Bearer {short}"}
        while client.get("/v1/me", headers=bearer).status_code == 200:
            time.sleep(0.5)
        lasted = round(time.perf_counter() - t0, 1)
    finally:
        provider.set_disabled("usr-sam", False)
    say(
        f"  accepted for {lasted} s (lifetime {seconds} s + leeway {leeway:g} s). With the"
        " default lifetime of 600 s, that is up to 630 s."
    )
    return {"lifetime_s": seconds, "leeway_s": leeway, "accepted_for_s": lasted}


def delete_tenant(client: TestClient, say) -> dict:
    kwame, ines = headers("usr-kwame"), headers("usr-ines")
    t0 = time.perf_counter()
    job = client.post(
        "/v1/admin/tenants/bramble/delete",
        headers=kwame,
        json={"reason": "Bramble Books closed its account (practice)"},
    ).json()
    r = client.get(f"{B}/tickets/T-40001", headers=ines)
    say(f"Kwame deletes Bramble Books. Ines, {ms(t0)} ms later: {r.status_code}.")
    settings = load_settings()
    from ticket_api.files import make_store

    t1 = time.perf_counter()
    outcome = run_once(Database(settings.database_url, pool=False), make_store(settings))
    result = sql("SELECT result FROM jobs WHERE job_id = %s", (job["job_id"],))[0]["result"]
    say(f"  the worker purged it in {ms(t1)} ms: {dict(outcome)[job['job_id']]} {result}")
    say("  Put the data back: python -m scripts.load --reset")
    return {"denied_status": r.status_code, "purge": result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "what",
        choices=[
            "remove",
            "role",
            "invitation",
            "membership-cache",
            "token",
            "all",
            "delete-tenant",
        ],
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    say = (lambda *a: None) if args.json else print
    steps = {
        "remove": remove,
        "role": role,
        "invitation": invitation,
        "membership-cache": membership_cache,
        "token": token_lifetime,
        "delete-tenant": delete_tenant,
    }
    names = [n for n in steps if n != "delete-tenant"] if args.what == "all" else [args.what]
    out = {}
    with TestClient(local_app(), raise_server_exceptions=False) as client:
        for name in names:
            out[name] = steps[name](client, say)
            say()
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
