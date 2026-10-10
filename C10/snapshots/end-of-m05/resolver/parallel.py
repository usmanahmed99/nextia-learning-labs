"""Parallel work with explicit inputs, outputs and merge rules.

`gather` runs independent reads at the same time. It is safe because the reads do not depend on each
other and change nothing; the merge rule is explicit: one result per call, in the order of the calls,
a failed read stays a failed read (it is never dropped silently).

`merge_proposals` merges the work of two workers that each looked at part of a ticket (for example one
order each). The rule: actions on different orders are combined; two different proposals for the same
order are a conflict, and a conflict goes to a person. Code never picks a winner by guessing.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from .schema import Resolution
from .systems import World
from .tools import ToolResult, run_read


def gather(calls: list[tuple[str, dict]], customer_id: str, world: World, max_workers: int = 3,
           delay_s: float = 0.0) -> list[ToolResult]:
    """Run the read calls in parallel; the results come back in the order of `calls`.
    `delay_s` simulates a slow service (each read waits that long), to see the time saved."""
    def one(call):
        if delay_s:
            time.sleep(delay_s)
        return run_read(call[0], call[1], customer_id, world)

    with ThreadPoolExecutor(max_workers) as pool:
        return list(pool.map(one, calls))


class Conflict(Exception):
    pass


def merge_proposals(a: Resolution, b: Resolution) -> Resolution:
    """Combine two partial resolutions. Raises Conflict when they disagree about the same order."""
    if "hand_to_person" in (a.outcome, b.outcome):
        keep = a if a.outcome == "hand_to_person" else b
        return keep
    by_order: dict[str, list] = {}
    for source in (a, b):
        for action in source.actions:
            by_order.setdefault(action.order_id, []).append((source, action))
    for order_id, items in by_order.items():
        sources = {id(s) for s, _ in items}
        if len(sources) > 1:
            first = sorted(x.model_dump_json() for s, x in items if s is a)
            second = sorted(x.model_dump_json() for s, x in items if s is b)
            if first != second:
                raise Conflict(f"the two workers propose different actions for {order_id}")
    actions, seen = [], set()
    for source in (a, b):
        for action in source.actions:
            key = action.model_dump_json()
            if key not in seen:
                seen.add(key)
                actions.append(action)
    outcome = "resolve" if actions else ("ask_customer" if "ask_customer" in (a.outcome, b.outcome) else "reply_only")
    return Resolution(outcome=outcome, rule=f"{a.rule}+{b.rule}", actions=actions,
                      reply=f"{a.reply}\n\n{b.reply}".strip()[:2000], reason=f"{a.reason} {b.reason}".strip()[:600])
