"""Check the whole design pack before you hand it in (Module 6).

Each check is something a reviewer would ask: does every number say where it comes from, does
every component have a job, does every decision say when to revisit it?
"""

import re

from .components import check_diagram, load_components
from .demand import load_demand
from .inputs import ROOT, InputError, load_measured, load_prices

ADR_HEADINGS = ("## Status", "## Context", "## Options", "## Decision", "## Consequences", "## Revisit when")


def _requirements():
    text = (ROOT / "requirements.md").read_text(encoding="utf-8")
    for h in ("## Users and journeys", "## Out of scope", "## Quality attributes", "## Verified and assumed"):
        if h not in text:
            return f"requirements.md has no '{h}' section"
    rows = [line for line in text.splitlines() if line.startswith("| Q")]
    if not rows or any(line.count("|") < 6 or "| |" in line for line in rows):
        return "every quality attribute row (| Q1 ...) needs a target and how we measure it"
    return None


def _decisions():
    adrs = sorted((ROOT / "decisions").glob("adr-*.md"))
    if not adrs:
        return "decisions/ has no adr-*.md"
    for a in adrs:
        text = a.read_text(encoding="utf-8")
        missing = [h for h in ADR_HEADINGS if h not in text]
        if missing:
            return f"{a.name} has no {', '.join(missing)}"
    return None


def _failures():
    text = (ROOT / "decisions" / "failure-modes.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| F")]
    if len(rows) < 5:
        return "failure-modes.md needs at least 5 failures (| F1 ...)"
    if any(re.search(r"\|\s*\|", line) for line in rows):
        return "every failure needs an owner, a mitigation and a detection signal (no empty cells)"
    return None


def _roadmap():
    text = (ROOT / "decisions" / "roadmap.md").read_text(encoding="utf-8")
    ids = [a.stem.split("-")[1] for a in sorted((ROOT / "decisions").glob("adr-*.md"))]
    missing = [i for i in ids if f"ADR-{i}" not in text]
    return f"roadmap.md does not link ADR-{', ADR-'.join(missing)}" if missing else None


def _presentation():
    text = (ROOT / "decisions" / "presentation-outline.md").read_text(encoding="utf-8")
    for h in ("Assumptions", "Risks", "unresolved"):
        if h not in text:
            return f"presentation-outline.md does not mention '{h}'"
    return None


def _measured():
    bad = [m.name for m in load_measured().values() if not m.source.startswith("measured:")]
    return f"measured values without a run: {bad}" if bad else None


def _prices():
    bad = [p.name for p in load_prices().values() if not p.source.startswith(("price:", "price page:"))]
    return f"prices without a source page: {bad}" if bad else None


def _components():
    missing = check_diagram(load_components())
    return f"not on the container diagram: {missing}" if missing else None


CHECKS = (
    ("requirements: journeys, out of scope, measurable quality attributes", _requirements),
    ("demand: every value has evidence (verified or assumed)", lambda: load_demand() and None),
    ("prices: every price has its source", _prices),
    ("measured: every value names its run", _measured),
    ("architecture: every component has a job, an owner and a place on the diagram", _components),
    ("decisions: every ADR has status, context, options, decision, consequences, revisit", _decisions),
    ("failures: at least 5, each with owner, mitigation and signal", _failures),
    ("roadmap: every ADR appears in the roadmap", _roadmap),
    ("presentation: assumptions, risks and an unresolved assumption", _presentation),
)


def run() -> tuple[int, list[str]]:
    lines, passed = [], 0
    for name, check in CHECKS:
        try:
            problem = check()
        except (InputError, FileNotFoundError, KeyError) as e:
            problem = str(e)
        passed += problem is None
        lines.append(f"  {'PASS' if problem is None else 'FAIL'}  {name}" + (f": {problem}" if problem else ""))
    lines.append(f"Design pack check: {passed} of {len(CHECKS)} passed")
    return passed, lines
