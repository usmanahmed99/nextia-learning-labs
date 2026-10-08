"""Score a file of tickets with the same bundle and contract as the API.

    python -m escalation.batch data/july_tickets.csv out/2026-07

Writes three files into the output folder:

    scores.csv      ticket_id, score, flag, model_version (one row per good ticket)
    rejected.csv    row, ticket_id, problem (one row per ticket that fails the contract)
    summary.json    what was read, what was written, with which model, and how long it took

A bad row does not stop the job: it is set aside in rejected.csv, and the
other rows are scored. But if more than --max-rejected of the rows are bad,
the input itself is probably broken, so the job fails (exit code 1) and
writes no scores.csv. Files are written under a temporary name and renamed at
the end, so a reader never sees half a file.
"""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from escalation.bundle import BundleError, load_bundle
from escalation.contract import FEATURES, TicketIn
from escalation.scoring import score_tickets
from escalation.settings import SettingsError, load_settings

COLUMNS = ["ticket_id"] + FEATURES


def problem(error: ValidationError) -> str:
    first = error.errors()[0]
    where = ".".join(str(p) for p in first["loc"]) or "row"
    return f"{where}: {first['msg']}"


def check_rows(chunk: pd.DataFrame, first_row: int):
    good, bad = [], []
    for offset, row in enumerate(chunk.to_dict("records")):
        values = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        try:
            good.append(TicketIn(**values))
        except ValidationError as error:
            bad.append({"row": first_row + offset, "ticket_id": values.get("ticket_id"), "problem": problem(error)})
    return good, bad


def write_atomic(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a CSV file of tickets.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="a folder for scores.csv, rejected.csv and summary.json")
    parser.add_argument("--chunk", type=int, default=500, help="tickets per chunk")
    parser.add_argument("--max-rejected", type=float, default=0.05, help="the largest share of bad rows")
    args = parser.parse_args()

    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    try:
        settings = load_settings()
        bundle = load_bundle(settings.model_bundle, settings.model_sha256)
    except (SettingsError, BundleError) as error:
        print(f"Start-up error: {error}", file=sys.stderr)
        return 2
    try:
        reader = pd.read_csv(args.input, usecols=COLUMNS, dtype=str, keep_default_na=False,
                             na_values=[""], chunksize=args.chunk)
    except ValueError as error:  # a missing column
        print(f"Stopped: {error}", file=sys.stderr)
        return 2

    scored, rejected, rows = [], [], 0
    for chunk in reader:
        good, bad = check_rows(chunk, first_row=rows + 2)  # row 1 is the header
        rows += len(chunk)
        rejected += bad
        if good:
            results, _ = score_tickets(bundle, good)
            scored += [{"ticket_id": t.ticket_id, "score": r.score, "flag": int(r.flag),
                        "model_version": bundle.version} for t, r in zip(good, results)]

    args.output.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame(scored, columns=["ticket_id", "score", "flag", "model_version"])
    write_atomic(pd.DataFrame(rejected, columns=["row", "ticket_id", "problem"]), args.output / "rejected.csv")
    failed = rows == 0 or len(rejected) / rows > args.max_rejected
    if not failed:
        write_atomic(scores, args.output / "scores.csv")
    summary = {
        "input": str(args.input),
        "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "rows": rows,
        "scored": len(scores),
        "rejected": len(rejected),
        "flagged": int(scores["flag"].sum()),
        "flag_rate": round(float(scores["flag"].mean()), 3) if len(scores) else None,
        "model_version": bundle.version,
        "bundle_sha256": bundle.digest,
        "started_at": started_at.isoformat(timespec="seconds"),
        "seconds": round(time.perf_counter() - started, 2),
        "status": "failed: too many rejected rows" if failed else "done",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Read {rows} rows: scored {len(scores)}, rejected {len(rejected)}, "
          f"flagged {summary['flagged']} ({summary['flag_rate']}). Model {bundle.version}. {summary['seconds']} s.")
    if failed:
        print(f"Failed: {len(rejected)} of {rows} rows were rejected (the limit is {args.max_rejected:.0%}). "
              f"No scores.csv was written. See {args.output / 'rejected.csv'}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
