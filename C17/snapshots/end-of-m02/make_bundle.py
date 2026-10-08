"""Make a model bundle from the C05 project's model/ folder.

    python make_bundle.py ../ticket-model --version 1.0.0

Reads ../ticket-model/model/ (escalation_model.joblib, model_info.json) and
../ticket-model/data/ (for the parity cases), and writes
bundles/escalation-<version>/ with the model, its contract, its metadata, the
parity cases and SHA256SUMS. It prints the bundle digest: give it to the
service as MODEL_SHA256.

Run it only on a model that you trained yourself, or that comes from a source
you trust: it loads the joblib file, and loading can run code.
"""

import argparse
import json
import shutil
import sys
from importlib.metadata import version
from pathlib import Path

import joblib
import pandas as pd

from escalation.bundle import FILES, PACKAGES, bundle_digest, sha256
from escalation.contract import FEATURES, TicketFeatures

# Fixed tickets that every copy of the model must score the same way.
# Normal: real validation tickets. Missing: the two numbers that may be null.
# Extreme: values at the edges of the contract. Unknown: a category the
# model never saw.
EDGE_CASES = [
    ("missing", "T-900001", dict(team="account", order_value=None)),
    ("missing", "T-900002", dict(segment="guest", customer_tenure_days=None, prior_tickets_90d=0, prior_escalations_90d=0)),
    ("missing", "T-900003", dict(order_value=None, customer_tenure_days=None)),
    ("extreme", "T-900004", dict(priority=1, order_value=5000, word_count=10000, prior_tickets_90d=500, prior_escalations_90d=500, created_hour=23)),
    ("extreme", "T-900005", dict(priority=3, order_value=0, word_count=0, customer_tenure_days=0, prior_tickets_90d=0, prior_escalations_90d=0, created_hour=0)),
    ("extreme", "T-900006", dict(customer_tenure_days=20000, created_hour=0)),
    ("unknown", "T-900007", dict(channel="social")),
    ("unknown", "T-900008", dict(region="overseas", team="installation")),
]
BASE = dict(channel="email", team="payment", segment="home", region="west", priority=2, order_value=120.0,
            word_count=80, customer_tenure_days=500, prior_tickets_90d=1, created_hour=11, prior_escalations_90d=0)


def read(path):
    """Read a ticket CSV the way C05 does: only an empty cell is missing."""
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def parity_cases(data: Path) -> pd.DataFrame:
    valid = read(data / "valid.csv")
    extra = read(data / "extra_features.csv")[["ticket_id", "prior_escalations_90d"]]
    valid = valid.merge(extra, on="ticket_id", how="left", validate="one_to_one")
    normal = valid.dropna(subset=["order_value", "customer_tenure_days"]).head(6)
    rows = [{"case": "normal", "ticket_id": r.ticket_id, **{f: getattr(r, f) for f in FEATURES}}
            for r in normal.itertuples()]
    rows += [{"case": case, "ticket_id": tid, **{**BASE, **change}} for case, tid, change in EDGE_CASES]
    cases = pd.DataFrame(rows, columns=["case", "ticket_id"] + FEATURES)
    for name in ["priority", "word_count", "customer_tenure_days", "prior_tickets_90d", "created_hour",
                 "prior_escalations_90d"]:
        cases[name] = cases[name].astype("Int64")  # whole numbers, with an empty cell when missing
    for row in cases[FEATURES].to_dict("records"):  # every case must pass the contract
        TicketFeatures(**{k: (None if pd.isna(v) else v) for k, v in row.items()})
    return cases


def main():
    parser = argparse.ArgumentParser(description="Make a model bundle from a C05 project.")
    parser.add_argument("project", type=Path, help="the C05 ticket-model folder")
    parser.add_argument("--version", required=True, help="the model version, for example 1.0.0")
    parser.add_argument("--model-dir", default="model", help="the folder in the project with the model")
    args = parser.parse_args()

    source = args.project / args.model_dir
    info = json.loads((source / "model_info.json").read_text(encoding="utf-8"))
    pipeline = joblib.load(source / "escalation_model.joblib")
    if list(pipeline.feature_names_in_) != FEATURES:
        sys.exit("Stopped: the model was trained on other features than this service expects.")

    out = Path("bundles") / f"escalation-{args.version}"
    if out.exists():
        sys.exit(f"Stopped: {out} exists. A version is never changed: choose a new version.")
    out.mkdir(parents=True)

    shutil.copyfile(source / "escalation_model.joblib", out / "model.joblib")

    cases = parity_cases(args.project / "data")
    cases["expected_score"] = pipeline.predict_proba(cases[FEATURES])[:, 1]
    cases.to_csv(out / "parity_cases.csv", index=False)

    contract = {
        "model": "escalation",
        "model_version": args.version,
        "unit": "one support ticket, scored when it is created",
        "features": FEATURES,
        "schema": TicketFeatures.model_json_schema(),
        "known_categories": info["features"]["categories"],
        "missing_values": {
            "order_value": "null when the ticket has no order; the pipeline fills the training median",
            "customer_tenure_days": "null for a guest; the pipeline fills the training median",
            "other features": "never null: the request is rejected",
        },
        "unknown_categories": "allowed; scored as none of the known values; reported as a warning",
        "output": {
            "score": "0 to 1; a higher score means a higher risk of escalation; it ranks tickets",
            "flag": "true if score >= threshold: send the ticket to the senior team",
            "threshold": info["threshold"],
        },
    }
    (out / "contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "model_version": args.version,
        "description": info["model"],
        "trained_at": info["trained_at"],
        "train_rows": info["train_rows"],
        "data_sha256": info["data_sha256"],
        "evaluation": {"on": info.get("evaluated_on", "valid (May 2026)"), **info["valid"]},
        "review_capacity": info["review_capacity"],
        "python": info["versions"]["python"],
        "versions": {p: version(p) for p in PACKAGES},
    }
    trained = {"scikit-learn": info["versions"]["scikit-learn"], "numpy": info["versions"]["numpy"],
               "pandas": info["versions"]["pandas"], "joblib": info["versions"]["joblib"]}
    if trained != metadata["versions"]:
        sys.exit(f"Stopped: the model was trained with {trained}, but this environment has {metadata['versions']}.")
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    lines = [f"{sha256(out / name)}  {name}" for name in FILES]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Made {out}: {len(cases)} parity cases, threshold {info['threshold']}.")
    print(f"Bundle digest (MODEL_SHA256): {bundle_digest(out)}")


if __name__ == "__main__":
    main()
