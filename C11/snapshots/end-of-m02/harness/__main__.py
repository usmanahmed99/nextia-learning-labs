"""The command line of the evaluation harness: python -m harness <command> ...

Run `python -m harness --help` for the list. Every command reads saved files only (cases, saved
outputs, recorded judgments), unless you choose a live judge in .env.
"""

import argparse
import json
import sys

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
        run = find_run(a.run)
        out = load_outputs(run).get(case.case_id)
        if out is None:
            print(f"\n{run.run_id}: no output for this case")
            return
        print(f"\n{run.run_id}: " + (json.dumps({k: out.answer[k] for k in ("team", "needs_human", "reason")},
                                                ensure_ascii=False) if out.answer else f"no valid answer ({out.error})"))
        print(f"Reply: {out.reply}")


def cmd_coverage(a) -> None:
    table = dataset.coverage(load_cases(split="all"))
    print(f"{'slice':14}{'dev':>6}{'holdout':>9}{'contaminated':>14}")
    for name, row in table.items():
        print(f"{name:14}{row.get('dev', 0):>6}{row.get('holdout', 0):>9}{row.get('contaminated', 0):>14}")


def cmd_runs(a) -> None:
    for r in load_runs().values():
        print(f"{r.run_id:42} {r.cases:4} cases  {', '.join(r.splits):26} {r.model_version}  started {r.started}")


def cmd_score(a) -> None:
    from .scorers.decisions import needs_human_counts, team_accuracy

    run = find_run(a.run)
    cases = _cases(a.split)
    outputs = load_outputs(run)
    cases = [c for c in cases if c.case_id in outputs]
    ok, n = team_accuracy(cases, outputs)
    nh = needs_human_counts(cases, outputs)
    print(f"{run.run_id} on {a.split} ({len(cases)} cases)")
    print(f"answers {sum(outputs[c.case_id].answer is not None for c in cases)}/{len(cases)} | team {ok}/{n} | "
          f"needs a person: caught {nh.tp}/{nh.tp + nh.fn}, false alarms {nh.fp}")


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
    s.set_defaults(fn=cmd_score)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except (KeyError, dataset.DatasetProblem) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
