"""When the true answers arrive, check how the served model really did.

    docker compose logs escalation --no-log-prefix > predictions.log
    python monitoring/outcomes.py predictions.log data/july_labels.csv

Reads the prediction lines that the service writes (one JSON object per
scored ticket, from the logger escalation.predictions), joins them with the
labels by ticket_id, and prints precision and recall for each model version
(and for the shadow model, if there was one). Tickets without a label yet are
counted, not guessed.
"""

import argparse
import json

import pandas as pd

MARK = "escalation.predictions: "


def read_predictions(path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as log:
        for line in log:
            if MARK in line:
                rows.append(json.loads(line.split(MARK, 1)[1]))
    return pd.DataFrame(rows).drop_duplicates("ticket_id", keep="last")


def report(name: str, flags: pd.Series, truth: pd.Series) -> str:
    caught = int((flags & truth).sum())
    precision = caught / flags.sum() if flags.sum() else float("nan")
    recall = caught / truth.sum() if truth.sum() else float("nan")
    return (f"{name}: flagged {int(flags.sum())} of {len(flags)} ({flags.mean():.1%}), "
            f"precision {precision:.3f}, recall {recall:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions")
    parser.add_argument("labels")
    args = parser.parse_args()

    predictions = read_predictions(args.predictions)
    labels = pd.read_csv(args.labels)
    joined = predictions.merge(labels, on="ticket_id", how="left")
    waiting = joined["escalated_72h"].isna().sum()
    known = joined.dropna(subset=["escalated_72h"])
    truth = known["escalated_72h"].astype(int) == 1
    print(f"{len(predictions)} predictions, {len(known)} with a label, {waiting} still waiting for one.")
    print(f"Escalated: {int(truth.sum())} ({truth.mean():.1%}).")
    for version, group in known.groupby("model_version"):
        print(report(f"Model {version}", group["flag"].astype(bool), truth[group.index]))
    if "shadow_version" in known:
        for version, group in known.dropna(subset=["shadow_version"]).groupby("shadow_version"):
            print(report(f"Shadow {version}", group["shadow_flag"].astype(bool), truth[group.index]))


if __name__ == "__main__":
    main()
