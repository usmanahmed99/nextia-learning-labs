"""Run the whole preparation, in order, from larkfield.db to a validated
dataset. Stop at the first step that fails. At the end, write
data/model/MANIFEST.json with a SHA-256 checksum of every output file.

    python get_data.py --reset     start from a clean snapshot
    python run_pipeline.py

    python run_pipeline.py --tickets data/raw/tickets-2026-08-01.csv
                                   check a new export before you load it
"""

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

STEPS = [
    "scripts/check_input.py",
    "scripts/extract.py",
    "scripts/clean.py",
    "scripts/build_features.py",
    "scripts/split.py",
    "scripts/validate.py",
]
# Folders that only the pipeline writes. They are deleted before a run, so an
# old file can never look like the output of this run.
OUTPUT_FOLDERS = [Path("data/extract"), Path("data/clean"), Path("data/model")]
OUTPUTS = [
    "data/extract/tickets.csv", "data/extract/outcomes.csv",
    "data/clean/tickets.csv", "data/clean/quarantine.csv", "data/clean/outcomes.csv",
    "data/model/tickets_model.csv", "data/model/train.csv", "data/model/valid.csv", "data/model/test.csv",
    "data/model/build_summary.json", "data/model/split_manifest.json",
    "reports/cleaning.json", "reports/validation.json",
]
MANIFEST = Path("data/model/MANIFEST.json")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def describe(path):
    """Checksum, and the number of data rows for a CSV file."""
    entry = {"sha256": sha256(path)}
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            entry["rows"] = sum(1 for _ in csv.reader(f)) - 1  # minus the header
    return entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets", default="data/raw/tickets.csv",
                        help="the raw tickets file for the input check")
    args = parser.parse_args()

    if not Path("larkfield.db").exists():
        sys.exit("larkfield.db not found. Run: python get_data.py")
    for folder in OUTPUT_FOLDERS:
        shutil.rmtree(folder, ignore_errors=True)

    started = datetime.now(timezone.utc)
    for number, step in enumerate(STEPS, start=1):
        command = [sys.executable, step]  # the same Python that runs this script
        if step == "scripts/check_input.py":
            command += ["--tickets", args.tickets]
        name = Path(step).stem
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{number}/{len(STEPS)} {name}: FAILED\n")
            print((result.stdout + result.stderr).rstrip())
            print(f"\nStopped at step {number} ({name}). No MANIFEST.json was written: this run delivered no dataset.")
            sys.exit(1)
        print(f"{number}/{len(STEPS)} {name}: ok")

    # The extraction manifest says which snapshot and which selection the
    # dataset comes from. Its time stamp goes in "run", with this run's.
    extract = json.loads(Path("data/extract/manifest.json").read_text(encoding="utf-8"))
    outputs = {path: describe(path) for path in OUTPUTS}
    manifest = {
        "dataset": "Larkfield ticket escalation dataset",
        "source": extract["source"],
        "selection": extract["selection"],
        "queries": {f["query"]: f["query_sha256"] for f in extract["files"]},
        "steps": STEPS,
        "outputs": outputs,
        # One checksum for all outputs together: equal outputs give an
        # equal fingerprint, whatever the time of the run.
        "outputs_fingerprint": hashlib.sha256(json.dumps(outputs, sort_keys=True).encode()).hexdigest(),
        "run": {
            "started_at": started.isoformat(timespec="seconds"),
            "extracted_at": extract["extracted_at"],
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "pandas": version("pandas"),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    model = outputs["data/model/tickets_model.csv"]["rows"]
    parts = ", ".join(f"{p} {outputs[f'data/model/{p}.csv']['rows']}" for p in ["train", "valid", "test"])
    print(f"Done: {model} rows ({parts}).")
    print(f"Wrote {MANIFEST}. Outputs fingerprint: {manifest['outputs_fingerprint']}")


if __name__ == "__main__":
    main()
