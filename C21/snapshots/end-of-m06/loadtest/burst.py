"""Burst: 2 users, then 20 users for 15 s (ten times more), then 2 users again for 45 s.
What do users see during the burst, and how long until the queue is empty again?"""

from locustfile import Customer  # noqa: F401  (the user)
from shapes import Stages


class Burst(Stages):
    stages = [(20, 2), (35, 20), (80, 2)]
