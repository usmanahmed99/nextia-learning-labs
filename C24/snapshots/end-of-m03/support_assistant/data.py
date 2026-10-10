"""Load the course data: the cases (tasks and attacks), the tickets, the help-desk database and
the fake websites. Nothing here reaches a real system."""

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data"
WORK = Path(os.environ.get("ASSISTANT_WORK", PROJECT / "work"))
SEED_DB = DATA / "helpdesk.sqlite"
VFS = DATA / "vfs"           # the server's file area (read-only seed; a copy lives in work/)
WEB = DATA / "web"
TODAY = date(2026, 10, 9)    # the course's "today"
HOLIDAYS = {date(2026, 9, 7), date(2026, 10, 12)}


@dataclass
class Case:
    case_id: str
    kind: str                # "task" or "attack"
    slice: str
    tenant: str
    user: str                # the signed-in staff member (a user ID / sub)
    ticket_id: str
    request: str             # what the staff member asks the assistant to do
    language: str
    expect: dict             # writes, answer_any, tools_any (tasks)
    forbidden_text: list = field(default_factory=list)
    goal: str = ""           # for an attack: what it tries to make the assistant do
    note: str = ""
    constructed: bool = False


def load_cases(name: str) -> dict[str, Case]:
    path = DATA / name
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        c = Case(**json.loads(line))
        out[c.case_id] = c
    return out


def load_tasks() -> dict[str, Case]:
    return load_cases("tasks.jsonl")


def load_attacks() -> dict[str, Case]:
    return load_cases("attacks.jsonl")


def all_cases() -> dict[str, Case]:
    return {**load_tasks(), **load_attacks()}


def load_case(case_id: str) -> Case:
    cases = all_cases()
    if case_id not in cases:
        raise KeyError(f"No case {case_id}. Run `python -m support_assistant cases` to list them.")
    return cases[case_id]


def made_up_secrets() -> list[str]:
    """The canary strings. The output checks look for them; no real secret is ever here."""
    return json.loads((DATA / "secrets.json").read_text(encoding="utf-8"))["made_up_secrets"]
