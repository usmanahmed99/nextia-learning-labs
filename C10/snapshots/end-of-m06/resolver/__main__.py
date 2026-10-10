"""The command line of the resolution workflow.

    python -m resolver tasks [--slice SLICE]
    python -m resolver show T-90103
    python -m resolver run T-90103 [--variant agent] [--model chat-small] [--repeat 1] [--trace] [--fault TOOL:MODE[:TIMES]]
    python -m resolver approve RUN_ID --as agent [--name Amira] [--interrupt before-write|after-write] [--naive-retry]
    python -m resolver reject RUN_ID --as agent [--note "..."]
    python -m resolver resume RUN_ID
    python -m resolver trace RUN_ID|T-90103
    python -m resolver runs
    python -m resolver changes
    python -m resolver eval [--variant agent] [--model chat-small] [--repeat 1] [--slice S] [--approve all|labels]
    python -m resolver compare
    python -m resolver reset [--all]
"""

import argparse
import json
import sys
from pathlib import Path

from .approval import ApprovalError, approval_request, decide, required_role
from .checkpoint import CheckpointStore
from .config import Settings, make_provider
from .data import load_task, load_tasks
from .evaluate import by_slice, run_and_score, summarise
from .execute import ExecutionRefused, Interrupted, execute
from .runner import VARIANTS, new_state, run_task
from .systems import PRACTICE_DB, Faults, World, reset_practice_db
from .trace import render

RECORDED = [  # (variant, model, repeats) recorded for the course
    ("fixed", "chat-small", 1), ("router", "chat-small", 1), ("router", "chat-strong", 1),
    ("agent", "chat-small", 3), ("agent_structured", "chat-small", 1), ("agent_structured", "chat-strong", 3),
    ("workers", "chat-small", 3), ("agent_structured", "gemma3:4b", 1),
]


def parse_faults(specs: list[str]) -> list[dict]:
    out = []
    for spec in specs or []:
        parts = spec.split(":")
        out.append({"tool": parts[0], "mode": parts[1], "times": int(parts[2]) if len(parts) > 2 else 1})
    return out


def world_for(state, task, extra_faults=()) -> World:
    faults = Faults([*task.faults, *extra_faults])
    for tool, mode in state.faults_seen:          # a resumed run does not see a used failure again
        if faults.left.get((tool, mode), 0) > 0:
            faults.left[(tool, mode)] -= 1
    return World(PRACTICE_DB, task.task_id, faults)


def keep_faults(state, world) -> None:
    state.faults_seen = [list(f) for f in world.faults.seen] if not state.faults_seen else \
        state.faults_seen + [list(f) for f in world.faults.seen[len(state.faults_seen):]]


def print_outcome(state) -> None:
    p = state.proposal
    for e in state.events:
        if e.kind == "model" and e.detail.get("note"):
            print(f"Note: {e.detail['note']}")
            break
    if p is None:
        print(f"Stopped: {state.stop_reason}. No proposal: the ticket goes to a person.")
        for err in state.errors[-1:]:
            print(f"Last error: {err}")
        return
    cost = "unknown" if state.usage.cost_usd is None else f"US${state.usage.cost_usd:.5f}"
    print(f"Outcome: {p.outcome} (rule {p.rule}) | {state.usage.model_calls} model call(s), "
          f"{len(state.evidence)} tool call(s) | {state.usage.input_tokens} tokens in, {state.usage.output_tokens} out | "
          f"{cost}")
    if p.actions:
        print()
        print(approval_request(state))
    else:
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
    store = CheckpointStore()
    n = 1 + sum(1 for r in store.list() if r[0].startswith(f"{task.task_id}-{args.variant}-{model}-"))
    state = new_state(task, args.variant, model, f"{task.task_id}-{args.variant}-{model}-{n}")
    world = world_for(state, task, parse_faults(args.fault))
    provider = make_provider(settings)

    def complete(request, meta):
        return provider.complete(request, {**meta, "repeat": args.repeat})

    print(f"Run {state.run_id} | {VARIANTS[args.variant]} | {model}")
    state = run_task(task, args.variant, model, complete, world, settings.limits(), state,
                     on_step=lambda s: store.save(s))
    keep_faults(state, world)
    store.save(state)
    print_outcome(state)
    if args.trace:
        print()
        print(render(state))
    if state.status == "waiting_approval":
        print(f"\nNothing has changed yet. Next: python -m resolver approve {state.run_id} --as "
              f"{required_role(state)}   (or: reject)")


def _decide(args, approve: bool) -> None:
    store = CheckpointStore()
    state = store.load(args.run_id)
    task = load_task(state.task_id)
    try:
        decide(state, approve, args.name or args.role, args.role, args.note or "")
    except ApprovalError as e:
        sys.exit(f"Not approved: {e}")
    store.save(state)
    if not approve:
        print(f"Rejected by {args.name or args.role}. Nothing was written; the ticket goes to a person.")
        return
    world = world_for(state, task, parse_faults(args.fault))
    _execute(state, world, store, args.naive_retry, args.interrupt)


def _execute(state, world, store, naive=False, interrupt="") -> None:
    def save(s):
        keep_faults(s, world)
        store.save(s)
    try:
        execute(state, world, save, naive=naive, interrupt=interrupt or "")
    except Interrupted as e:
        save(state)
        print(f"The process stopped: {e}. Resume with: python -m resolver resume {state.run_id}")
        return
    except ExecutionRefused as e:
        sys.exit(f"Not executed: {e}")
    for op in state.operations:
        print(f"{op.tool} {op.arguments.get('order_id')}: {op.status} (operation {op.op_id}, {op.attempts} call(s))"
              + (f" {op.error}" if op.error else ""))
    print(f"Status: {state.status}")


def cmd_resume(args) -> None:
    store = CheckpointStore()
    state = store.load(args.run_id)
    task = load_task(state.task_id)
    print(f"Resuming {state.run_id} (status {state.status})")
    if state.status == "executing":
        _execute(state, world_for(state, task), store)
    elif state.status == "running":
        settings = Settings.from_env()
        provider = make_provider(settings)
        world = world_for(state, task)
        state = run_task(task, state.variant, state.model, provider.complete, world, settings.limits(), state,
                         on_step=lambda s: store.save(s))
        keep_faults(state, world)
        store.save(state)
        print_outcome(state)
    elif state.status == "waiting_approval":
        print(approval_request(state))
    else:
        print(f"Nothing to resume: the run is {state.status}.")


def cmd_trace(args) -> None:
    store = CheckpointStore()
    state = store.latest(args.run) if args.run.count("-") == 1 else store.load(args.run)
    if state is None:
        sys.exit(f"No run for {args.run}.")
    print(render(state))


def cmd_runs(args) -> None:
    for run_id, task_id, variant, model, status, updated in CheckpointStore().list():
        print(f"{run_id:<40} {status:<17} {updated}")


def cmd_changes(args) -> None:
    changes = World(PRACTICE_DB).changes()
    for c in changes:
        what = {"request_refund": lambda c: f"{c['amount']:.2f} {c['reason_code']}",
                "create_return_label": lambda c: f"{c['sku']} {c['reason']}",
                "reship_item": lambda c: f"{c['sku']} x {c['quantity']}"}[c["tool"]](c)
        print(f"{c['created_at']}  {c['ticket_id']}  {c['tool']:<20} {c['order_id']}  {what}  (operation {c['op_id']})")
    print(f"{len(changes)} change(s) in the practice database")


def eval_rows(variant, model, repeat, approver, slice_=None, task_ids=None):
    provider = make_provider(Settings.from_env())
    tasks = [t for t in load_tasks().values() if (not slice_ or t.slice == slice_) and (not task_ids or t.task_id in task_ids)]
    return [run_and_score(t, variant, model, provider.complete, approver, repeat)[0] for t in tasks]


def cmd_eval(args) -> None:
    model = args.model or Settings.from_env().model
    scores = eval_rows(args.variant, model, args.repeat, args.approve, args.slice,
                       args.tasks.split(",") if args.tasks else None)
    s = summarise(scores)
    cost = "unknown" if s["cost_usd"] is None else f"US${s['cost_usd']:.4f}"
    print(f"{args.variant}, {model}, repeat {args.repeat}, approver: {args.approve}")
    print(f"Task success: {s['success']}/{s['tasks']} | right proposal: {s['proposal_ok']} | database right: "
          f"{s['effects_ok']} | unexpected changes: {s['unexpected_changes']} (forbidden: {s['forbidden_changes']}) | "
          f"approvals asked: {s['approvals_requested']} | stopped: {s['stopped']}")
    print(f"Steps per task: {s['steps_mean']} | tool calls: {s['tool_calls']} ({s['refused_calls']} refused) | "
          f"tokens: {s['input_tokens']} in, {s['output_tokens']} out | cost: {cost} | "
          f"model time per task: median {s['seconds_median']} s, p95 {s['seconds_p95']} s")
    print("By slice: " + ", ".join(f"{k} {v['success']}/{v['tasks']}" for k, v in by_slice(scores).items()))
    failed = [x for x in scores if not x.success]
    if failed:
        print("Not successful:")
        for x in failed:
            extra = f" unexpected {x.unexpected}" if x.unexpected else ""
            print(f"  {x.task_id} {x.slice}: expected {x.expected}, got {x.outcome}"
                  f"{'' if x.proposal_ok else ' (wrong proposal)'}{extra}{' stop ' + x.stop_reason if x.stop_reason not in ('finished', '') else ''}")
    if args.save:
        out = Path(args.save)
        out.write_text(json.dumps({"summary": s, "tasks": [x.__dict__ for x in scores]}, indent=1, default=str))
        print(f"Saved to {out}")


def cmd_compare(args) -> None:
    print(f"{'design':<18} {'model':<12} {'success':>8} {'proposal':>9} {'unexpected':>11} {'approvals':>10} "
          f"{'steps':>6} {'cost US$':>9} {'median s':>9}")
    for variant, model, _ in RECORDED:
        s = summarise(eval_rows(variant, model, 1, "all"))
        cost = "-" if s["cost_usd"] is None else f"{s['cost_usd']:.4f}"
        print(f"{variant:<18} {model:<12} {s['success']:>5}/{s['tasks']:<2} {s['proposal_ok']:>9} "
              f"{s['unexpected_changes']:>11} {s['approvals_requested']:>10} {s['steps_mean']:>6} {cost:>9} "
              f"{s['seconds_median']:>9}")


def cmd_reset(args) -> None:
    reset_practice_db()
    print(f"Fresh practice database: {PRACTICE_DB}")
    if args.all:
        for name in ("runs.sqlite", "memory.sqlite"):
            path = PRACTICE_DB.parent / name
            if path.exists():
                path.unlink()
        print("Saved runs and memory deleted.")


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
    p.add_argument("--fault", action="append")
    p.add_argument("--trace", action="store_true")
    for name, approve in (("approve", True), ("reject", False)):
        p = sub.add_parser(name)
        p.add_argument("run_id")
        p.add_argument("--as", dest="role", required=True, choices=["agent", "team_lead", "grace"])
        p.add_argument("--name")
        p.add_argument("--note")
        p.add_argument("--fault", action="append")
        p.add_argument("--interrupt", choices=["before-write", "after-write"])
        p.add_argument("--naive-retry", action="store_true")
        p.set_defaults(approve=approve)
    p = sub.add_parser("resume")
    p.add_argument("run_id")
    p = sub.add_parser("trace")
    p.add_argument("run")
    sub.add_parser("runs")
    sub.add_parser("changes")
    p = sub.add_parser("eval")
    p.add_argument("--variant", default="agent", choices=list(VARIANTS))
    p.add_argument("--model")
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--slice")
    p.add_argument("--tasks")
    p.add_argument("--approve", default="all", choices=["all", "labels"])
    p.add_argument("--save")
    sub.add_parser("compare")
    p = sub.add_parser("reset")
    p.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)
    {"tasks": cmd_tasks, "show": cmd_show, "run": cmd_run, "resume": cmd_resume, "trace": cmd_trace,
     "runs": cmd_runs, "changes": cmd_changes, "eval": cmd_eval, "compare": cmd_compare, "reset": cmd_reset,
     "approve": lambda a: _decide(a, True), "reject": lambda a: _decide(a, False)}[args.command](args)


if __name__ == "__main__":
    main()
