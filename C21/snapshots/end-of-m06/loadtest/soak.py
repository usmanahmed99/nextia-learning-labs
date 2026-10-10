"""Soak (short): 3 users for 10 minutes. Does anything grow that should not (memory,
connections, queue age, errors)? A real soak test runs for hours."""

from locustfile import Customer  # noqa: F401  (the user)
from shapes import Stages


class Soak(Stages):
    stages = [(600, 3)]
