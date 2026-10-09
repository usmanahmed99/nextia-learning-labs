"""The known-good first run: the collection and the questions are there, and the CLI works."""

import subprocess
import sys

from policy_assistant.documents import PROJECT, load_inventory


def test_inventory_has_the_whole_collection():
    docs = load_inventory()
    assert len(docs) == 36
    assert sum(d.access == "staff" for d in docs) == 6
    assert sum(d.language == "fr" for d in docs) == 2
    assert sorted(d.format for d in docs if d.format != "md") == ["html", "html", "pdf", "pdf"]
    assert all(d.path.exists() for d in docs)


def test_two_versions_of_the_returns_policy():
    versions = {d.version: d for d in load_inventory() if d.doc_id == "returns-policy"}
    assert versions["3"].effective_to == "2026-10-31"
    assert versions["4"].effective_from == "2026-11-01"


def test_questions_file():
    lines = (PROJECT / "questions" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 67


def test_cli_inventory():
    out = subprocess.run([sys.executable, "-m", "policy_assistant", "inventory"], cwd=PROJECT,
                         capture_output=True, text=True, check=True).stdout
    assert "36 documents: 6 staff-only, 2 in French, 4 not Markdown" in out
