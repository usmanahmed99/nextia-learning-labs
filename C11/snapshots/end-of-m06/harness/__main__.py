"""The command line of the evaluation harness: python -m harness <command> ...

Run `python -m harness --help` for the list. Every command reads saved files only (cases, saved
outputs, recorded judgments), unless you choose a live judge in .env.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from . import dataset
from .dataset import DATA, load_cases
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
            print(f"  {name:13} criteria {value}")
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


def _judge_provider(live: bool):
    from .config import Settings, make_provider
    from .providers import MockProvider

    if not live:
        return MockProvider()
    settings = Settings.from_env()
    if settings.provider == "mock":
        raise SystemExit("--live needs JUDGE_PROVIDER=openai_compatible in .env (see .env.example).")
    return make_provider(settings)


def cmd_judge(a) -> None:
    from .agreement import cohens_kappa, percent_agreement
    from .judge import parse_verdict, reference_request
    from .providers import ProviderError
    from .scorers.criteria import all_passed

    run = find_run(a.run)
    outputs = load_outputs(run)
    cases = [c for c in _cases(a.split) if c.case_id in outputs]
    provider = _judge_provider(a.live)
    prompt = f"judge_reference_{a.prompt}"
    scores, crit, code_ok = {}, {}, {}
    for case in cases:
        out = outputs[case.case_id]
        needs = out.answer.get("needs_human") if out.answer else None
        try:
            v = parse_verdict(provider.complete(reference_request(case, out.reply, needs, a.judge, prompt)))
        except ProviderError as e:
            if "content_filter" in str(e):
                print(f"{case.case_id}: no verdict: the provider's content filter refused the judge request "
                      f"(jailbreak detected: {'True' in str(e).split('jailbreak')[-1][:40]})")
            else:
                print(f"{case.case_id}: no verdict: {e}")
            if "Usage cap" in str(e):
                break
            continue
        if v.score is None:
            continue
        scores[case.case_id], crit[case.case_id] = v.score, v.critical
        code_ok[case.case_id] = all_passed(case, out)
    ids = sorted(scores)
    dist = Counter(scores[i] for i in ids)
    print(f"{a.judge} judge ({prompt}) on {run.run_id}, {a.split}: {len(ids)} replies scored")
    print("scores: " + "  ".join(f"{s}: {dist.get(s, 0)}" for s in range(1, 6))
          + f" | mean {sum(scores.values()) / max(1, len(ids)):.2f} | critical: {sum(crit.values())}")
    judge_bad = [crit[i] or scores[i] <= 2 for i in ids]
    code_bad = [not code_ok[i] for i in ids]
    print(f"agreement with the code checks (bad = critical or score 1-2 / a criterion failed): "
          f"{percent_agreement(judge_bad, code_bad):.2f}, kappa {cohens_kappa(judge_bad, code_bad):.2f}")


def cmd_pairwise(a) -> None:
    from .judge import combine, pairwise_request, parse_verdict, unswap

    ra, rb = find_run(a.run_a), find_run(a.run_b)
    oa, ob = load_outputs(ra), load_outputs(rb)
    cases = [c for c in _cases(a.split) if c.case_id in oa and c.case_id in ob]
    provider = _judge_provider(a.live)
    results = Counter()
    flips = []
    for case in cases:
        ab = parse_verdict(provider.complete(pairwise_request(case, oa[case.case_id].reply, ob[case.case_id].reply, a.judge)))
        ba = parse_verdict(provider.complete(pairwise_request(case, ob[case.case_id].reply, oa[case.case_id].reply, a.judge)))
        first, second = unswap(ab.winner, ba.winner)
        verdict = combine(first, second)
        results[verdict] += 1
        if verdict == "inconsistent":
            flips.append(case.case_id)
    print(f"{a.judge} judge, {ra.run_id} (A) against {rb.run_id} (B), {a.split}: {len(cases)} pairs, both orders")
    print(f"A better: {results['A']} | B better: {results['B']} | tie: {results['tie']} | "
          f"the verdict changed with the order: {results['inconsistent']}")
    if flips:
        print("order changed the verdict on: " + ", ".join(flips))


def _read_sheet(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["item"]: int(r["score"]) for r in rows if r.get("score", "").strip()}


def cmd_agree(a) -> None:
    from .agreement import cohens_kappa, confusion, percent_agreement, within_one

    s1, s2 = _read_sheet(Path(a.sheet_a)), _read_sheet(Path(a.sheet_b))
    items = sorted(set(s1) & set(s2))
    if not items:
        raise SystemExit("No item has a score in both sheets.")
    x, y = [s1[i] for i in items], [s2[i] for i in items]
    print(f"{len(items)} replies scored by both")
    print(f"exact agreement {percent_agreement(x, y):.2f} | within one point {within_one(x, y):.2f} | "
          f"Cohen's kappa {cohens_kappa(x, y):.2f}")
    bad_x, bad_y = [v <= 2 for v in x], [v <= 2 for v in y]
    print(f"bad (1-2) or not: agreement {percent_agreement(bad_x, bad_y):.2f}, kappa {cohens_kappa(bad_x, bad_y):.2f}")
    print("rows: first sheet, columns: second sheet")
    for k, row in confusion(x, y).items():
        print(f"  {k}: " + "  ".join(f"{c}->{n}" for c, n in sorted(row.items())))
    differ = [i for i in items if abs(s1[i] - s2[i]) >= 2]
    if differ:
        print("discuss first (2 or more points apart): " + ", ".join(differ))


def cmd_public(a) -> None:
    from .agreement import cohens_kappa, percent_agreement

    rows = [json.loads(line) for line in (DATA / "public" / "mt_bench_sample.jsonl").read_text(encoding="utf-8").splitlines()]
    pairs_h, pairs_j = [], []
    for item in rows:
        votes = sorted(item["human_ratings"], key=lambda v: v["rater_id"])
        for i in range(len(votes)):
            for j in range(i + 1, len(votes)):
                pairs_h.append((votes[i]["label"], votes[j]["label"]))
        judge = item.get("model_judge")
        if judge:
            jl = "tie" if judge["label"] == "inconsistent" else judge["label"]
            for v in votes:
                pairs_j.append((v["label"], jl))
    print(f"MT-Bench human judgments (CC BY 4.0), fixed sample: {len(rows)} items")
    for name, pairs in (("human vs human", pairs_h), ("human vs GPT-4 judge", pairs_j)):
        x, y = [p[0] for p in pairs], [p[1] for p in pairs]
        print(f"{name:21} {len(pairs):4} pairs | agreement {percent_agreement(x, y):.3f} | kappa {cohens_kappa(x, y):.3f}")


def cmd_compare(a) -> None:
    from .compare import by_slice, paired_difference, per_case, wins_losses

    rb, rc = find_run(a.baseline), find_run(a.candidate)
    ob, oc = load_outputs(rb), load_outputs(rc)
    cases = [c for c in _cases(a.split) if c.case_id in ob and c.case_id in oc]
    print(f"{rc.run_id} (candidate) against {rb.run_id} (baseline), {a.split}, {len(cases)} cases")
    for measure in ("decisions", "criteria"):
        b, c = per_case(cases, ob, measure), per_case(cases, oc, measure)
        wl = wins_losses(b, c)
        print(f"{measure:10} baseline {sum(b.values()):.0f} | candidate {sum(c.values()):.0f} | "
              f"difference {paired_difference(b, c)} | better {len(wl['better'])}, worse {len(wl['worse'])}")
        if a.by == "slice":
            bs, cs = by_slice(cases, b), by_slice(cases, c)
            for s in bs:
                print(f"    {s:13} baseline {bs[s].value:.2f}  candidate {cs[s].value:.2f}  (n={bs[s].n})")


def cmd_repeats(a) -> None:
    from .compare import repeat_spread

    runs = sorted((r for r in load_runs().values() if r.system == a.system), key=lambda r: r.repeat)
    cases = [c for c in _cases("dev")]
    outs = [load_outputs(r) for r in runs]
    cases = [c for c in cases if all(c.case_id in o for o in outs)]
    for measure in ("decisions", "criteria"):
        s = repeat_spread(cases, outs, measure)
        print(f"{a.system} x {s['runs']} runs, {measure}: totals {s['totals']} out of {s['cases']} | "
              f"min {s['min']:.0f}, max {s['max']:.0f} | {len(s['unstable_cases'])} cases changed between runs")


def cmd_decide(a) -> None:
    from .release import BLOCKERS, decide

    rb, rc = find_run(a.baseline), find_run(a.candidate)
    cases = _cases(a.split)
    d = decide(cases, rb.run_id, load_outputs(rb), rc.run_id, load_outputs(rc))
    print(f"Decision for {rc.run_id} on {a.split}: {'SHIP' if d.ship else 'DO NOT SHIP'}")
    for r in d.reasons:
        print(f"  - {r}")
    for b in d.blockers:
        print(f"  blocker {b.case_id}: {BLOCKERS[b.code]} ({b.source}{': ' + b.evidence if b.evidence else ''})")


def cmd_report(a) -> None:
    from .report import build

    rb, rc = find_run(a.baseline), find_run(a.candidate)
    text = build(_cases(a.split), rb, load_outputs(rb), rc, load_outputs(rc), a.split)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"Wrote {a.out}")


def cmd_feedback(a) -> None:
    from .feedback import load_log, summary

    s = summary(load_log())
    print("Production log (SIMULATED for the course; not real usage)")
    for k, v in s.items():
        print(f"  {k}: {v}")


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

    s = sub.add_parser("judge", help="a model judge scores every reply of a run (recorded; --live to call)")
    s.add_argument("run")
    s.add_argument("--judge", default="chat-strong")
    s.add_argument("--prompt", default="v1", choices=["v1", "v1b"])
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.add_argument("--live", action="store_true")
    s.set_defaults(fn=cmd_judge)

    s = sub.add_parser("pairwise", help="a model judge compares two runs' replies, in both orders")
    s.add_argument("run_a")
    s.add_argument("run_b")
    s.add_argument("--judge", default="chat-strong")
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.add_argument("--live", action="store_true")
    s.set_defaults(fn=cmd_pairwise)

    s = sub.add_parser("agree", help="agreement between two score sheets (CSV: item,score)")
    s.add_argument("sheet_a")
    s.add_argument("sheet_b")
    s.set_defaults(fn=cmd_agree)

    sub.add_parser("public", help="human agreement on the public MT-Bench sample").set_defaults(fn=cmd_public)

    s = sub.add_parser("compare", help="candidate against baseline, paired, with intervals")
    s.add_argument("baseline")
    s.add_argument("candidate")
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.add_argument("--by", choices=["slice"])
    s.set_defaults(fn=cmd_compare)

    s = sub.add_parser("repeats", help="the spread of repeated runs of one system on dev")
    s.add_argument("system")
    s.set_defaults(fn=cmd_repeats)

    s = sub.add_parser("decide", help="the release decision with blockers")
    s.add_argument("baseline")
    s.add_argument("candidate")
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.set_defaults(fn=cmd_decide)

    s = sub.add_parser("report", help="write the Markdown release report")
    s.add_argument("baseline")
    s.add_argument("candidate")
    s.add_argument("--split", default="dev", help=SPLIT_HELP)
    s.add_argument("--out", default="report.md")
    s.set_defaults(fn=cmd_report)

    sub.add_parser("feedback", help="the simulated production log").set_defaults(fn=cmd_feedback)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except (KeyError, dataset.DatasetProblem) as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
