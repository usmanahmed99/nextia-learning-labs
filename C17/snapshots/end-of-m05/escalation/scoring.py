"""Score tickets with a loaded bundle. The API and the batch job both use this.

The work for each request is split into three timed steps, so that a
benchmark can show where the time goes:

    frame     the checked tickets → a table with the training columns
    prepare   the pipeline's preprocessing (one-hot, impute, scale)
    model     the logistic regression's score
"""

import time
from dataclasses import dataclass, field

from escalation.bundle import Bundle
from escalation.contract import TicketFeatures, to_frame, unknown_categories


@dataclass
class Result:
    score: float
    flag: bool
    warnings: list[str]


@dataclass
class Timings:
    """Milliseconds spent in each step of one call."""

    steps: dict[str, float] = field(default_factory=dict)

    def header(self) -> str:
        """The value of a Server-Timing header, for example "frame;dur=0.41"."""
        return ", ".join(f"{name};dur={ms:.2f}" for name, ms in self.steps.items())


def score_tickets(bundle: Bundle, tickets: list[TicketFeatures]) -> tuple[list[Result], Timings]:
    timings = Timings()
    started = time.perf_counter()

    frame = to_frame(tickets)
    now = time.perf_counter()
    timings.steps["frame"] = (now - started) * 1000

    preprocess, model = bundle.pipeline[:-1], bundle.pipeline[-1]
    prepared = preprocess.transform(frame)
    started, now = now, time.perf_counter()
    timings.steps["prepare"] = (now - started) * 1000

    scores = model.predict_proba(prepared)[:, 1]
    started, now = now, time.perf_counter()
    timings.steps["model"] = (now - started) * 1000

    results = [
        Result(
            score=float(score),
            flag=bool(score >= bundle.threshold),
            warnings=unknown_categories(ticket, bundle.known),
        )
        for ticket, score in zip(tickets, scores)
    ]
    return results, timings
