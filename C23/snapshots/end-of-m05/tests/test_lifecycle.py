"""Module 5 of the authentication course: jobs, support access, members, invitations, and
deleting an organization. Every change takes effect at the next request."""

import pytest

from ticket_api import worker
from ticket_api.db import Database

L = "/v1/tenants/larkfield"
B = "/v1/tenants/bramble"


@pytest.fixture
def db(db_url):
    return Database(db_url, pool=False, row_security=True)


# ---------- jobs ----------


def test_an_export_runs_as_the_person_who_asked(client_as, db):
    sam = client_as("usr-sam")
    job = sam.post(f"{L}/exports", json={"status": "open"}).json()
    assert job["status"] == "queued" and job["actor_id"] == "usr-sam"
    assert worker.run_once(db) == [(job["job_id"], "done")]
    done = sam.get(f"{L}/exports/{job['job_id']}").json()
    assert done["status"] == "done" and done["result"]["rows"] > 0


def test_a_job_is_refused_when_its_actor_was_removed_before_it_ran(client_as, db):
    sam, grace = client_as("usr-sam"), client_as("usr-grace")
    job = sam.post(f"{L}/exports", json={}).json()
    assert grace.delete(f"{L}/members/usr-sam").status_code == 204
    assert worker.run_once(db) == [(job["job_id"], "refused")]
    reason = grace.get(f"{L}/exports/{job['job_id']}").json()["reason"]
    assert "no membership" in reason and "checked when the job ran" in reason


def test_a_job_row_that_names_an_organization_its_actor_cannot_access_is_refused(conn, db):
    """Constructed: someone inserts a job for Sam in Bramble Books, bypassing the API."""
    conn.execute(
        "INSERT INTO jobs (job_id, tenant_id, actor_id, kind) VALUES"
        " ('00000000-0000-4000-8000-000000000001', 'bramble', 'usr-sam', 'export')"
    )
    assert worker.run_once(db) == [("00000000-0000-4000-8000-000000000001", "refused")]


def test_a_queue_message_with_another_organization_changes_nothing(client_as, db):
    sam = client_as("usr-sam")
    job_id = sam.post(f"{L}/exports", json={}).json()["job_id"]
    job = worker.claim(db)
    message = {"job_id": job_id, "tenant_id": "bramble"}  # a forged or wrong field
    assert worker.run_job(db, job, message=message) == "refused"


def test_another_members_export_is_not_found_but_the_owner_sees_it(client_as):
    sam, camille, grace = client_as("usr-sam"), client_as("usr-camille"), client_as("usr-grace")
    job_id = sam.post(f"{L}/exports", json={}).json()["job_id"]
    assert camille.get(f"{L}/exports/{job_id}").status_code == 404
    assert grace.get(f"{L}/exports/{job_id}").status_code == 200
    assert client_as("usr-omar").post(f"{L}/exports", json={}).status_code == 403


# ---------- support access ----------


def test_a_platform_administrator_sees_nothing_without_a_grant(client_as):
    assert client_as("usr-kwame").get(f"{B}/tickets/T-40001").status_code == 404


def test_support_access_is_reasoned_time_limited_read_only_and_visible_to_the_owner(client_as):
    kwame, ines = client_as("usr-kwame"), client_as("usr-ines")
    too_short = kwame.post("/v1/admin/tenants/bramble/support-access", json={"reason": "help"})
    assert too_short.status_code == 422  # a real reason, please
    grant = kwame.post(
        "/v1/admin/tenants/bramble/support-access",
        json={"reason": "Ines asked for help with T-40001 (call on 9 October)", "minutes": 15},
    )
    assert grant.status_code == 201
    assert kwame.get(f"{B}/tickets/T-40001").status_code == 200
    reply = {"author": "agent", "body": "x"}
    assert kwame.post(f"{B}/tickets/T-40001/messages", json=reply).status_code == 403
    assert kwame.get(f"{L}/tickets/T-30002").status_code == 404  # only that organization
    seen = ines.get(f"{B}/support-access").json()["items"]
    assert seen[0]["user_id"] == "usr-kwame" and "T-40001" in seen[0]["reason"]
    uses = ines.get(f"{B}/audit", params={"action": "support_access.used"}).json()["items"]
    assert {u["result"] for u in uses} == {"allowed", "denied"}
    kwame.post(f"/v1/admin/support-access/{grant.json()['grant_id']}/revoke")
    assert kwame.get(f"{B}/tickets/T-40001").status_code == 404


def test_a_grant_cannot_last_more_than_an_hour(client_as):
    kwame = client_as("usr-kwame")
    body = {"reason": "A long support session", "minutes": 61}
    assert kwame.post("/v1/admin/tenants/bramble/support-access", json=body).status_code == 422


def test_only_a_platform_administrator_may_ask_for_support_access(client_as):
    grace = client_as("usr-grace")  # an owner, but of Larkfield only
    body = {"reason": "I want to see Bramble Books' tickets"}
    response = grace.post("/v1/admin/tenants/bramble/support-access", json=body)
    assert response.status_code == 403


# ---------- members and invitations ----------


def test_a_role_change_takes_effect_at_the_next_request(client_as):
    sam, grace = client_as("usr-sam"), client_as("usr-grace")
    reply = {"author": "agent", "body": "x"}
    assert sam.post(f"{L}/tickets/T-30002/messages", json=reply).status_code == 201
    grace.patch(f"{L}/members/usr-sam", json={"role": "read_only"})
    assert sam.post(f"{L}/tickets/T-30002/messages", json=reply).status_code == 403


def test_a_removed_member_gets_404_at_once(client_as):
    camille, grace = client_as("usr-camille"), client_as("usr-grace")
    assert camille.get(f"{L}/tickets/T-30002").status_code == 200
    assert grace.delete(f"{L}/members/usr-camille").status_code == 204
    assert camille.get(f"{L}/tickets/T-30002").status_code == 404
    assert camille.get(f"{B}/tickets/T-40001").status_code == 200  # the other membership stays


def test_the_last_owner_cannot_be_removed_or_demoted(client_as):
    grace = client_as("usr-grace")
    assert grace.delete(f"{L}/members/usr-grace").json()["error"]["code"] == "last_owner"
    answer = grace.patch(f"{L}/members/usr-grace", json={"role": "staff"})
    assert answer.status_code == 409


def test_only_an_owner_manages_members(client_as):
    sam = client_as("usr-sam")
    assert sam.get(f"{L}/members").status_code == 200
    assert sam.delete(f"{L}/members/usr-omar").status_code == 403


def test_an_invitation_works_once_for_its_email_and_not_after_it_expires(client_as, conn):
    grace, tomas, sam = client_as("usr-grace"), client_as("usr-tomas"), client_as("usr-sam")
    invite = grace.post(
        f"{L}/invitations", json={"email": "tomas@larkfield.example", "role": "read_only"}
    ).json()
    assert sam.post("/v1/invitations/accept", json={"code": invite["code"]}).status_code == 404
    conn.execute(
        "UPDATE invitations SET created_at = now() - interval '4 days',"
        " expires_at = now() - interval '1 day'"
    )  # constructed: four days later
    late = tomas.post("/v1/invitations/accept", json={"code": invite["code"]})
    assert late.status_code == 409 and late.json()["error"]["code"] == "invitation_expired"
    fresh = grace.post(
        f"{L}/invitations", json={"email": "Tomas@Larkfield.example", "role": "read_only"}
    ).json()
    joined = tomas.post("/v1/invitations/accept", json={"code": fresh["code"]})
    assert joined.json() == {
        "tenant_id": "larkfield",
        "tenant_name": "Larkfield",
        "role": "read_only",
    }
    again = tomas.post("/v1/invitations/accept", json={"code": fresh["code"]})
    assert again.json()["error"]["code"] == "invitation_used"
    assert tomas.get(f"{L}/tickets/T-30002").status_code == 200
    stored = conn.execute("SELECT code_sha256 FROM invitations").fetchall()
    assert all(fresh["code"] not in r["code_sha256"] for r in stored)


def test_a_membership_cache_keeps_a_removed_member_in_until_it_expires(make_api):
    camille = make_api(user="usr-camille", membership_cache_seconds=300)
    grace = make_api(user="usr-grace")
    assert camille.get(f"{L}/tickets/T-30002").status_code == 200
    grace.delete(f"{L}/members/usr-camille")
    assert camille.get(f"{L}/tickets/T-30002").status_code == 200  # stale: the cache said staff


# ---------- deleting an organization ----------


def test_deleting_an_organization_closes_it_at_once_and_purges_it_in_the_background(
    client_as, db, conn
):
    from ticket_api.lifecycle import remaining

    kwame, ines = client_as("usr-kwame"), client_as("usr-ines")
    job = kwame.post(
        "/v1/admin/tenants/bramble/delete",
        json={"reason": "Bramble Books closed its account (test)"},
    )
    assert job.status_code == 202
    assert ines.get(f"{B}/tickets/T-40001").status_code == 404  # before the purge ran
    assert worker.run_once(db) == [(job.json()["job_id"], "done")]
    left = remaining(conn, "bramble")
    assert left["ai_runs"] == 69 and sum(left.values()) == 69  # costs only, without text
    assert (
        conn.execute(
            "SELECT count(*) AS n FROM ai_runs WHERE tenant_id = 'bramble' AND output IS NOT NULL"
        ).fetchone()["n"]
        == 0
    )
    status = conn.execute("SELECT status FROM tenants WHERE tenant_id = 'bramble'").fetchone()
    assert status["status"] == "deleted"
    assert client_as("usr-grace").get(f"{L}/tickets/T-30002").status_code == 200
