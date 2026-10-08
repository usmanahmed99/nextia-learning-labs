"""Retrain the escalation model with the newer tickets, for a new version.

Nextia Learning, C17, Module 5. Put this file in your C05 ticket-model folder,
next to train.py, and run it there:

    python retrain.py --out model-1.1.0

C05 decided (Plan production checks) to retrain with the May and June tickets
after the warranty policy changed. This script fits the same pipeline on
train + valid (July 2024 to May 2026), and chooses the threshold for the 20%
review capacity on the June tickets (test), which the new model has not seen.
It writes the same three files as train.py, so make_bundle.py can read them.

    --balanced         weight the rare escalations more (class_weight="balanced")
    --threshold 0.19   keep a fixed threshold instead of choosing a new one

Release candidate 1.1.0-rc1 was made with both options. Together they are a
mistake: balanced weights move every score up, so the old threshold flags
far more tickets than the senior team can review.
"""

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from ticket_model import CATEGORIES, DATA, FEATURES, NUMBERS, TARGET, build_pipeline, load
from train import REVIEW_CAPACITY, choose_threshold, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--balanced", action="store_true", help='use class_weight="balanced"')
    parser.add_argument("--threshold", type=float, help="keep this threshold (not recommended)")
    args = parser.parse_args()

    fit_on = pd.concat([load("train"), load("valid")], ignore_index=True)
    june = load("test")
    model = LogisticRegression(max_iter=1000, class_weight="balanced") if args.balanced else None
    pipeline = build_pipeline(model).fit(fit_on[FEATURES], fit_on[TARGET])
    scores = pipeline.predict_proba(june[FEATURES])[:, 1]
    threshold = args.threshold if args.threshold is not None else choose_threshold(scores, REVIEW_CAPACITY)
    flagged = scores >= threshold
    caught = int((flagged & (june[TARGET] == 1)).sum())
    results = {
        "rows": len(june), "escalated": int(june[TARGET].sum()),
        "roc_auc": round(roc_auc_score(june[TARGET], scores), 3),
        "average_precision": round(average_precision_score(june[TARGET], scores), 3),
        "flagged": int(flagged.sum()), "flag_rate": round(flagged.mean(), 3),
        "precision": round(caught / max(flagged.sum(), 1), 3),
        "recall": round(caught / june[TARGET].sum(), 3),
    }

    args.out.mkdir(exist_ok=False)
    joblib.dump(pipeline, args.out / "escalation_model.joblib")
    categories = pipeline.named_steps["prepare"].named_transformers_["categories"].categories_
    info = {
        "model": "Larkfield ticket escalation: logistic regression in a scikit-learn pipeline, "
                 "retrained with the tickets up to May 2026",
        "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "target": f"{TARGET}: 1 if the ticket is escalated within 72 hours of creation",
        "prediction_time": "when the ticket is created",
        "features": {
            "categories": {name: [str(v) for v in values] for name, values in zip(CATEGORIES, categories)},
            "numbers": NUMBERS,
        },
        "threshold": threshold,
        "threshold_chosen_on": "fixed by hand" if args.threshold is not None else "test (June 2026)",
        "review_capacity": REVIEW_CAPACITY,
        "valid": results,
        "evaluated_on": "test (June 2026)",
        "train_rows": len(fit_on),
        "data_sha256": {name: sha256(DATA / name) for name in
                        ("train.csv", "valid.csv", "test.csv", "extra_features.csv")},
        "artifact_sha256": sha256(args.out / "escalation_model.joblib"),
        "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                     "scikit-learn": sklearn.__version__, "numpy": np.__version__, "joblib": joblib.__version__},
    }
    (args.out / "model_info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"Trained on {len(fit_on)} tickets (to the end of May). Threshold {threshold}"
          f"{' (fixed by hand)' if args.threshold is not None else ' for a review capacity of 20%'}.")
    print("June: ROC AUC {roc_auc}, average precision {average_precision}, flagged {flagged} of {rows} "
          "({flag_rate:.1%}), precision {precision}, recall {recall}.".format(**results))
    print(f"Saved {args.out}/escalation_model.joblib and model_info.json.")


if __name__ == "__main__":
    main()
