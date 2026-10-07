"""Clean the extracted tickets and outcomes. Every input row ends in exactly
one place: the clean table, the quarantine table, or the count of removed
exact duplicates. The original values stay next to the corrected ones."""

import json
from pathlib import Path

import pandas as pd

IN = Path("data/extract")
OUT = Path("data/clean")
REPORTS = Path("reports")

TICKET_TYPES = {
    "ticket_id": "string", "customer_id": "string", "channel": "string", "team": "string",
    "priority": "Int64", "order_value": "Float64", "word_count": "Int64",
    "first_reply_minutes": "Int64", "priority_now": "Int64",
    "segment": "string", "region": "string",
}
CHANNELS = {"email", "chat", "phone", "web_form"}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
WEB_FORM_FIXED = pd.Timestamp("2026-02-01")  # the web form sent cents before this day
MAX_WORDS = 10_000


def load_tickets():
    df = pd.read_csv(IN / "tickets.csv", dtype=TICKET_TYPES, keep_default_na=False, na_values=[""])
    df["created_at"] = pd.to_datetime(df["created_at"], format=TIME_FORMAT)
    df["closed_at"] = pd.to_datetime(df["closed_at"], format=TIME_FORMAT)
    df["joined_on"] = pd.to_datetime(df["joined_on"], format="%Y-%m-%d")
    return df


def clean_tickets(raw):
    counts = {"input_rows": len(raw)}
    df = raw.drop_duplicates()
    counts["exact_duplicates_removed"] = len(raw) - len(df)
    assert df["ticket_id"].is_unique, "a ticket ID appears twice with different values"

    # Channel: one spelling per value. A missing channel stays missing, and
    # becomes its own category, "unknown", so the model can still use the row.
    df["channel_raw"] = df["channel"]
    channel = df["channel"].str.strip().str.lower().replace({"webform": "web_form"})
    counts["channel_respelled"] = int((channel != df["channel"]).fillna(False).sum())
    df["channel"] = channel.fillna("unknown")
    assert set(df["channel"]) <= CHANNELS | {"unknown"}

    # Segment and region: the customer table spells "Trade" in two ways.
    # Guests have no customer; deleted customers have an ID but no row.
    df["segment"] = df["segment"].str.strip().str.lower()
    no_customer = df["customer_id"].isna()
    df.loc[no_customer, "segment"] = "guest"
    df["segment"] = df["segment"].fillna("unknown")
    df["region"] = df["region"].fillna("unknown")

    # Order value: keep the original, then correct or blank it, with a flag.
    df["order_value_raw"] = df["order_value"]
    df["order_value_flag"] = "ok"
    df.loc[df["team"] == "account", "order_value_flag"] = "not_applicable"
    unknown = df["order_value"] == -1
    df.loc[unknown, "order_value"] = pd.NA
    df.loc[unknown, "order_value_flag"] = "unknown"
    cents = (df["channel"] == "web_form") & (df["created_at"] < WEB_FORM_FIXED) & df["order_value"].notna()
    df.loc[cents, "order_value"] = (df.loc[cents, "order_value"] / 100).round(2)
    df.loc[cents, "order_value_flag"] = "converted_from_cents"
    counts.update({f"order_value_{k}": int(v) for k, v in df["order_value_flag"].value_counts().items()})

    # Rows we cannot correct with confidence go to quarantine, with a reason.
    df["reject_reason"] = pd.NA
    df.loc[df["created_at"] < df["joined_on"], "reject_reason"] = "created_before_customer_joined"
    df.loc[df["word_count"] > MAX_WORDS, "reject_reason"] = "word_count_above_10000"
    quarantine = df[df["reject_reason"].notna()]
    clean = df[df["reject_reason"].isna()].drop(columns="reject_reason")
    counts["quarantined"] = len(quarantine)
    counts["clean_rows"] = len(clean)
    assert counts["clean_rows"] + counts["quarantined"] + counts["exact_duplicates_removed"] == counts["input_rows"]
    return clean, quarantine, counts


def clean_outcomes(tickets):
    df = pd.read_csv(IN / "outcomes.csv", dtype={"csat": "Int64"}, keep_default_na=False, na_values=[""])
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], format=TIME_FORMAT)
    counts = {"input_rows": len(df)}
    # A retry logged some events twice: same ticket, time and status, new ID.
    # Keep the first one logged.
    df = df.sort_values("outcome_id").drop_duplicates(["ticket_id", "recorded_at", "status"], keep="first")
    counts["repeated_events_removed"] = counts["input_rows"] - len(df)
    df = df[df["ticket_id"].isin(tickets["ticket_id"])]
    counts["events_of_quarantined_tickets"] = counts["input_rows"] - counts["repeated_events_removed"] - len(df)
    counts["clean_rows"] = len(df)
    return df, counts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    tickets, quarantine, ticket_counts = clean_tickets(load_tickets())
    outcomes, outcome_counts = clean_outcomes(tickets)
    for df in (tickets, quarantine):
        df["joined_on"] = df["joined_on"].dt.strftime("%Y-%m-%d")
    tickets.to_csv(OUT / "tickets.csv", index=False, date_format=TIME_FORMAT)
    quarantine.to_csv(OUT / "quarantine.csv", index=False, date_format=TIME_FORMAT)
    outcomes.to_csv(OUT / "outcomes.csv", index=False, date_format=TIME_FORMAT)
    summary = {"tickets": ticket_counts, "outcomes": outcome_counts}
    (REPORTS / "cleaning.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
