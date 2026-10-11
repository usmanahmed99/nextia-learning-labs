"""The README's claims are checked, so that it stays true after a change."""

import re
from pathlib import Path

from ticket_cleaner.cli import main, make_parser

README = Path("README.md").read_text(encoding="utf-8")


def test_the_readme_shows_the_real_output(tmp_path, capsys):
    assert main(["data/tickets.csv", "--output", str(tmp_path / "s.json")]) == 0
    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line == "15 rows: 9 valid, 6 rejected."
    assert first_line in README


def test_every_option_of_the_command_is_in_the_readme():
    options = set(re.findall(r"--[a-z-]+", make_parser().format_help()))
    options.discard("--help")
    documented = set(re.findall(r"^\| `(--[a-z-]+)`", README, re.MULTILINE))
    assert options == documented
