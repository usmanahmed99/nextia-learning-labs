"""Report the saved model's results on the test set, once.

Nextia Learning, C05, Module 6, lesson 3 (Thresholds and calibration). Module 8
uses the report again.

    python evaluate.py

Uses the threshold that train.py chose on valid. Writes
reports/test_report.json. If the report exists already, it stops: look at
the test set once, and do not change the model after you look.
"""

import json
import sys
from pathlib import Path

import joblib
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, roc_auc_score

from ticket_model import FEATURES, TARGET, load

REPORT = Path("reports/test_report.json")


def main():
    if REPORT.exists() and "--again" not in sys.argv:
        sys.exit(f"{REPORT} exists: the test set was used already. Read the report. "
                 "Run with --again only to reproduce it, never to choose a change.")
    pipeline = joblib.load("model/escalation_model.joblib")
    info = json.loads(Path("model/model_info.json").read_text(encoding="utf-8"))
    test = load("test")
    scores = pipeline.predict_proba(test[FEATURES])[:, 1]
    flags = (scores >= info["threshold"]).astype(int)
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(test[TARGET], flags, labels=[0, 1]).ravel())
    rule = (test["priority"] == 1).astype(int)
    rule_tp = int((rule & test[TARGET]).sum())
    report = {
        "rows": len(test), "escalated": int(test[TARGET].sum()), "threshold": info["threshold"],
        "roc_auc": round(roc_auc_score(test[TARGET], scores), 3),
        "average_precision": round(average_precision_score(test[TARGET], scores), 3),
        "brier": round(brier_score_loss(test[TARGET], scores), 4),
        "mean_score": round(float(scores.mean()), 3), "escalated_rate": round(float(test[TARGET].mean()), 3),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "flag_rate": round((tp + fp) / len(test), 3),
        "precision": round(tp / (tp + fp), 3), "recall": round(tp / (tp + fn), 3),
        "baseline_priority_1": {"flagged": int(rule.sum()), "flag_rate": round(float(rule.mean()), 3),
                                "precision": round(rule_tp / rule.sum(), 3),
                                "recall": round(rule_tp / test[TARGET].sum(), 3)},
    }
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
