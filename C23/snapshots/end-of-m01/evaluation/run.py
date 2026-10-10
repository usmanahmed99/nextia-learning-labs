"""Evaluate a classifier version on the labelled tickets, and gate a release.

    python -m evaluation.run --classifier 1.1 [--split holdout] [--report reports/evaluation.json]

Prints the results, writes a JSON report, and exits with 1 when the gate in
evaluation/thresholds.json fails. The gate has three parts: floors that no
release may go below, the must-pass cases (each one correct, with the right
priority), and no regression against the baseline: the results of the
classifier in production, in evaluation/baseline.json. The gate uses the
holdout split: those tickets were never used to choose the keywords.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from ticket_api.classifier import make_classifier

HERE = Path(__file__).parent


def load_cases(split: str) -> list[dict]:
    lines = (HERE / "tickets.jsonl").read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    return [c for c in cases if split == "all" or c["split"] == split]


def evaluate(version: str, split: str) -> dict:
    classifier = make_classifier("keywords", version)
    cases = load_cases(split)
    correct, totals, hits, failures = 0, Counter(), Counter(), []
    for case in cases:
        prediction = classifier.predict(f"{case['subject']}\n{case['body']}")
        ok = prediction.category == case["category"]
        correct += ok
        totals[case["category"]] += 1
        hits[case["category"]] += ok
        if case["must_pass"] and not (ok and prediction.priority == case["priority"]):
            failures.append(case["id"])
    recall = {c: round(hits[c] / totals[c], 3) for c in sorted(totals)}
    return {
        "classifier": classifier.version,
        "split": split,
        "cases": len(cases),
        "accuracy": round(correct / len(cases), 3),
        "recall": recall,
        "must_pass_failures": failures,
    }


def gate(result: dict, thresholds: dict, baseline: dict) -> list[str]:
    problems = []
    drop = round(baseline["accuracy"] - result["accuracy"], 3)
    if drop > thresholds["max_accuracy_drop"]:
        problems.append(f"accuracy fell by {drop} from the baseline {baseline['accuracy']}")
    for category, value in result["recall"].items():
        before = baseline["recall"].get(category, 0)
        if round(before - value, 3) > thresholds["max_recall_drop"]:
            problems.append(f"recall of {category} fell from {before} to {value}")
    if result["accuracy"] < thresholds["min_accuracy"]:
        problems.append(f"accuracy {result['accuracy']} < {thresholds['min_accuracy']}")
    for category, value in result["recall"].items():
        if value < thresholds["min_recall_per_category"]:
            limit = thresholds["min_recall_per_category"]
            problems.append(f"recall of {category} {value} < {limit}")
    if thresholds["must_pass_all"] and result["must_pass_failures"]:
        problems.append(f"must-pass cases failed: {', '.join(result['must_pass_failures'])}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--classifier", default="1.0", help="CLASSIFIER_VERSION to test")
    parser.add_argument("--split", default=None, help="dev, holdout or all")
    parser.add_argument("--report", default="reports/evaluation.json")
    args = parser.parse_args()

    thresholds = json.loads((HERE / "thresholds.json").read_text(encoding="utf-8"))
    result = evaluate(args.classifier, args.split or thresholds["split"])
    baseline = json.loads(Path(thresholds["baseline"]).read_text(encoding="utf-8"))
    on_gate_split = result["split"] == thresholds["split"]
    result["baseline"] = baseline["classifier"]
    result["problems"] = gate(result, thresholds, baseline) if on_gate_split else []
    result["passed"] = not result["problems"]

    print(
        f"{result['classifier']} on {result['cases']} {result['split']} tickets"
        f" (baseline {baseline['classifier']})"
    )
    print(f"accuracy {result['accuracy']}")
    for category, value in result["recall"].items():
        print(f"recall   {category:<9}{value}")
    print(f"must-pass failures: {len(result['must_pass_failures'])}")
    for problem in result["problems"]:
        print(f"FAIL: {problem}")
    print("Gate passed." if result["passed"] else "Gate failed.")

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
