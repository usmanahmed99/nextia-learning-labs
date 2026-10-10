"""Module 5, lesson 2: similar tickets by vector, with a version and filters."""

from ticket_api import repository


def test_similar_tickets_are_closest_first_and_never_the_ticket_itself(api):
    result = api.get("/v1/tickets/T-30002/similar", params={"k": 5}).json()
    assert result["embedding_version"] == "e5-small-v1"
    distances = [t["distance"] for t in result["items"]]
    assert len(distances) == 5 and distances == sorted(distances)
    assert "T-30002" not in [t["ticket_id"] for t in result["items"]]


def test_a_filter_keeps_k_results(api):
    items = api.get("/v1/tickets/T-30002/similar", params={"k": 5, "team": "login"}).json()["items"]
    assert len(items) == 5 and {t["team"] for t in items} == {"login"}


def test_approximate_and_exact_search_agree_on_the_small_data(conn):
    for ticket in ("T-30002", "T-30050", "T-30150"):
        exact = repository.similar_tickets(conn, ticket, k=5, version="e5-small-v1", exact=True)
        approx = repository.similar_tickets(conn, ticket, k=5, version="e5-small-v1")
        assert [r["ticket_id"] for r in exact] == [r["ticket_id"] for r in approx]


def test_a_vector_of_another_version_is_never_compared(conn):
    conn.execute(
        "INSERT INTO embedding_versions (version, model, revision, dimensions)"
        " VALUES ('other-v1', 'another model', 'x', 384)"
    )
    conn.execute(
        "INSERT INTO ticket_embeddings (tenant_id, ticket_id, embedding, embedding_version,"
        " source_sha256) SELECT tenant_id, ticket_id, embedding, 'other-v1', source_sha256"
        " FROM ticket_embeddings"
        " WHERE ticket_id = 'T-30003'"
    )
    items = repository.similar_tickets(conn, "T-30002", k=300, version="e5-small-v1")
    # every other ticket once (of both shops: this search has no organization filter yet);
    # the other version's copy is not there
    assert len(items) == 239


def test_a_ticket_without_a_vector_is_404(api, conn):
    conn.execute("DELETE FROM ticket_embeddings WHERE ticket_id = 'T-30002'")
    assert api.get("/v1/tickets/T-30002/similar").status_code == 404


def test_only_one_version_can_be_current(conn):
    import psycopg
    import pytest

    conn.execute(
        "INSERT INTO embedding_versions (version, model, revision, dimensions)"
        " VALUES ('other-v1', 'another model', 'x', 384)"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("UPDATE embedding_versions SET is_current = true WHERE version = 'other-v1'")
