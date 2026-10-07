"""Score new tickets with the saved escalation model.

Nextia Learning, C05, Module 8 (Package artifacts; Plan production checks).

    python predict.py data/july_tickets.csv predictions.csv
    python predict.py --check     reload the model and compare the fixed sample

Checks the input before it scores: the required columns, numbers that are
numbers, values in their allowed range, and categories that the model knows.
A missing column or a wrong type stops the run (exit code 1). An unknown
category is allowed (the model treats it as "none of the known ones") but is
counted and reported, because many of them mean that the input has changed.
"""

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ticket_model import FEATURES, read

MODEL = Path("model")
RANGES = {"priority": (1, 3), "word_count": (0, 10000), "order_value": (0, 5000), "customer_tenure_days": (0, 20000),
          "prior_tickets_90d": (0, 500), "created_hour": (0, 23), "prior_escalations_90d": (0, 500)}


def load_model():
    info = json.loads((MODEL / "model_info.json").read_text(encoding="utf-8"))
    return joblib.load(MODEL / "escalation_model.joblib"), info


def check_input(df, info):
    """Return a list of problems that stop the run, and a list of warnings."""
    errors, warnings = [], []
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        return [f"missing columns: {', '.join(missing)}"], warnings
    for name in info["features"]["numbers"]:
        values = pd.to_numeric(df[name], errors="coerce")
        bad = values.isna() & df[name].notna()
        if bad.any():
            errors.append(f"{name}: {bad.sum()} values are not numbers, for example {df.loc[bad, name].iloc[0]!r}")
            continue
        low, high = RANGES[name]
        outside = values.notna() & ((values < low) | (values > high))
        if outside.any():
            errors.append(f"{name}: {outside.sum()} values outside {low} to {high}")
    for name, known in info["features"]["categories"].items():
        unknown = df[name].notna() & ~df[name].isin(known)
        if unknown.any():
            values = ", ".join(sorted(df.loc[unknown, name].astype(str).unique())[:5])
            warnings.append(f"{name}: {unknown.sum()} rows have a category the model never saw ({values})")
    return errors, warnings


def check_sample(pipeline):
    sample = read(MODEL / "check_sample.csv")
    scores = pipeline.predict_proba(sample[FEATURES])[:, 1]
    largest = float(np.abs(scores - sample["score"]).max())
    if largest > 1e-9:
        sys.exit(f"Check failed: the reloaded model's scores differ from the saved ones by up to {largest:.2e}.")
    print(f"Check passed: {len(sample)} scores are identical after reloading (largest difference {largest:.1e}).")


def main():
    parser = argparse.ArgumentParser(description="Score new tickets with the saved escalation model.")
    parser.add_argument("input", nargs="?", help="CSV file with one row per new ticket")
    parser.add_argument("output", nargs="?", default="predictions.csv")
    parser.add_argument("--check", action="store_true", help="compare the fixed sample after reloading")
    args = parser.parse_args()
    pipeline, info = load_model()
    if args.check:
        check_sample(pipeline)
        return
    if not args.input:
        parser.error("give an input CSV file, or --check")

    df = read(args.input)
    errors, warnings = check_input(df, info)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        for error in errors:
            print(f"Error: {error}")
        sys.exit("Stopped: the input does not match the model's feature schema. Nothing was scored.")

    scores = pipeline.predict_proba(df[FEATURES])[:, 1]
    out = pd.DataFrame({"ticket_id": df["ticket_id"], "score": scores.round(4),
                        "flag": (scores >= info["threshold"]).astype(int)})
    out.to_csv(args.output, index=False)
    print(f"Scored {len(out)} tickets with threshold {info['threshold']}: {out['flag'].sum()} flagged "
          f"({out['flag'].mean():.1%}). Wrote {args.output}.")


if __name__ == "__main__":
    main()
