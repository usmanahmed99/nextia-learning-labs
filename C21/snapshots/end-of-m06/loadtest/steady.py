"""Steady: 4 users for 60 s (after 10 s of warm-up). The baseline to compare against."""

from locustfile import Customer  # noqa: F401  (the user)
from shapes import Stages


class Steady(Stages):
    stages = [(70, 4)]
