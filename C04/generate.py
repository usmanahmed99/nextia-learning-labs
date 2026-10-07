"""Generate the synthetic Larkfield help-desk export used in C04.

Nextia Learning, C04: SQL and Data Preparation for AI.

Larkfield is a fictional online shop for home and garden products. This
script writes three CSV files, as the shop's help-desk system would export
them on 2026-07-01 at 06:00:

    data/customers.csv   one row per customer
    data/tickets.csv     one row per support ticket (with export problems)
    data/outcomes.csv    one row per event in a ticket's life

and one later export with a changed schema, for Module 6:

    data/tickets-2026-08-01.csv

Nothing here comes from a real system or a real person. The problems in the
data (duplicates, missing values, mixed units, leaky columns) are added on
purpose, and each one is listed in data/dataset.md.

Run it with Python 3.12 or later and the standard library only:

    python generate.py

The seed is fixed, so the output is the same on every run. The checksums in
data/dataset.md let you confirm that.
"""

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 2026
OUT = Path(__file__).parent / "data"

START = datetime(2026, 1, 5)
END = datetime(2026, 7, 1)          # tickets are created before this day
SNAPSHOT = datetime(2026, 7, 1, 6)  # the moment of the export
POLICY_CHANGE = datetime(2026, 5, 1)  # new warranty policy: more escalations after it

TEAMS = ["delivery", "returns", "payment", "warranty", "account"]
TEAM_WEIGHTS = [32, 24, 16, 14, 14]
CHANNELS = ["email", "chat", "phone", "web_form"]
CHANNEL_WEIGHTS = [40, 30, 15, 15]
REGIONS = ["north", "south", "east", "west"]

rng = random.Random(SEED)


def ts(moment):
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def random_moment(start, end):
    """A random moment between start and end, mostly in working hours."""
    while True:
        seconds = rng.uniform(0, (end - start).total_seconds())
        moment = start + timedelta(seconds=int(seconds))
        weekday_ok = moment.weekday() < 5 or rng.random() < 0.45
        hour_ok = 7 <= moment.hour < 22 or rng.random() < 0.08
        if weekday_ok and hour_ok:
            return moment


# ---------------------------------------------------------------- customers

customers = []
for n in range(1, 241):
    segment = rng.choices(["home", "trade", "business"], [72, 22, 6])[0]
    joined = datetime(2019, 3, 1) + timedelta(days=rng.randint(0, (datetime(2026, 6, 15) - datetime(2019, 3, 1)).days))
    customers.append({
        "customer_id": f"C-{n:04d}",
        "segment": segment,
        "region": rng.choice(REGIONS),
        "joined_on": joined.strftime("%Y-%m-%d"),
        # Hidden: how likely this customer's tickets are to need escalation.
        "_effect": rng.gauss(0, 0.8),
        "_rate": {"home": 3.2, "trade": 12.0, "business": 18.0}[segment],
    })

# ------------------------------------------------------------------ tickets

tickets = []
for c in customers:
    joined = datetime.strptime(c["joined_on"], "%Y-%m-%d")
    first = max(START, joined)
    if first >= END:
        continue
    share = (END - first).days / (END - START).days
    # Some customers never contact support in the period.
    count = 0 if rng.random() < 0.09 else max(0, round(rng.expovariate(1 / (c["_rate"] * share))))
    for _ in range(count):
        tickets.append({"_customer": c, "_created": random_moment(first, END)})

tickets.sort(key=lambda t: t["_created"])


def escalation_chance(t):
    c = t["_customer"]
    score = -3.6
    score += {1: 1.9, 2: 0.7, 3: 0.0}[t["priority"]]
    score += {"payment": 0.8, "warranty": 0.6, "account": -0.6}.get(t["team"], 0.0)
    score += {"phone": 0.6, "chat": 0.1}.get(t["channel"], 0.0)
    score += {"business": 0.8, "trade": 0.35}.get(c["segment"], 0.0)
    score += 0.8 * (math.log(t["word_count"]) - math.log(90))
    if t["order_value"] is not None and t["order_value"] > 200:
        score += 0.5
    if t["_created"] >= POLICY_CHANGE:
        score += 0.35 + (0.7 if t["team"] == "warranty" else 0.0)
    score += c["_effect"]
    return 1 / (1 + math.exp(-score))


outcomes = []
for n, t in enumerate(tickets, start=1):
    c = t["_customer"]
    created = t["_created"]
    t["ticket_id"] = f"T-{10000 + n}"
    t["customer_id"] = c["customer_id"]
    t["team"] = rng.choices(TEAMS, TEAM_WEIGHTS)[0]
    t["channel"] = rng.choices(CHANNELS, CHANNEL_WEIGHTS)[0]
    t["priority"] = rng.choices([1, 2, 3], [25, 35, 40] if t["team"] == "payment" else [12, 35, 53])[0]
    if t["team"] == "account":
        t["order_value"] = None  # account questions are not about an order
    else:
        base = 60 * (1.8 if c["segment"] != "home" else 1.0)
        t["order_value"] = round(min(max(rng.lognormvariate(math.log(base), 0.8), 4.5), 1450), 2)
    t["word_count"] = max(8, int(rng.lognormvariate(math.log(90), 0.6)))

    escalated = rng.random() < escalation_chance(t)
    events = []
    reply = created + timedelta(minutes=max(2, int(rng.expovariate(1 / (25 if escalated else 140)))))
    if escalated:
        # Most escalations happen within hours; one in ten comes days later.
        delay = rng.expovariate(1 / 9) if rng.random() < 0.9 else rng.uniform(76, 220)
        escalated_at = created + timedelta(hours=delay, seconds=rng.randint(0, 3599))
        events.append(("escalated", escalated_at))
        resolved_at = escalated_at + timedelta(hours=rng.gammavariate(2.0, 20))
    else:
        resolved_at = created + timedelta(hours=rng.gammavariate(1.6, 18))
    events.append(("resolved", resolved_at))
    if rng.random() < 0.08:
        reopened_at = resolved_at + timedelta(hours=rng.uniform(20, 120))
        events.append(("reopened", reopened_at))
        # Some reopened tickets are answered at once: the agent reopens and
        # resolves them in the same second. Both events have the same time,
        # and only the logging order (the outcome ID) says which came last.
        quick = rng.random() < 0.12
        events.append(("resolved", reopened_at if quick else reopened_at + timedelta(hours=rng.gammavariate(1.5, 15))))

    # The export holds only what happened before the snapshot.
    events = [(status, at) for status, at in events if at < SNAPSHOT]
    t["_events"] = events
    t["_escalated_by_snapshot"] = any(s == "escalated" for s, _ in events)
    t["first_reply_minutes"] = int((reply - created).total_seconds() // 60) if reply < SNAPSHOT else None
    t["priority_now"] = 1 if t["_escalated_by_snapshot"] else t["priority"]
    final = events[-1][0] if events else None
    t["closed_at"] = ts(events[-1][1]) if final == "resolved" else None
    t["created_at"] = ts(created)

    for status, at in events:
        code = csat = None
        if status == "resolved":
            code = rng.choices(["refund", "replacement", "information", "no_action"], [25, 20, 40, 15])[0]
            if rng.random() < 0.6:
                mean = 3.2 if t["_escalated_by_snapshot"] else 4.1
                csat = min(5, max(1, round(rng.gauss(mean, 0.9))))
        outcomes.append({"ticket_id": t["ticket_id"], "recorded_at": ts(at), "status": status,
                         "resolution_code": code, "csat": csat})

# ------------------------------------------------------ problems, on purpose
#
# Each block adds one kind of problem. data/dataset.md lists them with counts.

# Customers: missing regions and inconsistent segment spelling.
for c in rng.sample(customers, 9):
    c["region"] = None
for c in rng.sample([c for c in customers if c["segment"] == "trade"], 3):
    c["segment"] = "Trade"

# Old web form (before February) sent order values in cents, not dollars.
for t in tickets:
    if t["channel"] == "web_form" and t["_created"] < datetime(2026, 2, 1) and t["order_value"] is not None:
        t["order_value"] = round(t["order_value"] * 100, 2)

# -1 means "unknown" in the order system.
for t in rng.sample([t for t in tickets if t["order_value"] is not None], 11):
    t["order_value"] = -1

# Empty messages (an attachment only) and one pasted log file.
for t in rng.sample(tickets, 6):
    t["word_count"] = 0
rng.choice(tickets)["word_count"] = 48210

# Channel spellings from different help-desk versions, and missing channels.
spellings = [("email", "Email", 21), ("email", "EMAIL", 6), ("chat", " chat", 8), ("web_form", "webform", 5)]
for real, wrong, k in spellings:
    for t in rng.sample([t for t in tickets if t["channel"] == real], k):
        t["channel"] = wrong
for t in rng.sample(tickets, 38):
    t["channel"] = None

# Guest tickets (no customer) and tickets from deleted customer accounts.
for t in rng.sample(tickets, 12):
    t["customer_id"] = None
deleted = ["C-0241", "C-0242", "C-0243", "C-0244"]
for i, t in enumerate(rng.sample([t for t in tickets if t["customer_id"]], 9)):
    t["customer_id"] = deleted[i % len(deleted)]

# Tickets created before the customer joined (a data entry error).
by_id = {c["customer_id"]: c for c in customers}
late_joiners = [t for t in tickets if t["customer_id"] in by_id
                and datetime.strptime(by_id[t["customer_id"]]["joined_on"], "%Y-%m-%d") > START + timedelta(days=60)]
for t in rng.sample(late_joiners, 3):
    joined = datetime.strptime(by_id[t["customer_id"]]["joined_on"], "%Y-%m-%d")
    t["created_at"] = ts(joined - timedelta(days=rng.randint(3, 20), hours=rng.randint(0, 8)))

# A typed year: 2036 instead of 2026.
typo = rng.choice(tickets)
typo["created_at"] = "2036" + typo["created_at"][4:]

# Outcomes: events logged twice by a retry (same ticket, time and status),
# and events for tickets that were deleted from the ticket table.
for o in rng.sample(outcomes, 30):
    outcomes.append(dict(o))
for k, at in enumerate(["2026-02-11 10:14:09", "2026-03-02 16:40:51", "2026-04-20 09:03:30", "2026-06-02 13:27:44"]):
    outcomes.append({"ticket_id": f"T-{9990 + k}", "recorded_at": at, "status": "resolved",
                     "resolution_code": "no_action", "csat": None})
outcomes.sort(key=lambda o: (o["recorded_at"], o["ticket_id"]))
for n, o in enumerate(outcomes, start=1):
    o["outcome_id"] = f"O-{n:05d}"

# Tickets: the export repeated some rows at a page boundary.
rows = list(tickets)
for t in rng.sample(tickets, 14):
    rows.insert(rows.index(t) + 1, t)

# ------------------------------------------------------------------- write

OUT.mkdir(exist_ok=True)


def write(name, fields, records):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(fields)
        for r in records:
            writer.writerow(["" if r[k] is None else r[k] for k in fields])


write("customers.csv", ["customer_id", "segment", "region", "joined_on"], customers)
ticket_fields = ["ticket_id", "customer_id", "created_at", "channel", "team", "priority", "order_value",
                 "word_count", "first_reply_minutes", "priority_now", "closed_at"]
write("tickets.csv", ticket_fields, rows)
write("outcomes.csv", ["outcome_id", "ticket_id", "recorded_at", "status", "resolution_code", "csat"], outcomes)

# Module 6: the next month's export, after a help-desk update. The update
# renamed `channel` to `contact_channel` and writes order values with a
# currency sign. The rows are the July tickets, which are new.
july = []
for n in range(1, 41):
    created = random_moment(datetime(2026, 7, 1, 7), datetime(2026, 8, 1))
    team = rng.choices(TEAMS, TEAM_WEIGHTS)[0]
    value = None if team == "account" else round(rng.lognormvariate(math.log(60), 0.8), 2)
    july.append({
        "ticket_id": f"T-{12000 + n}", "customer_id": rng.choice(customers)["customer_id"],
        "created_at": created, "contact_channel": rng.choices(CHANNELS, CHANNEL_WEIGHTS)[0], "team": team,
        "priority": rng.choices([1, 2, 3], [12, 35, 53])[0],
        "order_value": None if value is None else f"${value:.2f}",
        "word_count": max(8, int(rng.lognormvariate(math.log(90), 0.6))),
        "first_reply_minutes": None, "priority_now": None, "closed_at": None,
    })
july.sort(key=lambda t: t["created_at"])
for t in july:
    t["created_at"] = ts(t["created_at"])
    t["priority_now"] = t["priority"]
write("tickets-2026-08-01.csv", [f if f != "channel" else "contact_channel" for f in ticket_fields], july)

print(f"customers: {len(customers)}  tickets: {len(rows)} rows ({len(tickets)} tickets)  outcomes: {len(outcomes)}")
