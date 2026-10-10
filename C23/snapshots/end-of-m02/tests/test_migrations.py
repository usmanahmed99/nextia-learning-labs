"""Module 3, lesson 3: migrations run in order, once, never change, and do not wait forever."""

import shutil

import psycopg
import pytest

from ticket_api import migrate


@pytest.fixture
def migrations(tmp_path, monkeypatch):
    folder = tmp_path / "migrations"
    shutil.copytree(migrate.MIGRATIONS, folder)
    monkeypatch.setattr(migrate, "MIGRATIONS", folder)
    return folder


def test_a_changed_migration_stops_everything(empty_db_url, migrations, capsys):
    assert migrate.main([], url=empty_db_url, quiet=True) == 0
    path = migrations / "005_integrity_constraints.sql"
    path.write_text(path.read_text() + "\n-- a small edit\n")
    (migrations / "999_new.sql").write_text("CREATE TABLE never_made (id int);")
    assert migrate.main([], url=empty_db_url) == 1
    assert (
        "005_integrity_constraints.sql was changed after it was applied" in capsys.readouterr().err
    )
    with psycopg.connect(empty_db_url) as conn:
        assert conn.execute("SELECT to_regclass('never_made')").fetchone()[0] is None


def test_a_no_transaction_migration_can_build_an_index_concurrently(db_url, migrations):
    (migrations / "900_index.sql").write_text(
        "-- migrate: no-transaction\nCREATE INDEX CONCURRENTLY IF NOT EXISTS t_subject_idx ON"
        " tickets (subject);\n"
    )
    assert migrate.main([], url=db_url, quiet=True) == 0
    with psycopg.connect(db_url) as conn:
        assert conn.execute("SELECT to_regclass('t_subject_idx')").fetchone()[0] == "t_subject_idx"


def test_concurrently_inside_a_transaction_fails(db_url, migrations, capsys):
    (migrations / "900_index.sql").write_text(
        "CREATE INDEX CONCURRENTLY t_subject_idx ON tickets (subject);\n"
    )
    assert migrate.main([], url=db_url, quiet=True) == 1
    err = capsys.readouterr().err
    assert (
        "900_index.sql failed: CREATE INDEX CONCURRENTLY cannot run inside a transaction block"
        in err
    )


def test_a_migration_that_waits_for_a_lock_stops(db_url, migrations, monkeypatch, capsys):
    monkeypatch.setenv("MIGRATION_LOCK_TIMEOUT", "1s")
    (migrations / "900_column.sql").write_text("ALTER TABLE ai_runs ADD COLUMN reviewed boolean;\n")
    holder = psycopg.connect(db_url)
    holder.execute("SELECT count(*) FROM ai_runs")  # an open transaction holds a lock on ai_runs
    try:
        assert migrate.main([], url=db_url) == 1
    finally:
        holder.rollback()
        holder.close()
    assert "waited more than 1s for a lock" in capsys.readouterr().err
    with psycopg.connect(db_url) as conn:
        cols = conn.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = 'ai_runs' AND column_name = 'reviewed'"
        ).fetchall()
    assert cols == []


def test_status_lists_every_migration(db_url, capsys):
    assert migrate.main(["--status"], url=db_url) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == len(list(migrate.MIGRATIONS.glob("*.sql")))
    assert all(line.startswith("applied") for line in out)
