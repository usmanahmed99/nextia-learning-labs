"""Production feedback: what a month of use tells you, and what it does not.

The log in data/production/feedback_log.jsonl is SIMULATED for the course (no real usage exists):
see its builder in the course's reference folder. Three things to look for:
- thumbs are biased: few customers give one, and unhappy ones give one more often;
- agent edits are a better signal: every draft is read, so every draft can be edited;
- drift: a topic that the evaluation set does not cover appears, or a language grows.
New cases found here go to the development set after a person labels them. The holdout set stays frozen.
"""

import json
import random
from collections import Counter
from pathlib import Path

from .dataset import DATA

LOG = DATA / "production" / "feedback_log.jsonl"


def load_log(path: Path = LOG) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def by_week(rows: list[dict], fn) -> dict[int, float]:
    weeks: dict[int, list] = {}
    for r in rows:
        weeks.setdefault(r["week"], []).append(r)
    return {w: round(fn(rs), 3) for w, rs in sorted(weeks.items())}


def summary(rows: list[dict]) -> dict:
    thumbs = Counter(r["thumb"] for r in rows)
    return {
        "tickets": len(rows),
        "thumbs given": f"{thumbs['up'] + thumbs['down']} ({(thumbs['up'] + thumbs['down']) / len(rows):.1%}); "
                        f"up {thumbs['up']}, down {thumbs['down']}",
        "agent edit rate by week": by_week(rows, lambda rs: sum(r["agent_edited"] for r in rs) / len(rs)),
        "thumbs-down share of thumbs by week": by_week(
            rows, lambda rs: sum(r["thumb"] == "down" for r in rs) / max(1, sum(r["thumb"] != "none" for r in rs))),
        "new topic (not in the evaluation set) by week": by_week(
            rows, lambda rs: sum(r["topic"] == "price_adjustment" for r in rs) / len(rs)),
        "French share by week": by_week(rows, lambda rs: sum(r["language"] == "fr" for r in rs) / len(rs)),
    }


def review_sample(rows: list[dict], per_week: int = 10, seed: int = 7) -> list[str]:
    """A fixed random sample per week for a person to read: not only the tickets with a thumbs-down."""
    rng = random.Random(seed)
    out = []
    for week in sorted({r["week"] for r in rows}):
        tickets = sorted(r["ticket"] for r in rows if r["week"] == week)
        out += sorted(rng.sample(tickets, min(per_week, len(tickets))))
    return out
