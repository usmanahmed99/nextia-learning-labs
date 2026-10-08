"""Model health signals, kept in memory for the last WINDOW scored tickets.

The service cannot know at once whether a score was right: the true answer
(escalated or not) arrives 72 hours later. So it watches signals that it can
see now:

    contract errors     tickets rejected before scoring, by field
    unknown categories  values the model never saw, by feature
    flag rate           the share of tickets flagged, against the review capacity
    mean score          a change means the inputs or the model changed
    latency             p50 and p95 of the scoring time

Each worker process has its own monitor. With two workers, ask each one, or
send the prediction log to one place (C25 does this properly).
"""

import threading
from collections import Counter, deque
from dataclasses import dataclass

import numpy as np

WINDOW = 1000
MIN_FOR_ALERTS = 200


@dataclass
class Scored:
    score: float
    flag: bool
    ms: float
    shadow_score: float | None = None
    shadow_flag: bool | None = None


class Monitor:
    def __init__(self, capacity: float):
        self.capacity = capacity
        self.recent: deque[Scored] = deque(maxlen=WINDOW)
        self.contract_errors: Counter[str] = Counter()
        self.unknown: Counter[str] = Counter()
        self.scored_total = 0
        self.lock = threading.Lock()

    def contract_error(self, fields: list[str]) -> None:
        with self.lock:
            self.contract_errors.update(fields)

    def scored(self, item: Scored, warnings: list[str]) -> None:
        with self.lock:
            self.recent.append(item)
            self.scored_total += 1
            self.unknown.update(w.split(":")[0] for w in warnings)

    def report(self) -> dict:
        with self.lock:
            items = list(self.recent)
            errors, unknown, total = dict(self.contract_errors), dict(self.unknown), self.scored_total
        report = {
            "scored_total": total,
            "window": len(items),
            "contract_errors": errors,
            "unknown_categories": unknown,
            "flag_rate": None,
            "mean_score": None,
            "latency_ms": None,
            "shadow": None,
            "alerts": [],
        }
        if not items:
            return report
        scores = np.array([i.score for i in items])
        flags = np.array([i.flag for i in items])
        ms = np.array([i.ms for i in items])
        report["flag_rate"] = round(float(flags.mean()), 3)
        report["mean_score"] = round(float(scores.mean()), 4)
        report["latency_ms"] = {
            "p50": round(float(np.percentile(ms, 50)), 2),
            "p95": round(float(np.percentile(ms, 95)), 2),
        }
        shadowed = [i for i in items if i.shadow_score is not None]
        if shadowed:
            shadow_flags = np.array([i.shadow_flag for i in shadowed])
            live_flags = np.array([i.flag for i in shadowed])
            report["shadow"] = {
                "compared": len(shadowed),
                "flag_rate": round(float(shadow_flags.mean()), 3),
                "mean_score": round(float(np.mean([i.shadow_score for i in shadowed])), 4),
                "same_flag": round(float((shadow_flags == live_flags).mean()), 3),
            }
        if len(items) >= MIN_FOR_ALERTS and report["flag_rate"] > self.capacity:
            report["alerts"].append(
                f"flag rate {report['flag_rate']:.3f} is above the review capacity {self.capacity:.2f}"
            )
        if report["shadow"] and len(shadowed) >= MIN_FOR_ALERTS and report["shadow"]["flag_rate"] > self.capacity:
            report["alerts"].append(
                f"shadow flag rate {report['shadow']['flag_rate']:.3f} is above the review capacity {self.capacity:.2f}"
            )
        return report
