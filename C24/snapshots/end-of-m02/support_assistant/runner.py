"""Run one case on a fresh practice database, then score it. Used by the CLI, the facts script and
the tests."""

import tempfile
from pathlib import Path
from typing import Callable

from .assistant import run_case
from .data import Case
from .evaluate import score_attack, score_task
from .systems import World, reset_practice_db


def fresh_world() -> World:
    db = Path(tempfile.mkdtemp(prefix="c24-run-")) / "helpdesk.sqlite"
    reset_practice_db(db)
    return World(db=db)


def run_and_score(case: Case, complete: Callable, model: str, design: str, world: World | None = None,
                  max_steps: int = 8):
    world = world or fresh_world()
    state = run_case(case, complete, world, model, design, max_steps)
    score = score_task(state, case, world) if case.kind == "task" else score_attack(state, case, world)
    return state, score
