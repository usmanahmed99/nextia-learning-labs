"""Run one task with one design (variant) and one model: the entry point of `run` and `eval`."""

from datetime import datetime
from typing import Callable

from .agent import run_agent, run_workers
from .data import Task
from .loop import Limits
from .state import TaskState
from .systems import Faults, World
from .workflow import run_fixed, run_router

VARIANTS = {
    "fixed": "fixed workflow: code decides every step; the model drafts the reply",
    "router": "router: the model chooses one path; code does the rest",
    "agent": "single agent with tool calling: the model chooses every step",
    "agent_structured": "single agent with one JSON step per call (for models without tool calling)",
    "workers": "two workers: an investigator reads, a resolver decides",
}


def new_state(task: Task, variant: str, model: str, run_id: str | None = None) -> TaskState:
    run_id = run_id or f"{task.task_id}-{variant}-{model}-{datetime.now().strftime('%H%M%S%f')[:9]}"
    return TaskState(run_id=run_id, task_id=task.task_id, customer_id=task.customer_id, variant=variant, model=model,
                     goal=task.text, attachments=task.attachments)


def run_task(task: Task, variant: str, model: str, complete: Callable, world: World | None = None,
             limits: Limits = Limits(), state: TaskState | None = None, on_step=None) -> TaskState:
    """Run the task until it has a proposal (or stops). Nothing is written: writes wait for approval."""
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant {variant!r}: use one of {', '.join(VARIANTS)}.")
    world = world or World(ticket_id=task.task_id, faults=Faults(task.faults))
    state = state or new_state(task, variant, model)
    if variant == "fixed":
        run_fixed(state, complete, world)
    elif variant == "router":
        run_router(state, complete, world)
    elif variant == "agent":
        run_agent(state, complete, world, "tools", limits, on_step)
    elif variant == "agent_structured":
        run_agent(state, complete, world, "structured", limits, on_step)
    else:
        run_workers(state, complete, world, limits, on_step=on_step)
    if state.proposal is None:
        state.status = "stopped"
    elif state.proposal.actions:
        state.status = "waiting_approval"
    elif state.proposal.outcome == "hand_to_person":
        state.status = "handed_to_person"
    else:
        state.status = "done"
    return state
