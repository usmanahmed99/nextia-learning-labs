"""Build the modelling table: one row per ticket, with only the facts known
when the ticket is created, and the target, escalated_72h."""

import json
from pathlib import Path

import pandas as pd

IN = Path("data/clean")
OUT = Path("data/model")
SNAPSHOT = pd.Timestamp("2026-07-01 06:00:00")  # from data/extract/manifest.json
WINDOW = pd.Timedelta(hours=72)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Columns filled in after the ticket is created. They describe the future of
# the ticket, so they must not be features.
AFTER_CREATION = ["priority_now", "first_reply_minutes", "closed_at"]
FEATURES = ["channel", "team", "priority", "segment", "region", "order_value", "word_count",
            "customer_tenure_days", "prior_tickets_90d", "created_hour"]


def main():
    tickets = pd.read_csv(IN / "tickets.csv", parse_dates=["created_at", "joined_on"],
                          dtype={"customer_id": "string"}, keep_default_na=False, na_values=[""])
    outcomes = pd.read_csv(IN / "outcomes.csv", parse_dates=["recorded_at"])

    # Target: an escalation within 72 hours of creation.
    first_escalation = outcomes[outcomes["status"] == "escalated"].groupby("ticket_id")["recorded_at"].min()
    tickets["escalated_at"] = tickets["ticket_id"].map(first_escalation)
    tickets["escalated_72h"] = (tickets["escalated_at"] <= tickets["created_at"] + WINDOW).astype(int)

    # A ticket's 72 hours must be over before the snapshot, or its label is
    # not final yet.
    eligible = tickets["created_at"] <= SNAPSHOT - WINDOW
    counts = {"clean_tickets": len(tickets), "too_recent_for_label": int((~eligible).sum())}
    df = tickets[eligible].copy()

    # Features known at creation time.
    df["customer_tenure_days"] = (df["created_at"] - df["joined_on"]).dt.days
    df["created_hour"] = df["created_at"].dt.hour
    df = df.sort_values(["created_at", "ticket_id"])
    df["prior_tickets_90d"] = prior_count(df, tickets)

    columns = ["ticket_id", "customer_id", "created_at"] + FEATURES + ["escalated_72h"]
    df = df[columns]
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "tickets_model.csv", index=False, date_format=TIME_FORMAT)
    counts.update({"rows": len(df), "escalated": int(df["escalated_72h"].sum()),
                   "escalated_rate": round(df["escalated_72h"].mean(), 3)})
    (OUT / "build_summary.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))


def prior_count(df, all_tickets):
    """For each ticket: how many tickets the same customer created in the 90
    days before it. Only earlier tickets count, so the value is known at
    creation time. Guests have no history: 0."""
    history = all_tickets.dropna(subset=["customer_id"]).groupby("customer_id")["created_at"].apply(sorted)
    result = []
    for customer, created in zip(df["customer_id"], df["created_at"]):
        if pd.isna(customer):
            result.append(0)
            continue
        earlier = [t for t in history[customer] if created - pd.Timedelta(days=90) <= t < created]
        result.append(len(earlier))
    return result


if __name__ == "__main__":
    main()
