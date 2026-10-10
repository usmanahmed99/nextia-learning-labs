import json

from ticket_cleaner.cli import main


def test_report_for_pending_tickets(tmp_path):
    output = tmp_path / "pending.json"
    exit_code = main(
        ["data/tickets.csv", "--status", "pending", "--output", str(output)]
    )
    assert exit_code == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["selected"] == 2
    assert len(summary["rejected"]) == 6


def test_missing_file_gives_exit_code_1(tmp_path):
    assert main([str(tmp_path / "missing.csv")]) == 1
