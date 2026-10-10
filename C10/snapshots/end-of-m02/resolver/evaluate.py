"""Compare designs on the same tasks: did each one propose the right resolution, and at what cost?

Until Module 4 nothing is written, so this scores the PROPOSAL: the outcome (resolve, reply_only,
ask_customer, hand_to_person) and the exact actions. Module 4 adds approval and the writes; then the
evaluation also checks what changed in the database.
"""

import shutil
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .data import SEED_DB, Task
from .state import TaskState
from .systems import Faults, World

MATCH_FIELDS = ("tool", "order_id", "sku", "quantity", "amount", "reason")


def norm(action: dict) -> tuple:
    a = dict(action)
    code = a.pop("reason_code", None)
    if code is not None:
        a["reason"] = code
    if a.get("amount") is not None:
        a["amount"] = round(float(a["amount"]), 2)
    return tuple(a.get(f) for f in MATCH_FIELDS)


def same_actions(got: list[dict], expected: list[dict]) -> bool:
    return sorted(map(norm, got), key=str) == sorted(map(norm, expected), key=str)


@dataclass
class TaskScore:
    task_id: str
    slice: str
    expected: str
    outcome: str                 # a stopped run goes to a person
    proposal_ok: bool            # the right outcome and exactly the right actions
    stop_reason: str
    approvals: int               # proposals with actions: each one will need a person's approval
    steps: int = 0
    tool_calls: int = 0
    refused_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0
    seconds: float = 0.0


def score(task: Task, state: TaskState) -> TaskScore:
    p = state.proposal
    if p is None:   # a stopped run goes to a person: right when a person was expected
        outcome, ok = "hand_to_person", "hand_to_person" in task.outcomes_accepted
    else:
        outcome = p.outcome
        ok = p.outcome in task.outcomes_accepted and same_actions(
            [a.model_dump() for a in p.actions], task.expected["actions"] if p.outcome == task.expected["outcome"] else [])
    return TaskScore(task_id=task.task_id, slice=task.slice, expected=task.expected["outcome"], outcome=outcome,
                     proposal_ok=ok, stop_reason=state.stop_reason, approvals=int(bool(p and p.actions)),
                     steps=state.step, tool_calls=len(state.evidence),
                     refused_calls=sum(1 for e in state.evidence if not e.ok), input_tokens=state.usage.input_tokens,
                     output_tokens=state.usage.output_tokens, cost_usd=state.usage.cost_usd,
                     seconds=state.usage.model_seconds)


def run_and_score(task: Task, variant: str, model: str, complete, repeat: int = 1,
                  workdir: Path | None = None) -> tuple[TaskScore, TaskState]:
    from .runner import run_task

    workdir = workdir or Path(tempfile.mkdtemp(prefix="resolver-eval-"))
    db = workdir / f"{task.task_id}.sqlite"
    shutil.copyfile(SEED_DB, db)
    world = World(db, task.task_id, Faults(task.faults))
    state = run_task(task, variant, model, lambda request, meta: complete(request, {**meta, "repeat": repeat}), world)
    return score(task, state), state


def summarise(scores: list[TaskScore]) -> dict:
    n = len(scores)
    costs = [s.cost_usd for s in scores if s.cost_usd is not None]
    return {
        "tasks": n,
        "proposal_ok": sum(s.proposal_ok for s in scores),
        "approvals_requested": sum(s.approvals for s in scores),
        "stopped": sum(s.stop_reason not in ("finished", "") for s in scores),
        "steps_mean": round(statistics.mean(s.steps for s in scores), 2) if n else 0,
        "tool_calls": sum(s.tool_calls for s in scores),
        "refused_calls": sum(s.refused_calls for s in scores),
        "input_tokens": sum(s.input_tokens for s in scores),
        "output_tokens": sum(s.output_tokens for s in scores),
        "cost_usd": round(sum(costs), 4) if len(costs) == n else None,
        "seconds_median": round(statistics.median(s.seconds for s in scores), 2) if n else 0,
    }


def by_slice(scores: list[TaskScore]) -> dict:
    out = {}
    for s in scores:
        out.setdefault(s.slice, []).append(s)
    return {k: {"tasks": len(v), "proposal_ok": sum(x.proposal_ok for x in v)} for k, v in out.items()}
