"""The practice data loads, and the loader refuses to load it twice by accident."""

import pytest

from scripts import load

COUNTS = {
    "customers": 40,
    "tickets": 200,
    "messages": 334,  # 331 + the 3 whose ticket does not exist
    "attachments": 43,
    "documents": 36,
    "ai_runs": 294,
    "ticket_embeddings": 200,
}


def test_small_data_loads_with_the_expected_counts(empty_db_url):
    result = load.load(empty_db_url, "small", quiet=True, files=False)
    # From Module 2 on, the 3 messages whose ticket does not exist go to orphaned_messages.
    result["counts"]["messages"] += result["orphans"]
    assert result["counts"] == COUNTS


def test_loading_twice_needs_reset(db_url):
    with pytest.raises(SystemExit, match="--reset"):
        load.load(db_url, "small", quiet=True, files=False)
    result = load.load(db_url, "small", reset=True, quiet=True, files=False)
    assert result["counts"]["tickets"] == 200


def test_a_changed_data_file_stops_the_load(tmp_path, monkeypatch):
    folder = tmp_path / "small"
    folder.mkdir()
    (folder / "tickets.csv").write_text("changed\n")
    digest = "0" * 64
    (folder / "SHA256SUMS").write_text(f"{digest}  tickets.csv\n")
    with pytest.raises(SystemExit, match="missing or changed"):
        load.check_files(folder)
