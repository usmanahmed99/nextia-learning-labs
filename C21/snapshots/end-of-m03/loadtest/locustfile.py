"""The workload: customers send new tickets (Locust, https://locust.io, MIT licence).

Run it only against your own API on your computer:

    locust -f loadtest/locustfile.py --host http://127.0.0.1:8000 --headless -u 4 -r 4 -t 60s

-u is the number of simulated customers (users) that send at the same time, -r how many
start per second, -t how long the test runs. Without --headless, Locust opens a web page
on http://127.0.0.1:8089 with live charts.

Each user sends a ticket, waits for the answer, and sends the next one at once (no pause),
so -u is also the number of requests in flight. The tickets are the practice data's
subjects and bodies, picked at random with a fixed seed, so every run sends the same mix.

Set SAMPLES_CSV=<file> to write one line per request (start time, name, status, ms): the
measurement scripts compute exact percentiles from it.
"""

import csv
import os
import random
import time
from pathlib import Path

from locust import events, task
from locust.contrib.fasthttp import FastHttpUser

DATA = Path(__file__).resolve().parent.parent / "data" / "small" / "tickets.csv"
TICKETS = [
    (r["customer_id"], r["subject"], r["body"])
    for r in csv.DictReader(open(DATA, encoding="utf-8"))
]
HEADERS = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
_rng = random.Random(21)
_samples = None


@events.test_start.add_listener
def open_samples(environment, **kwargs):
    global _samples
    path = os.environ.get("SAMPLES_CSV")
    if path:
        _samples = open(path, "w", encoding="utf-8", newline="")
        _samples.write("start,name,status,ms\n")


@events.request.add_listener
def record(request_type, name, response_time, response, exception, start_time=None, **kwargs):
    if _samples is not None:
        status = getattr(response, "status_code", 0) or 0
        _samples.write(f"{start_time or time.time():.3f},{name},{status},{response_time:.1f}\n")


@events.test_stop.add_listener
def close_samples(environment, **kwargs):
    if _samples is not None:
        _samples.flush()


class Customer(FastHttpUser):
    """Sends a new ticket, waits for the answer, then sends the next one."""

    @task
    def new_ticket(self):
        customer, subject, body = _rng.choice(TICKETS)
        payload = {"customer_id": customer, "subject": subject, "body": body}
        with self.client.post(
            "/v1/tickets",
            json=payload,
            headers=HEADERS,
            name="POST /v1/tickets",
            catch_response=True,
        ) as r:
            if r.status_code in (201, 202):
                r.success()
            else:
                r.failure(f"{r.status_code}")
