"""The command line for the support assistant.

    python -m support_assistant cases [--attacks] [--slice S]
    python -m support_assistant show CASE
    python -m support_assistant run CASE [--design start] [--model M]
    python -m support_assistant eval [--attacks] [--design start] [--model M] [--slice S]
    python -m support_assistant compare [CASE] [--attacks]
    python -m support_assistant changes
    python -m support_assistant reset

There is one design so far: `start`, the weak start. `run` uses your practice database (work/);
`reset` makes it fresh. `eval` and `compare` run every case on a fresh copy of the data.
"""

import argparse

from .assistant import DESIGNS
from .config import Settings, make_provider
from .data import load_attacks, load_case, load_tasks
from .evaluate import summarise
from .runner import fresh_world, run_and_score
from .systems import World, reset_practice_db


def _cases(attacks: bool, slice_: str | None):
    cases = (load_attacks() if attacks else load_tasks()).values()
    return [c for c in cases if not slice_ or c.slice == slice_]


def _provider_and_model(args):
    settings = Settings.from_env()
    model = args.model or settings.model
    return make_provider(settings).complete, model


def cmd_cases(args):
    for c in _cases(args.attacks, args.slice):
        extra = f"  goal: {c.goal}" if c.kind == "attack" else ""
        print(f"{c.case_id}  [{c.kind}/{c.slice}]  {c.tenant}  {c.user}  {c.ticket_id}{extra}")


def cmd_show(args):
    c = load_case(args.case)
    print(f"{c.case_id}  [{c.kind}/{c.slice}]  tenant {c.tenant}  signed in as {c.user}")
    print(f"Request: {c.request}")
    t = fresh_world().ticket(c.ticket_id)
    print(f"Ticket {c.ticket_id} (customer {t['customer_id']}):")
    print(f"  {t['text']}")
    if t["attachments"]:
        print(f"  attachments: {', '.join(t['attachments'])}")
    if c.note:
        print(f"Note: {c.note}")
    if c.kind == "attack":
        print(f"What the attack tries to do: {c.goal}")


def cmd_run(args):
    complete, model = _provider_and_model(args)
    c = load_case(args.case)
    state, score = run_and_score(c, complete, model, args.design, world=World())
    print(f"{c.case_id}  design {args.design}  model {model}  role {state.role}")
    print(f"Stop: {state.stop_reason} | {state.usage_calls} model call(s) | "
          f"{state.input_tokens} in, {state.output_tokens} out | "
          f"US${state.cost_usd if state.cost_usd is not None else 0:.5f}")
    for e in state.tool_events:
        mark = "ok" if e.ok else ("blocked" if not e.allowed else "fail")
        print(f"  tool {e.tool} -> {mark}" + (f" ({e.blocked_reason or e.code})" if mark != "ok" else "")
              + (f": {e.summary}" if e.summary else ""))
    for p in state.proposals:
        tag = "executed" if p.executed else "proposed"
        print(f"  write {p.tool} {p.arguments} -> {tag}")
    print(f"Reply draft: {state.answer[:400]}")
    if c.kind == "attack":
        print(f"Attack succeeded: {score['success']}"
              + (f" (goal reached: {'; '.join(score['goal_reached'])})" if score["success"]
                 else f" (stopped by {score['blocked_by']})" if score["blocked_by"] else " (the model did not do it)"))
        print("Unsafe side effects: " + (", ".join(score["side_effects"]) or "none"))
    else:
        print(f"Task success: {score['success']}" + ("" if score["success"] else f" ({'; '.join(score['reasons'])})"))
    if state.replay_notes:
        print(f"Note: {state.replay_notes} recorded model decision(s) were made for a different request than yours "
              "(your code or data differs from the recording). Each was replayed and checked against your state.")


def cmd_eval(args):
    complete, model = _provider_and_model(args)
    cases = _cases(args.attacks, args.slice)
    scores = [run_and_score(c, complete, model, args.design)[1] for c in cases]
    s = summarise(scores)
    what = "attacks that succeeded" if args.attacks else "tasks done right"
    print(f"design {args.design}, model {model}: {s['success']}/{s['n']} {what}")
    print("by slice: " + ", ".join(f"{k} {v}" for k, v in s["by_slice"].items()))
    if "unsafe" in s:
        print(f"runs with an unsafe side effect: {s['unsafe']}/{s['n']}")


def cmd_compare(args):
    complete, model = _provider_and_model(args)
    cases = [load_case(args.case)] if args.case else _cases(args.attacks, None)
    header = "attack success (lower is better)" if (args.case and load_case(args.case).kind == "attack") \
        or args.attacks else "task success (higher is better)"
    print(f"{header}, model {model}:")
    for design in DESIGNS:
        scores = [run_and_score(c, complete, model, design)[1] for c in cases]
        print(f"  {design:<9} {sum(x['success'] for x in scores)}/{len(scores)}")


def cmd_changes(args):
    for table, rows in World().changes().items():
        print(f"{table}: {len(rows)}")


def cmd_reset(args):
    reset_practice_db()
    print("Fresh practice database.")


def main():
    ap = argparse.ArgumentParser(prog="support_assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cases"); p.add_argument("--attacks", action="store_true"); p.add_argument("--slice")
    p.set_defaults(fn=cmd_cases)
    p = sub.add_parser("show"); p.add_argument("case"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("run"); p.add_argument("case"); p.add_argument("--design", default="start", choices=DESIGNS)
    p.add_argument("--model"); p.set_defaults(fn=cmd_run)
    p = sub.add_parser("eval"); p.add_argument("--attacks", action="store_true")
    p.add_argument("--design", default="start", choices=DESIGNS); p.add_argument("--model")
    p.add_argument("--slice"); p.set_defaults(fn=cmd_eval)
    p = sub.add_parser("compare"); p.add_argument("case", nargs="?"); p.add_argument("--attacks", action="store_true")
    p.add_argument("--model"); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("changes"); p.set_defaults(fn=cmd_changes)
    p = sub.add_parser("reset"); p.set_defaults(fn=cmd_reset)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
