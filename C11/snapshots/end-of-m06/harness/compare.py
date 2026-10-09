"""Compare a baseline and a candidate on the same cases: paired differences, bootstrap intervals,
slices and the variation between repeated runs.

Every measure here is a list of per-case values (1 = passed, 0 = failed, or a judge score), so that
every number traces back to its cases.

The bootstrap: you have one evaluation set, but you want to know how much a number would move with
another set of the same size. So you draw a new set of the same size from your cases, with
replacement (some cases twice, some not at all), compute the number again, and repeat 2,000 times.
The middle 95% of those numbers is a 95% confidence interval. For a comparison, draw the same cases
for both systems (a paired bootstrap): the difference then reflects the cases, not two unrelated draws.
"""

from dataclasses import dataclass

import numpy as np

from .scorers.criteria import all_passed
from .scorers.decisions import needs_human_correct, team_correct

SEED = 2026
RESAMPLES = 2000


def decisions_ok(case, output) -> int:
    """1 when both decisions are right (team, if the case has one, and needs_human)."""
    team = team_correct(case, output)
    return int(needs_human_correct(case, output) and team is not False)


def criteria_ok(case, output) -> int:
    return int(all_passed(case, output))


MEASURES = {"decisions": decisions_ok, "criteria": criteria_ok}


def per_case(cases, outputs, measure: str) -> dict[str, float]:
    fn = MEASURES[measure]
    return {c.case_id: float(fn(c, outputs.get(c.case_id))) for c in cases}


@dataclass(frozen=True)
class Interval:
    value: float
    low: float
    high: float
    n: int

    def __str__(self) -> str:
        return f"{self.value:.3f} [{self.low:.3f}, {self.high:.3f}] (n={self.n})"


def bootstrap_mean(values: list[float], resamples: int = RESAMPLES, seed: int = SEED) -> Interval:
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(resamples, len(x)))
    means = x[idx].mean(axis=1)
    return Interval(float(x.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), len(x))


def paired_difference(base: dict[str, float], cand: dict[str, float], resamples: int = RESAMPLES,
                      seed: int = SEED) -> Interval:
    """Mean of (candidate - baseline) over the same cases, with a paired bootstrap interval."""
    ids = sorted(set(base) & set(cand))
    diff = [cand[i] - base[i] for i in ids]
    return bootstrap_mean(diff, resamples, seed)


def wins_losses(base: dict[str, float], cand: dict[str, float]) -> dict[str, list[str]]:
    """Which cases got better, worse or stayed the same: the cases behind a difference."""
    out = {"better": [], "worse": [], "same": []}
    for i in sorted(set(base) & set(cand)):
        out["better" if cand[i] > base[i] else "worse" if cand[i] < base[i] else "same"].append(i)
    return out


def by_slice(cases, values: dict[str, float]) -> dict[str, Interval]:
    groups: dict[str, list[float]] = {}
    for c in cases:
        if c.case_id in values:
            groups.setdefault(c.slice, []).append(values[c.case_id])
    return {s: bootstrap_mean(v) for s, v in sorted(groups.items())}


def repeat_spread(cases, runs_outputs: list[dict], measure: str) -> dict:
    """The same system run several times on the same cases: the spread of the total, and the cases
    whose result changed between runs (the model does not give the same answer twice)."""
    per_run = [per_case(cases, outs, measure) for outs in runs_outputs]
    totals = [sum(v.values()) for v in per_run]
    unstable = sorted(i for i in per_run[0] if len({v[i] for v in per_run}) > 1)
    return {"runs": len(per_run), "cases": len(per_run[0]), "totals": totals, "min": min(totals), "max": max(totals),
            "mean": float(np.mean(totals)), "unstable_cases": unstable}
