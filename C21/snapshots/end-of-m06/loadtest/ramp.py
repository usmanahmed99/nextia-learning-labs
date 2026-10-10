"""Ramp-up: 2, 4, 8, 12, 16 users, 20 s each. Where does p95 start to grow?"""

from locustfile import Customer  # noqa: F401  (the user)
from shapes import Stages


class Ramp(Stages):
    stages = [(20, 2), (40, 4), (60, 8), (80, 12), (100, 16)]
