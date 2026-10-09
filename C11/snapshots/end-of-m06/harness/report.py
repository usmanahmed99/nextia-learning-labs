"""The baseline-versus-candidate report, in Markdown. Every number names its cases, so a reader can
check any score against the saved outputs (python -m harness show CASE_ID --run RUN_ID)."""

from .compare import by_slice, paired_difference, per_case, wins_losses
from .dataset import version
from .release import BLOCKERS, decide, operations
from .scorers.decisions import needs_human_counts, team_accuracy


def _ids(ids: list[str], limit: int = 12) -> str:
    return ", ".join(ids[:limit]) + (f" and {len(ids) - limit} more" if len(ids) > limit else "") if ids else "none"


def build(cases, base_run, base_outputs, cand_run, cand_outputs, split: str) -> str:
    base_outputs = {c.case_id: base_outputs.get(c.case_id) for c in cases}
    cand_outputs = {c.case_id: cand_outputs.get(c.case_id) for c in cases}
    lines = [f"# Release report: {cand_run.run_id} against {base_run.run_id}", "",
             f"- Split: {split} ({len(cases)} cases); dataset version {version()} "
             f"(runs recorded on {base_run.dataset_version}; inputs version {base_run.inputs_version})",
             f"- Baseline: {base_run.system}, prompt {base_run.prompt}, {base_run.model} ({base_run.model_version})",
             f"- Candidate: {cand_run.system}, prompt {cand_run.prompt}, {cand_run.model} ({cand_run.model_version})", ""]
    decision = decide(cases, base_run.run_id, base_outputs, cand_run.run_id, cand_outputs)
    lines += ["## Decision", "", "**Ship.**" if decision.ship else "**Do not ship.**", ""]
    lines += [f"- {r}" for r in decision.reasons] + [""]
    lines += ["## Blockers (any one fails the release)", "", "| Case | Blocker | Evidence | Found by |", "|---|---|---|---|"]
    lines += [f"| {b.case_id} | {BLOCKERS[b.code]} | {b.evidence} | {b.source} |" for b in decision.blockers] or ["| none | | | |"]
    lines += ["", "## Measures (95% bootstrap intervals; paired differences on the same cases)", "",
              "| Measure | Baseline | Candidate | Candidate - baseline | Cases better / worse |", "|---|---|---|---|---|"]
    for measure in ("decisions", "criteria"):
        b, c = per_case(cases, base_outputs, measure), per_case(cases, cand_outputs, measure)
        wl = wins_losses(b, c)
        lines.append(f"| {measure} | {sum(b.values()):.0f}/{len(b)} | {sum(c.values()):.0f}/{len(c)} | "
                     f"{paired_difference(b, c)} | {_ids(wl['better'], 6)} / {_ids(wl['worse'], 6)} |")
    for name, outs in (("Baseline", base_outputs), ("Candidate", cand_outputs)):
        ok, n = team_accuracy(cases, outs)
        nh = needs_human_counts(cases, outs)
        lines.append(f"\n{name}: team {ok}/{n}; needs a person: caught {nh.tp} of {nh.tp + nh.fn}, "
                     f"false alarms {nh.fp} (precision {nh.precision:.2f}, recall {nh.recall:.2f}).")
    lines += ["", "## By slice (criteria passed; small slices move a lot: read the intervals)", "",
              "| Slice | Baseline | Candidate |", "|---|---|---|"]
    bs = by_slice(cases, per_case(cases, base_outputs, "criteria"))
    cs = by_slice(cases, per_case(cases, cand_outputs, "criteria"))
    lines += [f"| {s} | {bs[s]} | {cs[s]} |" for s in bs]
    ob, oc = operations(base_outputs), operations(cand_outputs)
    lines += ["", "## Cost and time (recorded)", "", "| | Baseline | Candidate |", "|---|---|---|",
              f"| Cost per 1,000 tickets | US${ob['cost_per_1000_usd']:.2f} | US${oc['cost_per_1000_usd']:.2f} |",
              f"| Latency median / p95 | {ob['latency_median_s']:.2f} / {ob['latency_p95_s']:.2f} s | "
              f"{oc['latency_median_s']:.2f} / {oc['latency_p95_s']:.2f} s |",
              f"| Median tokens in / out | {ob['tokens_in_median']:.0f} / {ob['tokens_out_median']:.0f} | "
              f"{oc['tokens_in_median']:.0f} / {oc['tokens_out_median']:.0f} |", ""]
    return "\n".join(lines)
