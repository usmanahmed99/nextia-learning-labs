import json

import pytest

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


def test_report_for_some_categories(tmp_path):
    output = tmp_path / "teams.json"
    argv = ["data/tickets.csv", "--category", " Billing ", "--category", "shipping"]
    assert main([*argv, "--output", str(output)]) == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["by_category"] == {"billing": 2, "shipping": 1}
    assert summary["categories"] == ["billing", "shipping"]
    assert summary["valid_records"] == 9
    assert len(summary["rejected"]) == 6


def test_help_describes_the_category_option(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "--category NAME" in capsys.readouterr().out


def test_web_form_export_has_one_line_per_team(tmp_path):
    output = tmp_path / "week.json"
    assert main(["data/web-form-export.csv", "--output", str(output)]) == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    expected = {"account": 1, "billing": 3, "login": 4, "shipping": 2}
    assert summary["by_category"] == expected
