"""The command line for the support assistant.

    python -m support_assistant cases [--attacks] [--slice S]
    python -m support_assistant show CASE
    python -m support_assistant boundaries
    python -m support_assistant run CASE [--design D] [--model M]
    python -m support_assistant eval [--attacks] [--design D] [--model M] [--slice S]
    python -m support_assistant compare [CASE] [--attacks]
    python -m support_assistant approvals [--status pending]
    python -m support_assistant approve APPROVAL --as USER [--reason TEXT]
    python -m support_assistant reject APPROVAL --as USER [--reason TEXT]
    python -m support_assistant changes
    python -m support_assistant reset

Designs: start, prompt, filter, controls, secure (see support_assistant/designs.py).
`run`, `approve` and `reject` use your practice database (work/); `reset` makes
it fresh. `eval` and `compare` run every case on a fresh copy of the data.
"""

import argparse

from .config import Settings, make_provider, redact
from .data import load_attacks, load_case, load_tasks
from .designs import DESIGNS, controls_for
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


def cmd_boundaries(args):
    from .boundaries import check, load
    m = load()
    for side in ("trusted", "untrusted"):
        print(f"{side.capitalize()} (inside the trust boundary):" if side == "trusted"
              else "Untrusted (outside: data, never instructions):")
        for s in m["sources"]:
            if s["trusted"] == (side == "trusted"):
                print(f"  {s['name']:<24} from {s['from']}; reaches the model as {s['enters_as']}")
    print("Tools (what each one can reach with no controls):")
    for name, t in m["tools"].items():
        print(f"  {name:<20} {t['kind']:<5} {t['reaches']}" + (f"; changes: {t['changes']}" if t.get("changes") else ""))
    for problem in check(m):
        print(f"Check: {problem}")


def cmd_run(args):
    complete, model = _provider_and_model(args)
    c = load_case(args.case)
    world = World(redact_log=controls_for(args.design).redact_logs)
    state, score = run_and_score(c, complete, model, args.design, world=world)
    print(f"{c.case_id}  design {args.design}  model {model}  role {state.role}")
    print(f"Stop: {state.stop_reason} | {state.usage_calls} model call(s) | "
          f"{state.input_tokens} in, {state.output_tokens} out | "
          f"US${state.cost_usd if state.cost_usd is not None else 0:.5f}")
    for e in state.tool_events:
        mark = "ok" if e.ok else ("blocked" if not e.allowed else "fail")
        print(f"  tool {e.tool} -> {mark}" + (f" ({e.blocked_reason or e.code})" if mark != "ok" else "")
              + (f": {e.summary}" if e.summary else ""))
    for p in state.proposals:
        tag = ("refused" if p.refused_reason else "executed" if p.executed
               else f"waiting for approval {p.approval_id}" if p.approval_id else "proposed")
        print(f"  write {p.tool} {p.arguments} -> {tag}" + (f": {p.refused_reason}" if p.refused_reason else ""))
    if state.filter_verdict:
        print(f"  input filter: {state.filter_verdict}")
    print(f"Reply draft: {state.answer[:400]}")
    for msg in state.errors:                 # what the provider or a control said (secrets redacted)
        print(f"  run note: {redact(msg)[:300]}")
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


def cmd_approvals(args):
    from .approvals import listing
    rows = listing(World(), args.status)
    if not rows:
        print("No approvals." if not args.status else f"No {args.status} approvals.")
    for a in rows:
        args_text = ", ".join(f"{k}={v}" for k, v in a["arguments"].items() if k != "body")
        print(f"{a['approval_id']}  {a['status']:<8} {a['tenant']:<9} {a['case_id']:<8} {a['tool']} {args_text}"
              + (f"  [{a['decided_by']}: {a['reason']}]" if a["status"] != "pending" else ""))


def cmd_decide(args):
    from .approvals import decide
    print(decide(World(), args.approval, args.as_user, args.cmd == "approve", args.reason or ""))


def cmd_changes(args):
    for table, rows in World().changes().items():
        print(f"{table}: {len(rows)}")


def cmd_reset(args):
    reset_practice_db()
    print("Fresh practice database.")


def main():
    ap = argparse.ArgumentParser(prog="support_assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    designs = list(DESIGNS)
    p = sub.add_parser("cases"); p.add_argument("--attacks", action="store_true"); p.add_argument("--slice")
    p.set_defaults(fn=cmd_cases)
    p = sub.add_parser("show"); p.add_argument("case"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("boundaries"); p.set_defaults(fn=cmd_boundaries)
    p = sub.add_parser("run"); p.add_argument("case"); p.add_argument("--design", default="secure", choices=designs)
    p.add_argument("--model"); p.set_defaults(fn=cmd_run)
    p = sub.add_parser("eval"); p.add_argument("--attacks", action="store_true")
    p.add_argument("--design", default="secure", choices=designs); p.add_argument("--model")
    p.add_argument("--slice")
    p.set_defaults(fn=cmd_eval)
    p = sub.add_parser("compare"); p.add_argument("case", nargs="?"); p.add_argument("--attacks", action="store_true")
    p.add_argument("--model"); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("approvals"); p.add_argument("--status", choices=["pending", "approved", "rejected"])
    p.set_defaults(fn=cmd_approvals)
    for name in ("approve", "reject"):
        p = sub.add_parser(name); p.add_argument("approval"); p.add_argument("--as", dest="as_user", required=True)
        p.add_argument("--reason"); p.set_defaults(fn=cmd_decide)
    p = sub.add_parser("changes"); p.set_defaults(fn=cmd_changes)
    p = sub.add_parser("reset"); p.set_defaults(fn=cmd_reset)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
