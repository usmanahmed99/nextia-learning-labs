"""The command line of the evaluation harness: python -m harness <command> ...

Run `python -m harness --help` for the list. Every command reads saved files only (cases, saved
outputs, recorded judgments), unless you choose a live judge in .env.
"""

import argparse
import json
import sys
from collections import Counter

from . import dataset
from .dataset import load_cases
from .run import find_run, load_outputs, load_runs

SPLIT_HELP = "dev (default), holdout, contaminated or all"


def _cases(split: str):
    if split == "holdout":
        print("Note: the holdout set is frozen. Use it once, for the release decision.\n")
    return load_cases(split=split)


def cmd_cases(a) -> None:
    cases = load_cases(split="all")
    print(f"{len(cases)} cases, dataset version {dataset.version()}")
    for split in dataset.SPLITS:
        part = [c for c in cases if c.split == split]
        print(f"  {split:13} {len(part):4}   needs a person: {sum(c.expected.needs_human for c in part):3}   "
              f"French: {sum(c.language == 'fr' for c in part):2}")


def cmd_show(a) -> None:
    case = dataset.by_id(load_cases(split="all"))[a.case_id]
    print(f"{case.case_id} | split {case.split} | slice {case.slice} | source {case.source}"
          + (f" | tags {', '.join(case.tags)}" if case.tags else ""))
    print(f"Text: {case.text or '(empty)'}" + (f"\nAttachments: {case.attachments}" if case.attachments else ""))
    e = case.expected
    print(f"Expected: team {e.team or '(none)'} | needs_human {str(e.needs_human).lower()}"
          f"{' (' + e.rule + ')' if e.rule else ''} | next step {e.next_step}")
    print(f"Reply must: {', '.join(case.criteria.must) or '-'} | must not: {', '.join(case.criteria.must_not)}")
    print(f"Labelled by: {case.label.by}, {case.label.date}; {case.label.method}; {case.label.team_source}"
          + (f"; {case.label.changed}" if case.label.changed else ""))
    if a.run:
        from .scorers.criteria import check_reply
        run = find_run(a.run)
        out = load_outputs(run).get(case.case_id)
        if out is None:
            print(f"\n{run.run_id}: no output for this case")
            return
        print(f"\n{run.run_id}: " + (json.dumps({k: out.answer[k] for k in ("team", "needs_human", "reason")},
                                                ensure_ascii=False) if out.answer else f"no valid answer ({out.error})"))
        print(f"Reply: {out.reply}")
        for r in check_reply(case, out):
            print(f"  {'pass' if r.passed else 'FAIL'}  {r.kind:8} {r.code}" + (f"  ({r.evidence})" if r.evidence else ""))


def cmd_coverage(a) -> None:
    table = dataset.coverage(load_cases(split="all"))
    print(f"{'slice':14}{'dev':>6}{'holdout':>9}{'contaminated':>14}")
    for name, row in table.items():
        print(f"{name:14}{row.get('dev', 0):>6}{row.get('holdout', 0):>9}{row.get('contaminated', 0):>14}")


def cmd_runs(a) -> None:
    for r in load_runs().values():
        print(f"{r.run_id:42} {r.cases:4} cases  {', '.join(r.splits):26} {r.model_version}  started {r.started}")


def cmd_score(a) -> None:
    from .compare import by_slice, per_case
    from .scorers.criteria import schema_valid
    from .scorers.decisions import needs_human_counts, team_accuracy

    run = find_run(a.run)
    cases = _cases(a.split)
    outputs = load_outputs(run)
    cases = [c for c in cases if c.case_id in outputs]
    ok, n = team_accuracy(cases, outputs)
    nh = needs_human_counts(cases, outputs)
    valid = sum(schema_valid(outputs[c.case_id]) for c in cases)
    crit = per_case(cases, outputs, "criteria")
    print(f"{run.run_id} on {a.split} ({len(cases)} cases)")
    print(f"valid answers {valid}/{len(cases)} | team {ok}/{n} | needs a person: caught {nh.tp}/{nh.tp + nh.fn}, "
          f"false alarms {nh.fp} | reply criteria passed {sum(crit.values()):.0f}/{len(crit)}")
    if a.by == "slice":
        for name, value in by_slice(cases, crit).items():
            print(f"  {name:13} criteria {value[0]:.2f} (n={value[1]})")
    if a.by == "criterion":
        from .scorers.criteria import check_reply
        counts: Counter = Counter()
        totals: Counter = Counter()
        for c in cases:
            for r in check_reply(c, outputs[c.case_id]):
                totals[(r.kind, r.code)] += 1
                counts[(r.kind, r.code)] += r.passed
        for key in sorted(totals):
            print(f"  {key[0]:8} {key[1]:24} passed {counts[key]}/{totals[key]}")


def cmd_retrieval(a) -> None:
    from .scorers.retrieval import evaluate, load_rankings

    data = load_rankings()
    print(f"Saved search results: {len(data['questions'])} questions, top {a.k}")
    print(f"{'method':9}{'hit':>7}{'recall':>8}{'precision':>11}{'MRR':>7}")
    for method in data["methods"]:
        m = evaluate(data, method, a.k)
        print(f"{method:9}{m['hit']:7.3f}{m['recall']:8.3f}{m['precision']:11.3f}{m['mrr']:7.3f}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m harness", description="Evaluate Larkfield's support assistant from saved outputs.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("cases", help="count the cases per split").set_defaults(fn=cmd_cases)

    s = sub.add_parser("show", help="one case, its labels and (with --run) a saved output")
    s.add_argument("case_id")
    s.add_argument("--run")
    s.set_defaults(fn=cmd_show)

    sub.add_parser("coverage", help="cases per slice and split").set_defaults(fn=cmd_coverage)

    sub.add_parser("runs", help="the saved runs").set_defaults(fn=cmd_runs)

    s = sub.add_parser("score", help="score one run")
    s.add_argument("run")
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.add_argument("--by", choices=["slice", "criterion"])
    s.set_defaults(fn=cmd_score)

    s = sub.add_parser("retrieval", help="ranking measures on the saved search results")
    s.add_argument("--k", type=int, default=5)
    s.set_defaults(fn=cmd_retrieval)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except (KeyError, dataset.DatasetProblem) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
