"""Measures per case, and the same measures by slice.

Every measure here is a list of per-case values (1 = passed, 0 = failed), so that every number traces
back to its cases. An overall score can hide a slice that fails: always look at both.
"""

from .scorers.criteria import all_passed
from .scorers.decisions import needs_human_correct, team_correct


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



def by_slice(cases, values: dict[str, float]) -> dict[str, tuple[float, int]]:
    """slice -> (mean, number of cases). A slice of 10 cases moves 0.1 with one case."""
    groups: dict[str, list[float]] = {}
    for c in cases:
        if c.case_id in values:
            groups.setdefault(c.slice, []).append(values[c.case_id])
    return {s: (sum(v) / len(v), len(v)) for s, v in sorted(groups.items())}
