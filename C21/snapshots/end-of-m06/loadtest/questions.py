"""The question workload: customers and staff ask the help desk's common questions.

    locust -f loadtest/questions.py --host http://127.0.0.1:8000 --headless -u 8 -r 8 -t 60s

Most people ask a few common questions, so the mix is skewed on purpose: question k is
asked with weight 1/k (a Zipf-like mix). 9 of 10 askers are customers (each with their own
X-Customer-ID, one of the 40 practice customers); 1 of 10 is staff. The hit rate that you
measure depends on this mix: write it down with the result.
"""

import os
import random

from locust import task
from locust.contrib.fasthttp import FastHttpUser

QUESTIONS = [
    "Where is my parcel and how do I track it?",
    "How do I return a damaged item?",
    "When will I get my refund?",
    "How do I reset my password?",
    "Can I change or cancel my order?",
    "How does the warranty work?",
    "Do you deliver large items like sheds?",
    "How do gift cards work?",
    "What are your opening hours?",
    "How do I change my email address?",
    "Is my garden furniture covered if it breaks?",
    "How do I use a discount code?",
]
WEIGHTS = [1 / (k + 1) for k in range(len(QUESTIONS))]
CUSTOMERS = [f"C-{n:04d}" for n in range(1, 41)]
HEADERS = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
_rng = random.Random(21)


class Asker(FastHttpUser):
    @task
    def ask(self):
        question = _rng.choices(QUESTIONS, weights=WEIGHTS)[0]
        headers = dict(HEADERS)
        if _rng.random() < 0.9:
            headers["X-Customer-ID"] = _rng.choice(CUSTOMERS)
        self.client.post(
            "/v1/answers", json={"question": question}, headers=headers, name="POST /v1/answers"
        )
