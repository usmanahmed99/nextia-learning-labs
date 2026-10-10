"""Load shapes for Locust (Module 6): how many users send tickets, second by second.

Each file next to this one (ramp.py, steady.py, burst.py, soak.py) is a locustfile with
the Customer user and one shape. Run one with --headless and no -u/-t (the shape decides):

    PACE_SECONDS=1 locust -f loadtest/burst.py --host http://127.0.0.1:8000 --headless

With PACE_SECONDS=1, the number of users is the arrival rate in tickets per second.
The times are short on purpose, so that a test fits on a laptop. A real soak test runs
for hours, on an environment that is like production and that you may break.
"""

from locust import LoadTestShape


class Stages(LoadTestShape):
    """A list of (until second, users). The test stops after the last stage."""

    # Not a shape on its own: without this line, Locust would also find Stages in each
    # file and could run it (no stages, so the test would stop at once).
    abstract = True
    stages: list[tuple[int, int]] = []

    def tick(self):
        t = self.get_run_time()
        for until, users in self.stages:
            if t < until:
                return users, max(users, 1)
        return None
