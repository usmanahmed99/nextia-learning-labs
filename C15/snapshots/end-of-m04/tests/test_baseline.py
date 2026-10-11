"""Today's report for the sample file, kept as it is.

This test pins the report of data/tickets.csv before any change. If a change
makes it fail, that change altered the report: check that this was intended.
"""

import json

from ticket_cleaner.cli import main


def test_report_of_the_sample_file_is_unchanged(tmp_path):
    output = tmp_path / "summary.json"
    assert main(["data/tickets.csv", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "status": "open",
        "valid_records": 9,
        "selected": 4,
        "by_category": {"billing": 2, "login": 1, "shipping": 1},
        "average_priority": 2.0,
        "rejected": [
            {"row": 7, "problems": ["unknown status 'opne'"]},
            {"row": 8, "problems": ["missing id"]},
            {"row": 9, "problems": ["priority must be 1, 2 or 3, not 'high'"]},
            {"row": 11, "problems": ["priority must be 1, 2 or 3, not '5'"]},
            {"row": 13, "problems": ["duplicate id T-1003"]},
            {"row": 14, "problems": ["missing category"]},
        ],
    }
