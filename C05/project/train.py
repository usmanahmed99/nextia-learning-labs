"""Train the escalation model, choose its threshold, and save the artifact.

Nextia Learning, C05, Module 8, lesson 1 (Package artifacts).

    python train.py

Fits the pipeline on train only, chooses the threshold on valid for the
review capacity, and writes into model/:

    escalation_model.joblib   the fitted preprocessing-plus-model pipeline
    model_info.json           feature schema, threshold, versions, checksums, valid results
    check_sample.csv          20 valid tickets and their scores, to check a reload

It never reads the test set: evaluate.py does that, once.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import average_precision_score, roc_auc_score

from ticket_model import CATEGORIES, DATA, FEATURES, NUMBERS, TARGET, build_pipeline, load

OUT = Path("model")
REVIEW_CAPACITY = 0.20  # the senior team can review at most 1 in 5 new tickets


def choose_threshold(scores, capacity):
    """The lowest threshold (in steps of 0.01) that flags no more than
    `capacity` of the tickets. Lower thresholds flag more tickets and catch
    more escalations, so the lowest one that fits catches the most."""
    for step in range(1, 100):
        threshold = step / 100
        if (scores >= threshold).mean() <= capacity:
            return threshold
    return 1.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    train, valid = load("train"), load("valid")
    pipeline = build_pipeline().fit(train[FEATURES], train[TARGET])

    scores = pipeline.predict_proba(valid[FEATURES])[:, 1]
    threshold = choose_threshold(scores, REVIEW_CAPACITY)
    flagged = scores >= threshold
    caught = int((flagged & (valid[TARGET] == 1)).sum())
    results = {
        "rows": len(valid), "escalated": int(valid[TARGET].sum()),
        "roc_auc": round(roc_auc_score(valid[TARGET], scores), 3),
        "average_precision": round(average_precision_score(valid[TARGET], scores), 3),
        "flagged": int(flagged.sum()), "flag_rate": round(flagged.mean(), 3),
        "precision": round(caught / flagged.sum(), 3),
        "recall": round(caught / valid[TARGET].sum(), 3),
    }

    OUT.mkdir(exist_ok=True)
    joblib.dump(pipeline, OUT / "escalation_model.joblib")
    sample = valid[["ticket_id", "created_at"] + FEATURES].head(20).copy()
    sample["score"] = scores[:20]
    sample.to_csv(OUT / "check_sample.csv", index=False)

    categories = pipeline.named_steps["prepare"].named_transformers_["categories"].categories_
    info = {
        "model": "Larkfield ticket escalation: logistic regression in a scikit-learn pipeline",
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "target": f"{TARGET}: 1 if the ticket is escalated within 72 hours of creation",
        "prediction_time": "when the ticket is created",
        "features": {
            "categories": {name: [str(v) for v in values] for name, values in zip(CATEGORIES, categories)},
            "numbers": NUMBERS,
        },
        "threshold": threshold,
        "review_capacity": REVIEW_CAPACITY,
        "valid": results,
        "train_rows": len(train),
        "data_sha256": {name: sha256(DATA / name) for name in ("train.csv", "valid.csv", "extra_features.csv")},
        "artifact_sha256": sha256(OUT / "escalation_model.joblib"),
        "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                     "scikit-learn": sklearn.__version__, "numpy": np.__version__, "joblib": joblib.__version__},
    }
    (OUT / "model_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")

    print(f"Trained on {len(train)} tickets. Threshold {threshold} for a review capacity of {REVIEW_CAPACITY:.0%}.")
    print("Valid: ROC AUC {roc_auc}, average precision {average_precision}, flagged {flagged} of {rows} "
          "({flag_rate:.1%}), precision {precision}, recall {recall}.".format(**results))
    print(f"Saved {OUT / 'escalation_model.joblib'}, model_info.json and check_sample.csv.")


if __name__ == "__main__":
    main()
