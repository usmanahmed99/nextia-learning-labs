"""Check the delivered dataset against its contract: the rules that Priya can
rely on in data/model/. Prints PASS or FAIL for each rule, writes
reports/validation.json, and exits with code 1 if any rule fails."""

import json
import sys
from pathlib import Path

import pandas as pd

MODEL = Path("data/model")
REPORT = Path("reports/validation.json")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
SPLITS = ["train", "valid", "test"]

# ---------------------------------------------------------------- the contract

# Every column, its type, and whether a value is required.
COLUMNS = {
    "ticket_id": ("text", True),
    "customer_id": ("text", False),            # guests have no customer
    "created_at": ("datetime", True),
    "channel": ("text", True),
    "team": ("text", True),
    "priority": ("integer", True),
    "segment": ("text", True),
    "region": ("text", True),
    "order_value": ("number", False),          # no order (account) or unknown
    "word_count": ("integer", True),
    "customer_tenure_days": ("number", False),  # guests and deleted customers
    "prior_tickets_90d": ("integer", True),
    "created_hour": ("integer", True),
    "escalated_72h": ("integer", True),        # the target
}
# Known only after the ticket is created: never in the dataset.
NEVER = ["priority_now", "first_reply_minutes", "closed_at"]
ALLOWED = {
    "channel": {"email", "chat", "phone", "web_form", "unknown"},
    "team": {"delivery", "returns", "payment", "warranty", "account"},
    "segment": {"home", "trade", "business", "guest", "unknown"},
    "region": {"north", "south", "east", "west", "unknown"},
}
RANGES = {  # inclusive; None means no limit
    "priority": (1, 3),
    "order_value": (0, 2000),
    "word_count": (0, 10_000),
    "customer_tenure_days": (0, None),
    "prior_tickets_90d": (0, None),
    "created_hour": (0, 23),
    # From the start of the selection to the snapshot minus 72 hours.
    "created_at": (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-06-28 06:00:00")),
}
ESCALATION_RATE = (0.05, 0.30)

# ---------------------------------------------------------------- helpers

results = []


def rule(name, problems):
    """Record one rule. An empty list of problems means the rule passes."""
    results.append({"rule": name, "passed": not problems, "problems": problems})
    print(f"{'PASS' if not problems else 'FAIL'}  {name}")
    for problem in problems:
        print(f"      {problem}")


def first(df, mask, column):
    """The first bad row, as an example: its ticket ID and its value."""
    row = df[mask].iloc[0]
    value = row[column]
    shown = repr(value) if isinstance(value, str) else value
    return f"first: {row['ticket_id']}, {shown}"


def n(count, word):
    """'1 row', '3 rows'."""
    return f"{count} {word}" + ("" if count == 1 else "s")


def load(path):
    """Read every value as text. Types are checked by the rules, not assumed."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def convert(text, kind):
    """Convert a text column to its type. A value that cannot be read becomes missing."""
    if kind == "text":
        return text
    if kind == "datetime":
        return pd.to_datetime(text, format=TIME_FORMAT, errors="coerce")
    numbers = pd.to_numeric(text, errors="coerce")
    if kind == "integer":
        numbers = numbers.where(numbers % 1 == 0)  # 2.5 is not an integer
    return numbers


# ---------------------------------------------------------------- the rules

def check_table(raw):
    """Rules for the modelling table, one row per ticket. Returns the typed table."""
    missing = [c for c in COLUMNS if c not in raw.columns]
    leaky = [c for c in raw.columns if c in NEVER]
    extra = [c for c in raw.columns if c not in COLUMNS and c not in NEVER]
    rule("required columns are present",
         [f"missing column: {c}" for c in missing])
    rule("no column that is known only after creation",
         [f"{c} must not be in the dataset" for c in leaky] + [f"unexpected column: {c}" for c in extra])
    if missing:
        return None

    df = raw.copy()
    problems = []
    for column, (kind, _) in COLUMNS.items():
        df[column] = convert(raw[column], kind)
        bad = raw[column].notna() & df[column].isna()
        if bad.any():
            problems.append(f"{column}: not a valid {kind} in {n(bad.sum(), 'row')} ({first(raw, bad, column)})")
    rule("every value has its column's type", problems)

    problems = []
    for column, (_, required) in COLUMNS.items():
        if required and raw[column].isna().any():
            problems.append(f"{column}: missing in {n(raw[column].isna().sum(), 'row')}")
    rule("no missing values in required columns", problems)

    repeated = df["ticket_id"].duplicated(keep=False)
    rule("ticket_id is unique",
         [f"{n(df.loc[repeated, 'ticket_id'].nunique(), 'ticket ID')} repeated "
          f"(first: {df.loc[repeated, 'ticket_id'].iloc[0]})"] if repeated.any() else [])

    problems = []
    for column, allowed in ALLOWED.items():
        bad = df[column].notna() & ~df[column].isin(allowed)
        if bad.any():
            values = sorted(df.loc[bad, column].unique())
            problems.append(f"{column}: values not allowed in {n(bad.sum(), 'row')}: {values}")
    rule("categories use allowed values only", problems)

    problems = []
    for column, (low, high) in RANGES.items():
        values = df[column]
        bad = pd.Series(False, index=df.index)
        if low is not None:
            bad |= values < low
        if high is not None:
            bad |= values > high
        if bad.any():
            problems.append(f"{column}: outside {low} to {high} in {n(bad.sum(), 'row')} ({first(df, bad, column)})")
    rule("numbers and dates are in their allowed ranges", problems)

    bad = ~df["escalated_72h"].isin([0, 1])
    rule("the target escalated_72h is 0 or 1",
         [f"not 0 or 1 in {n(bad.sum(), 'row')} ({first(df, bad, 'escalated_72h')})"] if bad.any() else [])
    return df


def rate_problem(name, target):
    """The escalation rate must be in the expected range, or something upstream changed."""
    low, high = ESCALATION_RATE
    rate = pd.to_numeric(target).mean()
    if not low <= rate <= high:
        return [f"{name}: escalation rate {rate:.1%} is outside {low:.0%} to {high:.0%}"]
    return []


def check_splits(table, parts):
    """Rules for train, valid and test."""
    empty = [name for name, part in parts.items() if len(part) == 0]
    rule("every split has rows", [f"{name} has no rows" for name in empty])
    if empty:
        return

    problems = []
    for name, part in parts.items():
        if list(part.columns) != list(table.columns):
            problems.append(f"{name}: the columns are not the same as in tickets_model.csv")
    together = pd.concat(parts.values())
    if len(together) != len(table):
        problems.append(f"the splits have {len(together)} rows together; tickets_model.csv has {len(table)}")
    if set(together["ticket_id"]) != set(table["ticket_id"]):
        problems.append("the splits do not contain the same tickets as tickets_model.csv")
    rule("together, the splits are exactly the modelling table", problems)

    problems = []
    for i, a in enumerate(SPLITS):
        for b in SPLITS[i + 1:]:
            shared = set(parts[a]["ticket_id"]) & set(parts[b]["ticket_id"])
            if shared:
                problems.append(f"{a} and {b} share {n(len(shared), 'ticket ID')} (first: {sorted(shared)[0]})")
    rule("no ticket is in two splits", problems)

    problems = []
    for a, b in zip(SPLITS, SPLITS[1:]):
        last = pd.to_datetime(parts[a]["created_at"], format=TIME_FORMAT).max()
        start = pd.to_datetime(parts[b]["created_at"], format=TIME_FORMAT).min()
        if not last < start:
            problems.append(f"{a} ends at {last}, which is not before the start of {b} at {start}")
    rule("the splits are in time order: train, then valid, then test", problems)

    problems = rate_problem("all rows", table["escalated_72h"])
    for name, part in parts.items():
        problems += rate_problem(name, part["escalated_72h"])
    rule(f"escalation rate between {ESCALATION_RATE[0]:.0%} and {ESCALATION_RATE[1]:.0%}", problems)


def main():
    files = ["tickets_model.csv"] + [f"{name}.csv" for name in SPLITS]
    missing = [f for f in files if not (MODEL / f).exists()]
    if missing:
        print(f"FAIL  missing file(s) in {MODEL}: {', '.join(missing)}")
        print("Run build_features.py and split.py first.")
        sys.exit(1)

    print(f"Checking {MODEL} against the contract")
    table = check_table(load(MODEL / "tickets_model.csv"))
    if table is not None:
        check_splits(table, {name: load(MODEL / f"{name}.csv") for name in SPLITS})

    failed = [r for r in results if not r["passed"]]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps({"files": files, "passed": not failed, "rules": results}, indent=2) + "\n",
                      encoding="utf-8")
    if failed:
        print(f"{len(failed)} of {len(results)} rules failed. Fix the step that made the data, then run it again.")
        sys.exit(1)
    print(f"All {len(results)} rules passed.")


if __name__ == "__main__":
    main()
