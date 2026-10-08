"""Build C06's ticket-text splits from the raw model replies, offline and reproducibly.

Input: raw/written-*.jsonl (Claude Haiku 5.5 wrote the tickets from specs) and raw/checked-*.jsonl
(Claude Sonnet 5.5 routed each ticket blind, with routing_policy.md). Output (default: ./out):
train.csv, valid.csv, test.csv, split_manifest.json, SHA256SUMS.

Rules:
1. Keep a ticket only if the checker's team equals the team in its spec (both readers agree).
2. Drop exact duplicates (after lower-casing and collapsing spaces).
3. Shuffle with SEED and split, stratified by team: 600 test, 600 valid, the rest train.
4. Train only: change the team of 1.5% of rows to a team that people often confuse with it,
   as happens in a real help desk. The rows are listed in split_manifest.json ("noisy_train_ids").

Usage: python build_dataset.py [out_dir]
"""
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from generate_tickets import specs

HERE = Path(__file__).parent
RAW = HERE / "raw"
SEED = 6006
N_TEST = 600
N_VALID = 600
NOISE = 0.015
CONFUSED_WITH = {"delivery": "warranty", "warranty": "delivery", "returns": "payment",
                 "payment": "returns", "account": "payment"}
STYLE = {"plain": "plain", "distractor": "distractor", "second_sentence": "request_last",
         "negation": "negation", "short": "short", "typos": "typos", "long": "long",
         "boundary": "boundary", "two_topics": "two_topics"}
TEAMS = ["delivery", "returns", "payment", "warranty", "account"]


def read_rows(pattern):
    for f in sorted(RAW.glob(pattern)):
        for line in f.read_text(encoding="utf-8").splitlines():
            yield from json.loads(line)["rows"]


def main(out: Path) -> None:
    spec = {s["spec_id"]: s for s in specs()}
    written = {r["spec_id"]: r["text"].strip() for r in read_rows("written-*.jsonl")
               if r.get("spec_id") in spec and isinstance(r.get("text"), str) and r["text"].strip()}
    checked = {r["id"]: r.get("team") for r in read_rows("checked-*.jsonl") if "id" in r}

    stats = Counter()
    seen, keep = set(), []
    for sid in sorted(written):
        s, text = spec[sid], written[sid]
        verdict = checked.get(sid)
        if verdict is None:
            stats["not_checked"] += 1
            continue
        if verdict != s["team"]:
            stats["unclear" if verdict == "unclear" else "disagree"] += 1
            continue
        key = re.sub(r"\s+", " ", text.lower())
        if key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(key)
        keep.append({"text": text, "team": s["team"], "style": STYLE[s["twist"]]})
    stats["kept"] = len(keep)

    rng = random.Random(SEED)
    by_team = defaultdict(list)
    for r in keep:
        by_team[r["team"]].append(r)
    for rows in by_team.values():
        rng.shuffle(rows)
    total = len(keep)
    split = {"test": [], "valid": [], "train": []}
    for team in TEAMS:
        rows = by_team[team]
        n_test = round(N_TEST * len(rows) / total)
        n_valid = round(N_VALID * len(rows) / total)
        split["test"] += rows[:n_test]
        split["valid"] += rows[n_test:n_test + n_valid]
        split["train"] += rows[n_test + n_valid:]
    for name in split:
        rng.shuffle(split[name])

    next_id = 60001
    for name in ("train", "valid", "test"):
        for r in split[name]:
            r["ticket_id"] = f"T-{next_id}"
            next_id += 1

    noisy = rng.sample(range(len(split["train"])), round(NOISE * len(split["train"])))
    noisy_ids = []
    for i in sorted(noisy):
        r = split["train"][i]
        r["team"] = CONFUSED_WITH[r["team"]]
        noisy_ids.append(r["ticket_id"])

    out.mkdir(parents=True, exist_ok=True)
    for name, rows in split.items():
        with (out / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["ticket_id", "text", "team", "style"], lineterminator="\n")
            w.writeheader()
            w.writerows({k: r[k] for k in ("ticket_id", "text", "team", "style")} for r in rows)
    manifest = {
        "seed": SEED,
        "filter": {k: stats[k] for k in ("kept", "disagree", "unclear", "duplicate", "not_checked")},
        "rows": {k: len(v) for k, v in split.items()},
        "teams": {k: dict(sorted(Counter(r["team"] for r in v).items())) for k, v in split.items()},
        "styles": {k: dict(sorted(Counter(r["style"] for r in v).items())) for k, v in split.items()},
        "noisy_train_ids": noisy_ids,
    }
    (out / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sums = [f"{hashlib.sha256((out / f).read_bytes()).hexdigest()}  {f}"
            for f in ("train.csv", "valid.csv", "test.csv", "split_manifest.json")]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "noisy_train_ids"}, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out")
