"""The compatibility matrix runs: SDK client x (in-process, stdio, HTTP) x (2026-07-28, 2025-11-25)."""

from scripts import compat


def test_every_row_of_the_matrix_passes():
    rows = compat.matrix()
    assert len(rows) == 6
    assert {(r["transport"], r["protocol"]) for r in rows} == {
        (t, p) for t in ("in-process", "stdio", "Streamable HTTP") for p in ("2026-07-28", "2025-11-25")
    }
    for r in rows:
        assert all(r.get(c) is True for c in compat.CHECKS), r
        if r["transport"] == "Streamable HTTP":
            assert r["no_token_refused"] is True
