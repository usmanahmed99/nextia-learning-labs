"""Compare prompt versions on the same fixed tickets with the same measures."""

from collections import Counter
from dataclasses import dataclass

from .data import Ticket


@dataclass
class Row:
    ticket: Ticket
    answer: dict | None   # the parsed answer, or None when there was no usable answer
    note: str = ""        # why there is no answer, or which rule rejected it


def score(rows: list[Row]) -> dict:
    """Team accuracy (tickets with an expected team), needs_human agreement, and the failures."""
    teams = [r for r in rows if r.ticket.team]
    answered = [r for r in rows if r.answer]
    team_ok = sum(1 for r in teams if r.answer and r.answer.get("team") == r.ticket.team)
    human_ok = sum(1 for r in rows if r.answer and r.answer.get("needs_human") == r.ticket.needs_human)
    human_true = [r for r in rows if r.ticket.needs_human]
    caught = sum(1 for r in human_true if r.answer and r.answer.get("needs_human") is True)
    return {
        "tickets": len(rows),
        "no_answer": len(rows) - len(answered),
        "team_correct": team_ok,
        "team_scored": len(teams),
        "needs_human_agree": human_ok,
        "needs_human_true_caught": f"{caught}/{len(human_true)}",
        "notes": dict(Counter(r.note for r in rows if r.note)),
    }


def misses(rows: list[Row]) -> list[str]:
    out = []
    for r in rows:
        a = r.answer or {}
        if not r.answer:
            out.append(f"{r.ticket.ticket_id}  no answer ({r.note})")
            continue
        if r.ticket.team and a.get("team") != r.ticket.team:
            out.append(f"{r.ticket.ticket_id}  team {a.get('team')} (expected {r.ticket.team}, {r.ticket.style})")
        if a.get("needs_human") != r.ticket.needs_human:
            out.append(f"{r.ticket.ticket_id}  needs_human {a.get('needs_human')} (expected {r.ticket.needs_human})")
    return out
