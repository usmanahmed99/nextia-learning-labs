"""Where a request spends its time, for the Server-Timing response header.

    timer = Timer()
    with timer("db"):
        ...
    response.headers["Server-Timing"] = timer.header()   # db;dur=3.1, classify;dur=812.4

Browsers show this header in their developer tools; scripts.breakdown adds it up over
many requests.
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager


class Timer:
    def __init__(self) -> None:
        self.parts: dict[str, float] = {}

    @contextmanager
    def __call__(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            ms = (time.perf_counter() - started) * 1000
            self.parts[name] = self.parts.get(name, 0.0) + ms

    def header(self) -> str:
        return ", ".join(f"{name};dur={ms:.1f}" for name, ms in self.parts.items())


def parse(header: str) -> dict[str, float]:
    """The parts of a Server-Timing header: {"db": 3.1, "classify": 812.4}."""
    out = {}
    for item in header.split(","):
        name, _, rest = item.strip().partition(";dur=")
        if name and rest:
            out[name] = float(rest)
    return out
