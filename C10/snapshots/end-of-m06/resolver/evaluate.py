"""Task-level evaluation: score the outcome AND what changed in the systems, not only the reply.

For each task: a fresh copy of the practice database, the run (recorded decisions by default), the
approval, the execution, then a look at the database. A task succeeds when
- the outcome is the expected one (or an accepted alternative),
- the changes in the database are exactly the expected changes (no missing one, no extra one, no duplicate),
- no forbidden change happened, and the reply does not say what it must not say.

The approver: `all` approves every proposal as it is (the worst case: it shows what the design would
write on its own); `labels` stands in for Grace: it approves only a proposal whose actions match the
expected ones and rejects the rest (it uses the task labels, so it is a perfect approver; real people are not).
"""

import json
import re
import shutil
import statistics
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .approval import decide, required_role
from .data import SEED_DB, Task
from .execute import execute
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


def denied_tools(task: Task) -> set[str]:
    return {f["tool"] for f in task.faults if f["mode"] == "denied"}


def expected_effects(task: Task) -> list[dict]:
    """The changes that should be in the database at the end (a refused write leaves none)."""
    return [a for a in task.expected["actions"] if a["tool"] not in denied_tools(task)]


def is_forbidden(change: dict, rules: list[dict]) -> bool:
    """A change matches a forbidden rule when every field of the rule matches (amounts to the cent)."""
    for rule in rules:
        if all(round(float(change.get(k) or 0), 2) == round(float(v), 2) if k == "amount" else change.get(k) == v
               for k, v in rule.items()):
            return True
    return False


@dataclass
class TaskScore:
    task_id: str
    slice: str
    expected: str
    outcome: str                 # the final outcome (a stopped run goes to a person)
    proposal_ok: bool            # the right outcome and the right proposed actions (before approval)
    effects_ok: bool             # the database changed exactly as expected
    success: bool
    stop_reason: str
    approvals: int               # approval requests (0 or 1)
    changes: list[dict] = field(default_factory=list)
    unexpected: list[dict] = field(default_factory=list)   # changes that should not have happened
    missing: list[dict] = field(default_factory=list)
    forbidden: list[dict] = field(default_factory=list)
    said: list[str] = field(default_factory=list)          # must_not_say patterns found in the reply
    steps: int = 0
    tool_calls: int = 0
    refused_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0
    seconds: float = 0.0


def score(task: Task, state: TaskState, changes: list[dict]) -> TaskScore:
    p = state.proposal
    outcome = "hand_to_person" if p is None else p.outcome
    if p is not None and state.status == "handed_to_person" and p.actions:
        outcome = "hand_to_person"      # rejected, or a write was refused: a person takes over
    proposed = [a.model_dump() for a in p.actions] if p else []
    if p is None:   # a stopped run goes to a person: right when a person was expected
        proposal_ok = "hand_to_person" in task.outcomes_accepted
    else:
        proposal_ok = p.outcome in task.outcomes_accepted and \
            same_actions(proposed, task.expected["actions"] if p.outcome == task.expected["outcome"] else [])
    got = [{k: c.get(k) for k in ("tool", "order_id", "sku", "quantity", "amount", "reason", "reason_code",
                                  "payment_id")} for c in changes]
    exp = expected_effects(task)
    remaining = list(map(norm, exp))
    unexpected = []
    for c in got:
        if norm(c) in remaining:
            remaining.remove(norm(c))
        else:
            unexpected.append(c)
    missing = [e for e in exp if norm(e) in remaining]
    forbidden = [c for c in got if is_forbidden(c, task.forbidden)]
    final_expected = "hand_to_person" if denied_tools(task) else task.expected["outcome"]
    accepted = {final_expected, *task.acceptable_outcomes}
    reply = p.reply if p else ""
    said = [pat for pat in task.must_not_say if re.search(pat, reply)]
    effects_ok = not unexpected and not missing
    tools = state.evidence
    return TaskScore(
        task_id=task.task_id, slice=task.slice, expected=task.expected["outcome"], outcome=outcome,
        proposal_ok=proposal_ok, effects_ok=effects_ok,
        success=proposal_ok and outcome in accepted and effects_ok and not forbidden and not said,
        stop_reason=state.stop_reason, approvals=int(bool(p and p.actions)), changes=got, unexpected=unexpected,
        missing=missing, forbidden=forbidden, said=said, steps=state.step, tool_calls=len(tools),
        refused_calls=sum(1 for e in tools if not e.ok), input_tokens=state.usage.input_tokens,
        output_tokens=state.usage.output_tokens, cost_usd=state.usage.cost_usd, seconds=state.usage.model_seconds)


def run_and_score(task: Task, variant: str, model: str, complete, approver: str = "all", repeat: int = 1,
                  workdir: Path | None = None) -> tuple[TaskScore, TaskState]:
    from .runner import run_task

    workdir = workdir or Path(tempfile.mkdtemp(prefix="resolver-eval-"))
    db = workdir / f"{task.task_id}.sqlite"
    shutil.copyfile(SEED_DB, db)
    world = World(db, task.task_id, Faults(task.faults))

    def with_repeat(request, meta):
        return complete(request, {**meta, "repeat": repeat})

    state = run_task(task, variant, model, with_repeat, world)
    if state.status == "waiting_approval":
        ok = approver == "all" or same_actions([a.model_dump() for a in state.proposal.actions],
                                               task.expected["actions"])
        decide(state, ok, f"eval ({approver})", "grace" if ok else required_role(state),
               "approved as proposed" if approver == "all" else ("matches the policy" if ok else "rejected"))
        if ok:
            execute(state, world)
    return score(task, state, world.changes()), state


def summarise(scores: list[TaskScore]) -> dict:
    n = len(scores)
    costs = [s.cost_usd for s in scores if s.cost_usd is not None]
    return {
        "tasks": n,
        "success": sum(s.success for s in scores),
        "proposal_ok": sum(s.proposal_ok for s in scores),
        "effects_ok": sum(s.effects_ok for s in scores),
        "tasks_with_unexpected_changes": sum(bool(s.unexpected) for s in scores),
        "unexpected_changes": sum(len(s.unexpected) for s in scores),
        "forbidden_changes": sum(len(s.forbidden) for s in scores),
        "approvals_requested": sum(s.approvals for s in scores),
        "stopped": sum(s.stop_reason not in ("finished", "") for s in scores),
        "steps_mean": round(statistics.mean(s.steps for s in scores), 2) if n else 0,
        "tool_calls": sum(s.tool_calls for s in scores),
        "refused_calls": sum(s.refused_calls for s in scores),
        "input_tokens": sum(s.input_tokens for s in scores),
        "output_tokens": sum(s.output_tokens for s in scores),
        "cost_usd": round(sum(costs), 4) if len(costs) == n else None,
        "seconds_median": round(statistics.median(s.seconds for s in scores), 2) if n else 0,
        "seconds_p95": round(sorted(s.seconds for s in scores)[max(0, int(0.95 * n) - 1)], 2) if n else 0,
    }


def by_slice(scores: list[TaskScore]) -> dict:
    out = {}
    for s in scores:
        out.setdefault(s.slice, []).append(s)
    return {k: {"tasks": len(v), "success": sum(x.success for x in v)} for k, v in out.items()}


def as_dicts(scores: list[TaskScore]) -> list[dict]:
    return [json.loads(json.dumps(asdict(s))) for s in scores]
