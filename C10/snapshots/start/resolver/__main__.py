"""The command line of the resolution workflow.

    python -m resolver tasks [--slice SLICE]
    python -m resolver show T-90103 [--expected]
    python -m resolver run T-90103 [--variant fixed|router|agent|agent_structured] [--model chat-small] [--trace]

Nothing is written yet: the workflow proposes, and a person's approval comes in Module 4.
"""

import argparse

from .config import Settings, make_provider
from .data import load_task, load_tasks
from .runner import VARIANTS, new_state, run_task
from .systems import Faults, World
from .trace import render


def print_outcome(state) -> None:
    p = state.proposal
    for e in state.events:
        if e.kind == "model" and e.detail.get("note"):
            print(f"Note: {e.detail['note']}")
            break
    if p is None:
        print(f"Stopped: {state.stop_reason}. No proposal: the ticket goes to a person.")
        return
    cost = "unknown" if state.usage.cost_usd is None else f"US${state.usage.cost_usd:.5f}"
    print(f"Outcome: {p.outcome} (rule {p.rule}) | {state.usage.model_calls} model call(s), "
          f"{len(state.evidence)} tool call(s) | {state.usage.input_tokens} tokens in, {state.usage.output_tokens} out | "
          f"{cost}")
    for a in p.actions:
        print(f"Proposed (not done): {a.model_dump()}")
    print(f"Reply draft: {p.reply}")


def cmd_tasks(args) -> None:
    tasks = [t for t in load_tasks().values() if not args.slice or t.slice == args.slice]
    for t in tasks:
        text = t.text.replace("\n", " ") or "(empty ticket)"
        print(f"{t.task_id}  {t.slice:<13} {text[:80]}")
    print(f"{len(tasks)} tasks")


def cmd_show(args) -> None:
    t = load_task(args.task)
    print(f"{t.task_id} | customer {t.customer_id} | slice {t.slice}")
    print(f"Attachments: {', '.join(t.attachments) or 'none'}")
    print(t.text or "(empty ticket)")
    if t.faults:
        print("Simulated failures for this task: " + ", ".join(f"{f['tool']} {f['mode']}" for f in t.faults))
    if args.expected:
        print(f"Expected: {t.expected['outcome']} (rule {t.expected['rule']}) {t.expected['actions']}")
        if t.expected.get("note"):
            print(f"Why: {t.expected['note']}")


def cmd_run(args) -> None:
    settings = Settings.from_env()
    task = load_task(args.task)
    model = args.model or settings.model
    state = new_state(task, args.variant, model, f"{task.task_id}-{args.variant}-{model}")
    world = World(ticket_id=task.task_id, faults=Faults(task.faults))
    provider = make_provider(settings)
    print(f"Run {state.run_id} | {VARIANTS[args.variant]} | {model}")
    state = run_task(task, args.variant, model, provider.complete, world, settings.limits(), state)
    print_outcome(state)
    if args.trace:
        print()
        print(render(state))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m resolver")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("tasks")
    p.add_argument("--slice")
    p = sub.add_parser("show")
    p.add_argument("task")
    p.add_argument("--expected", action="store_true")
    p = sub.add_parser("run")
    p.add_argument("task")
    p.add_argument("--variant", default="agent", choices=list(VARIANTS))
    p.add_argument("--model")
    p.add_argument("--trace", action="store_true")
    args = ap.parse_args(argv)
    {"tasks": cmd_tasks, "show": cmd_show, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
