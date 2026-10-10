"""Module 4, lessons 2 and 3: the organization is in every query, every file link, every
search, every citation and every cache key."""

import inspect

import psycopg
import pytest

from ticket_api import repository
from ticket_api.cache import TtlCache, cache_key

L = "/v1/tenants/larkfield"
B = "/v1/tenants/bramble"


def test_every_function_that_reads_an_organizations_records_needs_the_organization():
    for name in (
        "list_tickets",
        "get_ticket",
        "add_message",
        "ticket_exists",
        "get_attachment",
        "finish_attachment",
        "similar_tickets",
        "search_documents",
        "list_query",
    ):
        parameter = inspect.signature(getattr(repository, name)).parameters["tenant_id"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is inspect.Parameter.empty, name  # required, no default


def test_a_forgotten_organization_is_a_type_error_not_a_leak(conn):
    with pytest.raises(TypeError):
        repository.get_ticket(conn, "T-40001")


def test_similar_tickets_stay_in_the_organization(conn):
    items = repository.similar_tickets(
        conn, "T-40001", tenant_id="bramble", k=10, version="e5-small-v1"
    )
    assert len(items) == 10 and all(i["ticket_id"].startswith("T-4") for i in items)


def test_without_the_organization_filter_the_search_finds_larkfields_tickets(conn):
    """The leak that the filter prevents: the same query with no organization in it."""
    source = conn.execute(
        "SELECT embedding::text AS v FROM ticket_embeddings WHERE ticket_id = 'T-40001'"
    ).fetchone()["v"]
    rows = conn.execute(
        "SELECT ticket_id FROM ticket_embeddings WHERE ticket_id <> 'T-40001'"
        " ORDER BY embedding <=> %s::vector LIMIT 5",
        (source,),
    ).fetchall()
    assert any(r["ticket_id"].startswith("T-3") for r in rows)


def test_documents_of_the_organization_and_the_role(client_as):
    sam, omar, ines = client_as("usr-sam"), client_as("usr-omar"), client_as("usr-ines")
    staff = sam.get(f"{L}/documents", params={"q": "refund approval"}).json()
    public = omar.get(f"{L}/documents", params={"q": "refund approval"}).json()
    assert staff["access_level"] == "staff" and public["access_level"] == "public"
    assert "refund-approval-procedure" in [r["doc_id"] for r in staff["results"]]
    assert all(r["access"] == "public" for r in public["results"])
    bramble = ines.get(f"{B}/documents", params={"q": "return"}).json()["results"]
    larkfield = sam.get(f"{L}/documents", params={"q": "return"}).json()["results"]
    assert [r["title"] for r in bramble] == ["Returning a book"]
    assert "Returning a book" not in [r["title"] for r in larkfield]


def test_a_cache_key_starts_with_the_organization():
    with pytest.raises(ValueError):
        cache_key("", "similar", "T-30002")
    cache = TtlCache(60)
    cache.set(cache_key("larkfield", "similar", "T-30002"), "Larkfield's answer")
    assert cache.get(cache_key("bramble", "similar", "T-30002")) is None
    assert cache.drop_tenant("larkfield") == 1


def test_a_cached_answer_is_never_served_to_another_organization_or_role(client_as):
    sam, omar, ines = client_as("usr-sam"), client_as("usr-omar"), client_as("usr-ines")
    first = sam.get(f"{L}/documents", params={"q": "refund approval"}).json()
    again = omar.get(f"{L}/documents", params={"q": "refund approval"}).json()
    assert first != again  # Omar's key has "public", Sam's "staff"
    assert ines.get(f"{L}/tickets/T-30002/similar").status_code == 404


def test_files_of_another_organization_are_not_found_and_new_files_go_under_the_organization(
    make_api, tmp_path, conn
):
    from ticket_api.files import LocalFileStore

    sam = make_api(user="usr-sam")
    sam.app.state.files = LocalFileStore(tmp_path / "files")
    bramble_file = conn.execute(
        "SELECT attachment_id FROM attachments WHERE tenant_id = 'bramble' LIMIT 1"
    ).fetchone()["attachment_id"]
    assert sam.get(f"{L}/attachments/{bramble_file}/download").status_code == 404
    link = sam.post(
        f"{L}/tickets/T-30002/attachments",
        json={"file_name": "a.png", "content_type": "image/png", "size_bytes": 10},
    )
    assert link.status_code == 201
    key = conn.execute(
        "SELECT object_key FROM attachments WHERE attachment_id = %s",
        (link.json()["attachment_id"],),
    ).fetchone()["object_key"]
    assert key.startswith("tenants/larkfield/tickets/T-30002/")
    omar = make_api(user="usr-omar")
    omar.app.state.files = sam.app.state.files
    denied = omar.post(
        f"{L}/tickets/T-30002/attachments",
        json={"file_name": "a.png", "content_type": "image/png", "size_bytes": 10},
    )
    assert denied.status_code == 403


def test_the_database_refuses_a_message_for_another_organizations_ticket(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO messages (tenant_id, ticket_id, author, body)"
            " VALUES ('larkfield', 'T-40001', 'agent', 'x')"
        )
