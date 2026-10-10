"""The course data: the resolution tasks, the practice database and the policy passages."""

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data"
# Your practice copies: the database, the saved runs, the memory (made on first use). Tests use another folder.
WORK = Path(os.environ.get("RESOLVER_WORK", PROJECT / "work"))
SEED_DB = DATA / "larkfield.sqlite"
TODAY = date(2026, 10, 9)        # the course's "today": the data and the expected outcomes use it


@dataclass
class Task:
    task_id: str
    customer_id: str
    text: str
    attachments: list[str]
    slice: str
    source: str
    expected: dict
    acceptable_outcomes: list[str] = field(default_factory=list)
    forbidden: list[dict] = field(default_factory=list)
    must_not_say: list[str] = field(default_factory=list)
    faults: list[dict] = field(default_factory=list)

    @property
    def outcomes_accepted(self) -> list[str]:
        return [self.expected["outcome"], *self.acceptable_outcomes]


def load_tasks(path: Path = DATA / "tasks.jsonl") -> dict[str, Task]:
    tasks = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        t = Task(**json.loads(line))
        tasks[t.task_id] = t
    return tasks


def load_task(task_id: str) -> Task:
    tasks = load_tasks()
    if task_id not in tasks:
        raise KeyError(f"No task {task_id}. Run `python -m resolver tasks` to see the task IDs.")
    return tasks[task_id]


def load_passages(path: Path = DATA / "policy_passages.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
