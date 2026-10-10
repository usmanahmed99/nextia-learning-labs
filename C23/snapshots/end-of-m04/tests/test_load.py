"""The practice data loads, and the loader refuses to load it twice by accident."""

import pytest

from scripts import load

# Larkfield's small data (the databases course) and Bramble Books (the authentication course).
COUNTS = {
    "customers": {"larkfield": 40, "bramble": 12},
    "tickets": {"larkfield": 200, "bramble": 40},
    "messages": {"larkfield": 331, "bramble": 58},  # + 3 Larkfield messages whose ticket is gone
    "attachments": {"larkfield": 43, "bramble": 14},
    "documents": {"larkfield": 36, "bramble": 3},
    "ai_runs": {"larkfield": 294, "bramble": 69},
    "ticket_embeddings": {"larkfield": 200, "bramble": 40},
}


def test_small_data_loads_with_the_expected_counts(empty_db_url):
    result = load.load(empty_db_url, "small", quiet=True, files=False)
    assert result["by_tenant"] == COUNTS
    assert result["orphans"] == 3


def test_the_people_and_their_memberships_load(db_url, conn):
    rows = conn.execute(
        "SELECT tenant_id, user_id, role FROM memberships ORDER BY tenant_id, user_id"
    ).fetchall()
    assert [(r["tenant_id"], r["user_id"], r["role"]) for r in rows] == [
        ("bramble", "usr-camille", "read_only"),
        ("bramble", "usr-ines", "owner"),
        ("larkfield", "usr-camille", "staff"),
        ("larkfield", "usr-grace", "owner"),
        ("larkfield", "usr-omar", "read_only"),
        ("larkfield", "usr-sam", "staff"),
    ]
    users = conn.execute("SELECT count(*) AS n FROM users").fetchone()["n"]
    assert users == 7  # Tomás has no membership; Kwame is a platform administrator


def test_loading_twice_needs_reset(db_url):
    with pytest.raises(SystemExit, match="--reset"):
        load.load(db_url, "small", quiet=True, files=False)
    result = load.load(db_url, "small", reset=True, quiet=True, files=False)
    assert result["counts"]["tickets"] == 240


def test_a_changed_data_file_stops_the_load(tmp_path, monkeypatch):
    folder = tmp_path / "small"
    folder.mkdir()
    (folder / "tickets.csv").write_text("changed\n")
    digest = "0" * 64
    (folder / "SHA256SUMS").write_text(f"{digest}  tickets.csv\n")
    with pytest.raises(SystemExit, match="missing or changed"):
        load.check_files(folder)
