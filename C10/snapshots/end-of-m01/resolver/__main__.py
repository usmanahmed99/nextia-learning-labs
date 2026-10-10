"""The command line of the resolution workflow.

    python -m resolver tasks [--slice SLICE]
    python -m resolver show T-90103 [--expected]
    python -m resolver run T-90103 [--variant fixed|router|agent|agent_structured] [--model chat-small] [--repeat 1] [--trace]
    python -m resolver eval [--variant agent] [--model chat-small] [--repeat 1] [--slice S]
    python -m resolver compare

Nothing is written yet: the workflow proposes, and a person's approval comes in Module 4.
"""

import argparse

from .config import Settings, make_provider
from .data import load_task, load_tasks
from .evaluate import by_slice, run_and_score, summarise
from .runner import VARIANTS, new_state, run_task
from .systems import Faults, World
from .trace import render

RECORDED = [  # (variant, model) recorded for the course
    ("fixed", "chat-small"), ("router", "chat-small"), ("router", "chat-strong"), ("agent", "chat-small"),
    ("agent_structured", "chat-small"), ("agent_structured", "chat-strong"),
    ("agent_structured", "gemma3:4b"),
]


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
    state = run_task(task, args.variant, model, lambda request, meta: provider.complete(request, {**meta, "repeat": args.repeat}),
                     world, settings.limits(), state)
    print_outcome(state)
    if args.trace:
        print()
        print(render(state))


def eval_rows(variant, model, repeat=1, slice_=None):
    provider = make_provider(Settings.from_env())
    tasks = [t for t in load_tasks().values() if not slice_ or t.slice == slice_]
    return [run_and_score(t, variant, model, provider.complete, repeat)[0] for t in tasks]


def cmd_eval(args) -> None:
    model = args.model or Settings.from_env().model
    scores = eval_rows(args.variant, model, args.repeat, args.slice)
    s = summarise(scores)
    cost = "unknown" if s["cost_usd"] is None else f"US${s['cost_usd']:.4f}"
    print(f"{args.variant}, {model}, repeat {args.repeat}")
    print(f"Right proposal: {s['proposal_ok']}/{s['tasks']} | approvals it would ask for: {s['approvals_requested']} | "
          f"stopped: {s['stopped']} | steps per task: {s['steps_mean']} | tool calls: {s['tool_calls']} "
          f"({s['refused_calls']} refused) | tokens: {s['input_tokens']} in, {s['output_tokens']} out | {cost} | "
          f"model time per task: median {s['seconds_median']} s")
    print("By slice: " + ", ".join(f"{k} {v['proposal_ok']}/{v['tasks']}" for k, v in by_slice(scores).items()))
    for x in scores:
        if not x.proposal_ok:
            print(f"  {x.task_id} {x.slice}: expected {x.expected}, got {x.outcome}")


def cmd_compare(args) -> None:
    print(f"{'design':<18} {'model':<12} {'right':>7} {'approvals':>10} {'steps':>6} {'cost US$':>9} {'median s':>9}")
    for variant, model in RECORDED:
        s = summarise(eval_rows(variant, model))
        cost = "-" if s["cost_usd"] is None else f"{s['cost_usd']:.4f}"
        print(f"{variant:<18} {model:<12} {s['proposal_ok']:>4}/{s['tasks']:<2} {s['approvals_requested']:>10} "
              f"{s['steps_mean']:>6} {cost:>9} {s['seconds_median']:>9}")


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
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--trace", action="store_true")
    p = sub.add_parser("eval")
    p.add_argument("--variant", default="agent", choices=list(VARIANTS))
    p.add_argument("--model")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--slice")
    sub.add_parser("compare")
    args = ap.parse_args(argv)
    {"tasks": cmd_tasks, "show": cmd_show, "run": cmd_run, "eval": cmd_eval, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
