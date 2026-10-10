"""The data is well formed: cases load, every case's user is a member of the case's tenant, and the
practice database has the tenants and memberships the course expects."""

from support_assistant.data import all_cases, load_attacks, load_tasks
from support_assistant.runner import fresh_world


def test_cases_load():
    tasks, attacks = load_tasks(), load_attacks()
    assert len(tasks) == 26 and len(attacks) == 42
    assert all(c.kind == "attack" and c.constructed for c in attacks.values())


def test_every_case_user_is_a_member_of_its_tenant():
    w = fresh_world()
    for c in all_cases().values():
        assert w.role_in(c.user, c.tenant) is not None, c.case_id
        assert w.ticket(c.ticket_id) is not None, c.case_id


def test_tenants_and_memberships():
    w = fresh_world()
    assert w.role_in("usr-grace", "larkfield") == "owner"
    assert w.role_in("usr-camille", "bramble") == "read_only"
    assert w.role_in("usr-tomas", "larkfield") is None
    assert w.is_platform_admin("usr-kwame") and not w.is_platform_admin("usr-grace")


def test_the_secret_is_never_in_a_ticket_or_a_document():
    from support_assistant.data import made_up_secrets
    w = fresh_world()
    import sqlite3
    con = sqlite3.connect(w.db)
    texts = [r[0] for r in con.execute("SELECT text FROM tickets")]
    texts += [r[0] for r in con.execute("SELECT text FROM documents")]
    con.close()
    for secret in made_up_secrets():
        assert not any(secret in t for t in texts)
