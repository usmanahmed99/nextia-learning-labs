"""Generate the synthetic Larkfield help-desk data used in C05.

Nextia Learning, C05: Machine Learning: From Problem to Reliable Model.

Larkfield is a fictional online shop for home and garden products. In C04 you
prepared a sample export (240 customers, six months). C05 uses the full
export: about 1,000 customers over two years, from the same help desk, with
the same rules for escalation. The C04 preparation plan is already applied:
one row per ticket, only facts known at creation, the target escalated_72h,
and the same time split. The export problems of C04 (duplicates, cents,
spellings) are not added again, because C05 is about models, not cleaning.

The script writes, into data/:

    train.csv, valid.csv, test.csv   the modelling table, split by time
    split_manifest.json              the split rule and the counts
    extra_features.csv               more columns for C05-M03-L03 (some are traps)
    daily_tickets.csv                tickets created per day (a regression target)
    july_tickets.csv                 new tickets after the snapshot, no target (from
                                     15 July some come from a new channel, social)
    july_labels.csv                  their targets, which arrive later

Nothing here comes from a real system or a real person.

Run it with Python 3.12 or later and the standard library only:

    python generate.py

The seed is fixed, so the output is the same on every run. SHA256SUMS in
data/ lets you confirm that.
"""

import bisect
import csv
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SEED = 5010
OUT = Path(__file__).parent / "data"

START = datetime(2024, 7, 1)
END = datetime(2026, 7, 1)            # tickets are created before this day
SNAPSHOT = datetime(2026, 7, 1, 6)    # the moment of the export
POLICY_CHANGE = datetime(2026, 5, 1)  # new warranty policy: more escalations after it
VALID_FROM = datetime(2026, 5, 1)
TEST_FROM = datetime(2026, 6, 1)
WINDOW = timedelta(hours=72)
JULY_END = datetime(2026, 8, 1)
SOCIAL_FROM = datetime(2026, 7, 15)  # a new contact channel, after the snapshot

TEAMS = ["delivery", "returns", "payment", "warranty", "account"]
TEAM_WEIGHTS = [32, 24, 16, 14, 14]
CHANNELS = ["email", "chat", "phone", "web_form"]
CHANNEL_WEIGHTS = [40, 30, 15, 15]
REGIONS = ["north", "south", "east", "west"]
# Home and garden: more contacts in the garden season and before the holidays.
SEASON = {1: 0.85, 2: 0.85, 3: 1.0, 4: 1.3, 5: 1.45, 6: 1.4, 7: 1.25, 8: 1.0, 9: 0.9, 10: 0.9, 11: 1.1, 12: 1.2}

rng = random.Random(SEED)


def ts(moment):
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def random_moment(start, end):
    """A random moment between start and end: mostly in working hours, on
    weekdays, and more often in the busy months."""
    span = (end - start).total_seconds()
    while True:
        moment = start + timedelta(seconds=int(rng.random() * span))
        weekday_ok = moment.weekday() < 5 or rng.random() < 0.45
        hour_ok = 7 <= moment.hour < 22 or rng.random() < 0.08
        season_ok = rng.random() < SEASON[moment.month] / 1.45
        if weekday_ok and hour_ok and season_ok:
            return moment


# ---------------------------------------------------------------- customers

customers = []
for n in range(1, 1001):
    segment = rng.choices(["home", "trade", "business"], [72, 22, 6])[0]
    joined = datetime(2019, 3, 1) + timedelta(days=rng.randint(0, (datetime(2026, 6, 15) - datetime(2019, 3, 1)).days))
    customers.append({
        "customer_id": f"C-{n:05d}",
        "segment": segment,
        "region": rng.choice(REGIONS) if rng.random() > 0.04 else "unknown",
        "joined": joined,
        # Hidden: how likely this customer's tickets are to need escalation.
        "_effect": rng.gauss(0, 0.8),
        # Hidden: tickets per six months, as in C04.
        "_rate": {"home": 3.2, "trade": 12.0, "business": 18.0}[segment],
    })


def escalation_chance(t):
    """The same rule as C04's generator. The model never sees it."""
    score = -3.6
    score += {1: 1.9, 2: 0.7, 3: 0.0}[t["priority"]]
    score += {"payment": 0.8, "warranty": 0.6, "account": -0.6}.get(t["team"], 0.0)
    score += {"phone": 0.6, "chat": 0.1}.get(t["true_channel"], 0.0)
    score += {"business": 0.8, "trade": 0.35}.get(t["segment"], 0.0)
    score += 0.8 * (math.log(t["word_count"]) - math.log(90))
    if t["order_value"] is not None and t["order_value"] > 200:
        score += 0.5
    if t["created"] >= POLICY_CHANGE:
        score += 0.35 + (0.7 if t["team"] == "warranty" else 0.0)
    score += t["_effect"]
    return 1 / (1 + math.exp(-score))


def new_ticket(customer, created):
    """One ticket with the facts known at creation, and its future."""
    segment = customer["segment"] if customer else "home"
    t = {
        "created": created,
        "customer_id": customer["customer_id"] if customer else None,
        "segment": customer["segment"] if customer else "guest",
        "region": customer["region"] if customer else "unknown",
        "joined": customer["joined"] if customer else None,
        "_effect": customer["_effect"] if customer else rng.gauss(0, 0.8),
        "team": rng.choices(TEAMS, TEAM_WEIGHTS)[0],
        "true_channel": rng.choices(CHANNELS, CHANNEL_WEIGHTS)[0],
    }
    # About 1 in 40 tickets came through an old integration that does not
    # record the channel.
    t["channel"] = "unknown" if rng.random() < 0.025 else t["true_channel"]
    t["priority"] = rng.choices([1, 2, 3], [25, 35, 40] if t["team"] == "payment" else [12, 35, 53])[0]
    if t["team"] == "account":
        t["order_value"] = None  # account questions are not about an order
    else:
        base = 60 * (1.8 if segment != "home" else 1.0)
        t["order_value"] = round(min(max(rng.lognormvariate(math.log(base), 0.8), 4.5), 1450), 2)
    t["word_count"] = max(8, int(rng.lognormvariate(math.log(90), 0.6)))
    if rng.random() < 0.004:
        t["word_count"] = 0  # an attachment only
    escalated = rng.random() < escalation_chance({**t, "word_count": max(t["word_count"], 8)})
    if escalated:
        # Most escalations happen within hours; one in ten comes days later.
        delay = rng.expovariate(1 / 9) if rng.random() < 0.9 else rng.uniform(76, 220)
        t["escalated_at"] = created + timedelta(hours=delay, seconds=rng.randint(0, 3599))
    else:
        t["escalated_at"] = None
    # The order system cannot find about 1 in 100 orders: the value is unknown.
    if t["order_value"] is not None and rng.random() < 0.01:
        t["order_value"] = None
    return t


tickets = []
for c in customers:
    first = max(START, c["joined"])
    if first >= END:
        continue
    share = (END - first).days / (182.5)
    # Some customers never contact support in the period.
    count = 0 if rng.random() < 0.09 else max(0, round(rng.expovariate(1 / (c["_rate"] * share))))
    for _ in range(count):
        tickets.append(new_ticket(c, random_moment(first, END)))
# Guest checkouts: tickets without a customer account.
for _ in range(220):
    tickets.append(new_ticket(None, random_moment(START, END)))

tickets.sort(key=lambda t: t["created"])
for n, t in enumerate(tickets, start=1):
    t["ticket_id"] = f"T-{100000 + n}"

# ------------------------------------------------------- features and target

by_customer = defaultdict(list)       # created times, sorted
escalations = defaultdict(list)       # escalation times known by the snapshot
for t in tickets:
    if t["customer_id"]:
        by_customer[t["customer_id"]].append(t["created"])
        if t["escalated_at"] and t["escalated_at"] < SNAPSHOT:
            escalations[t["customer_id"]].append(t["escalated_at"])
for times in escalations.values():
    times.sort()


def count_between(times, start, end):
    return bisect.bisect_left(times, end) - bisect.bisect_left(times, start)


for t in tickets:
    created = t["created"]
    t["created_at"] = ts(created)
    t["escalated_72h"] = int(t["escalated_at"] is not None and t["escalated_at"] <= created + WINDOW)
    t["customer_tenure_days"] = (created - t["joined"]).days if t["joined"] else None
    t["created_hour"] = created.hour
    cid = t["customer_id"]
    t["prior_tickets_90d"] = count_between(by_customer[cid], created - timedelta(days=90), created) if cid else 0
    # Escalations of the same customer that were known before this ticket.
    t["prior_escalations_90d"] = count_between(escalations[cid], created - timedelta(days=90), created) if cid else 0
    t["priority_now"] = 1 if t["escalated_at"] and t["escalated_at"] < SNAPSHOT else t["priority"]
    t["order_value_band"] = ("none" if t["order_value"] is None else
                             "low" if t["order_value"] < 50 else "mid" if t["order_value"] < 200 else "high")

# A ticket's 72 hours must be over before the snapshot, or its target is not
# final yet.
labelled = [t for t in tickets if t["created"] <= SNAPSHOT - WINDOW]

# A trap for C05-M03-L03: each customer's escalation rate over ALL labelled
# rows, including later ones. It uses the target of the future.
totals = defaultdict(lambda: [0, 0])
for t in labelled:
    if t["customer_id"]:
        totals[t["customer_id"]][0] += t["escalated_72h"]
        totals[t["customer_id"]][1] += 1
for t in labelled:
    cid = t["customer_id"]
    t["customer_escalation_rate"] = round(totals[cid][0] / totals[cid][1], 4) if cid else None

# ------------------------------------------------------------------- write

OUT.mkdir(exist_ok=True)


def write(name, fields, records):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(fields)
        for r in records:
            writer.writerow(["" if r[k] is None else r[k] for k in fields])


FEATURES = ["channel", "team", "priority", "segment", "region", "order_value", "word_count",
            "customer_tenure_days", "prior_tickets_90d", "created_hour"]
MODEL_FIELDS = ["ticket_id", "customer_id", "created_at"] + FEATURES + ["escalated_72h"]

parts = {
    "train": [t for t in labelled if t["created"] < VALID_FROM],
    "valid": [t for t in labelled if VALID_FROM <= t["created"] < TEST_FROM],
    "test": [t for t in labelled if t["created"] >= TEST_FROM],
}
manifest = {
    "snapshot": ts(SNAPSHOT),
    "rule": "train < 2026-05-01 <= valid < 2026-06-01 <= test; only tickets created at or before 2026-06-28 06:00 (72 hours before the snapshot)",
    "parts": {},
}
for name, rows in parts.items():
    write(f"{name}.csv", MODEL_FIELDS, rows)
    positives = sum(t["escalated_72h"] for t in rows)
    manifest["parts"][name] = {
        "rows": len(rows), "escalated": positives, "escalated_rate": round(positives / len(rows), 3),
        "first_created": rows[0]["created_at"], "last_created": rows[-1]["created_at"],
    }
(OUT / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

write("extra_features.csv",
      ["ticket_id", "prior_escalations_90d", "order_value_band", "customer_escalation_rate", "priority_now"],
      labelled)

# Tickets created per day, for the regression lessons.
per_day = defaultdict(int)
for t in tickets:
    per_day[t["created"].date()] += 1
days = []
day = START.date()
while day < END.date():
    days.append({"date": day.isoformat(), "weekday": day.strftime("%a"), "is_weekend": int(day.weekday() >= 5),
                 "month": day.month, "tickets": per_day[day]})
    day += timedelta(days=1)
write("daily_tickets.csv", ["date", "weekday", "is_weekend", "month", "tickets"], days)

# July: new tickets that arrive after the snapshot. Their targets arrive
# later, in a separate file, as they would in real use.
july = []
active = [c for c in customers if c["joined"] < JULY_END]
weights = [c["_rate"] for c in active]
for _ in range(1400):
    customer = rng.choices(active, weights)[0] if rng.random() > 0.01 else None
    t = new_ticket(customer, random_moment(datetime(2026, 7, 1, 7), JULY_END))
    # On 15 July Larkfield starts answering on social media: a channel that
    # the model never saw. The rules for escalation do not change.
    if t["created"] >= SOCIAL_FROM and rng.random() < 0.15:
        t["channel"] = "social"
    july.append(t)
july.sort(key=lambda t: t["created"])
for n, t in enumerate(july, start=1):
    created = t["created"]
    t["ticket_id"] = f"T-{100000 + len(tickets) + n}"
    t["created_at"] = ts(created)
    t["escalated_72h"] = int(t["escalated_at"] is not None and t["escalated_at"] <= created + WINDOW)
    t["customer_tenure_days"] = (created - t["joined"]).days if t["joined"] else None
    t["created_hour"] = created.hour
    cid = t["customer_id"]
    t["prior_tickets_90d"] = count_between(by_customer[cid], created - timedelta(days=90), created) if cid else 0
# Escalations known before each July ticket: the history up to the snapshot,
# plus July escalations that happened before the ticket was created.
known = defaultdict(list, {cid: list(times) for cid, times in escalations.items()})
for t in july:
    if t["customer_id"] and t["escalated_at"]:
        bisect.insort(known[t["customer_id"]], t["escalated_at"])
for t in july:
    cid = t["customer_id"]
    t["prior_escalations_90d"] = count_between(known[cid], t["created"] - timedelta(days=90), t["created"]) if cid else 0
write("july_tickets.csv", ["ticket_id", "customer_id", "created_at"] + FEATURES + ["prior_escalations_90d"], july)
write("july_labels.csv", ["ticket_id", "escalated_72h"], july)

print(f"customers: {len(customers)}  tickets: {len(tickets)}  labelled: {len(labelled)}  july: {len(july)}")
for name, p in manifest["parts"].items():
    print(f"{name}: {p['rows']} rows, {p['escalated']} escalated ({p['escalated_rate']:.1%})")
