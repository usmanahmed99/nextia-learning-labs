"""Read a run as a timeline: every model call, tool call, proposal, approval, write and stop, in order.

A trace shows what can be observed: the steps, the tool events and their results. It does not show
the model's hidden reasoning, and it does not need to: most failures are visible in the steps.
"""

import json

from .state import TaskState


def _short(value, n: int = 90) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= n else text[: n - 1] + "…"


def line(e) -> str:
    d = e.detail
    if e.kind == "model":
        calls = ", ".join(f"{n}({_short(a, 40)})" for n, a in d.get("calls", [])) or d.get("purpose", "")
        note = "  [replayed from a different request]" if d.get("note") else ""
        return f"model     {e.name}: {calls}  ({d.get('tokens_in')} in, {d.get('tokens_out')} out, {d.get('latency_s')} s){note}"
    if e.kind == "tool":
        result = "ok" if d.get("ok") else f"REFUSED {d.get('code')}: {_short(d.get('error'), 60)}"
        return f"tool      {e.name}({_short(d.get('arguments'), 50)}) -> {result}"
    if e.kind == "plan":
        return f"plan      {_short(d.get('plan'), 110)}"
    if e.kind == "proposal":
        if not d.get("accepted"):
            return f"proposal  REFUSED: {_short(d.get('problem'), 100)}"
        args = d.get("arguments") or {}
        acts = ", ".join(f"{a.get('tool')} {a.get('order_id')}" for a in args.get("actions") or []) or "no change"
        return f"proposal  {args.get('outcome')} ({args.get('rule')}): {acts}"
    if e.kind == "approval":
        return f"approval  {e.name} by {d.get('approver')} ({d.get('role')}) {d.get('note', '')}"
    if e.kind == "write":
        return f"write     {e.name} op {d.get('op_id')} -> {d.get('outcome')}"
    if e.kind == "reconcile":
        return f"reconcile {e.name} op {d.get('op_id')} -> {'found: it happened' if d.get('found') else 'not found'}"
    if e.kind == "stop":
        return f"stop      {e.name}"
    if e.kind == "error":
        return f"error     {e.name}: {_short(d.get('message'), 100)}"
    return f"{e.kind:<9} {e.name} {_short(d, 100)}"


def render(state: TaskState) -> str:
    u = state.usage
    cost = "unknown" if u.cost_usd is None else f"US${u.cost_usd:.5f}"
    head = [f"Run {state.run_id}: {state.variant}, {state.model}, ticket {state.task_id}, status {state.status}",
            f"{u.model_calls} model call(s), {u.input_tokens} tokens in, {u.output_tokens} out, {cost}, "
            f"{u.model_seconds} s waiting for the model"]
    rows = [f"{e.step:>3}  {line(e)}" for e in state.events]
    return "\n".join(head + [""] + rows)
