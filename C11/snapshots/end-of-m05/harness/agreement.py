"""How far two raters agree: percent agreement and Cohen's kappa.

Percent agreement counts the items where both raters gave the same label. It looks better than it
is when one label is very common: two raters who both say "no" to almost everything agree a lot by
chance. Cohen's kappa removes the agreement that chance alone would give:

    kappa = (observed agreement - chance agreement) / (1 - chance agreement)

where chance agreement = the sum, over labels, of (share of rater 1 who used the label) x (share of
rater 2 who used it). kappa = 1: perfect; 0: no better than chance; below 0: worse than chance.
Worked example (tests/test_agreement.py): 10 replies, both say "ok" on 6, both "bad" on 1, they
differ on 3 -> observed 0.70; rater 1 says "ok" 8 times, rater 2 7 times -> chance
0.8 x 0.7 + 0.2 x 0.3 = 0.62 -> kappa = (0.70 - 0.62) / 0.38 = 0.21.
"""

from collections import Counter


def percent_agreement(a: list, b: list) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("Give two lists of the same, non-zero length (one label per item from each rater).")
    return sum(x == y for x, y in zip(a, b)) / len(a)


def chance_agreement(a: list, b: list) -> float:
    n = len(a)
    ca, cb = Counter(a), Counter(b)
    return sum((ca[label] / n) * (cb[label] / n) for label in set(ca) | set(cb))


def cohens_kappa(a: list, b: list) -> float:
    observed, chance = percent_agreement(a, b), chance_agreement(a, b)
    if chance == 1:
        return 1.0  # both raters used one and the same label everywhere: kappa is not informative
    return (observed - chance) / (1 - chance)


def within_one(a: list[int], b: list[int]) -> float:
    """For scores 1-5: the share of items where the two scores differ by at most 1."""
    return sum(abs(x - y) <= 1 for x, y in zip(a, b)) / len(a)


def confusion(a: list, b: list) -> dict:
    """label of rater 1 -> label of rater 2 -> count: where exactly the raters part."""
    table: dict = {}
    for x, y in zip(a, b):
        table.setdefault(x, Counter())[y] += 1
    return {k: dict(v) for k, v in sorted(table.items(), key=lambda kv: str(kv[0]))}
