"""Scorers for the assistant's two decisions: the team and needs_human.

Plain functions with no model: the base of the evaluation pyramid. Each returns numbers you can check
by hand on a few cases.
"""

from dataclasses import dataclass

TEAMS = ("delivery", "returns", "payment", "warranty", "account")


def answered(output) -> dict | None:
    """The parsed answer, or None when the system gave no usable answer (error, cut off, not JSON)."""
    return output.answer if output is not None else None


def team_correct(case, output) -> bool | None:
    """True or False; None when the case has no team to score (no readable request)."""
    if not case.expected.team:
        return None
    answer = answered(output)
    return answer is not None and answer.get("team") == case.expected.team


def needs_human_correct(case, output) -> bool:
    answer = answered(output)
    return answer is not None and answer.get("needs_human") == case.expected.needs_human


@dataclass(frozen=True)
class Counts:
    """A confusion table for one yes/no decision ("a person must handle it")."""
    tp: int  # said yes, and yes was right (caught)
    fp: int  # said yes, but no was right (a false alarm)
    fn: int  # said no, but yes was right (missed)
    tn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def accuracy(self) -> float:
        n = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / n if n else 0.0


def needs_human_counts(cases, outputs) -> Counts:
    """An answer that is missing counts as "no": the ticket would not reach a person."""
    tp = fp = fn = tn = 0
    for case in cases:
        answer = answered(outputs.get(case.case_id))
        said = bool(answer and answer.get("needs_human"))
        if said and case.expected.needs_human:
            tp += 1
        elif said:
            fp += 1
        elif case.expected.needs_human:
            fn += 1
        else:
            tn += 1
    return Counts(tp, fp, fn, tn)


def team_accuracy(cases, outputs) -> tuple[int, int]:
    """(correct, scored): cases without a team are not scored."""
    results = [team_correct(c, outputs.get(c.case_id)) for c in cases]
    scored = [r for r in results if r is not None]
    return sum(scored), len(scored)


def team_confusion(cases, outputs) -> dict[str, dict[str, int]]:
    """expected team -> predicted team -> count ("none" when there was no answer)."""
    table: dict[str, dict[str, int]] = {t: {} for t in TEAMS}
    for case in cases:
        if not case.expected.team:
            continue
        answer = answered(outputs.get(case.case_id))
        predicted = answer.get("team", "none") if answer else "none"
        row = table[case.expected.team]
        row[predicted] = row.get(predicted, 0) + 1
    return table


def per_team(cases, outputs) -> dict[str, dict[str, float]]:
    """Precision and recall for each team, one team against the others."""
    out = {}
    for team in TEAMS:
        tp = fp = fn = 0
        for case in cases:
            if not case.expected.team:
                continue
            answer = answered(outputs.get(case.case_id))
            predicted = answer.get("team") if answer else None
            if predicted == team and case.expected.team == team:
                tp += 1
            elif predicted == team:
                fp += 1
            elif case.expected.team == team:
                fn += 1
        out[team] = {"precision": tp / (tp + fp) if tp + fp else 0.0, "recall": tp / (tp + fn) if tp + fn else 0.0,
                     "support": tp + fn}
    return out
