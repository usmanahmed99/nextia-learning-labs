"""The evaluation set: load the cases, check them, and give the dataset a version.

One case is one support ticket with its labels: the expected team and needs_human (with the rule of
Grace's policy), the next step that a good reply contains, and the criteria for the reply. Each case
belongs to one split: `dev` (used while you change a prompt), `holdout` (frozen: used once, for the
release decision) or `contaminated` (tickets the prompt was written and tuned on).
"""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "data"
CASES = DATA / "cases.jsonl"
SPLITS = ("dev", "holdout", "contaminated")
SLICES = ("normal", "boundary", "difficult", "french", "needs_person", "unanswerable")


class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team: Literal["delivery", "returns", "payment", "warranty", "account", ""]  # "" = no team can be scored
    needs_human: bool
    rule: Literal["H1", "H2", "H3", "H4", "H5", ""]
    next_step: str


class Criteria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    must: list[str]
    must_not: list[str]


class Label(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by: str
    date: str
    method: str
    team_source: str
    reviewed: str
    changed: str


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    text: str
    attachments: str
    source: str
    style: str
    language: Literal["en", "fr", "other"]
    slice: Literal["normal", "boundary", "difficult", "french", "needs_person", "unanswerable", "contaminated"]
    tags: list[str]
    split: Literal["dev", "holdout", "contaminated"]
    critical: bool
    expected: Expected
    criteria: Criteria
    label: Label


class DatasetProblem(Exception):
    """The evaluation set breaks one of its own rules."""


def version(path: Path = CASES) -> str:
    """The dataset version: the first 12 hex characters of the SHA-256 of the file.

    Change one character of one case and the version changes, so a score always names the exact data."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def inputs_version(cases: list[Case]) -> str:
    """A version of what the system sees (case IDs, texts and attachments), without the labels.

    A label can change after review; the saved outputs stay valid as long as this version is the same."""
    lines = sorted(json.dumps([c.case_id, c.text, c.attachments], ensure_ascii=False) for c in cases)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:12]


def load_cases(path: Path = CASES, split: str | None = None) -> list[Case]:
    """All cases, or the cases of one split. The holdout set is never loaded by accident: ask for it."""
    cases = [Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    check(cases)
    if split is None:
        return [c for c in cases if c.split != "holdout"]
    if split == "all":
        return cases
    if split not in SPLITS:
        raise ValueError(f"Unknown split {split!r}: use dev, holdout, contaminated or all.")
    return [c for c in cases if c.split == split]


def by_id(cases: list[Case]) -> dict[str, Case]:
    return {c.case_id: c for c in cases}


def text_key(text: str) -> str:
    """Two tickets with the same words (case and spacing ignored) get the same key."""
    return hashlib.sha256(" ".join(text.lower().split()).encode("utf-8")).hexdigest()[:16]


def check(cases: list[Case]) -> None:
    """The rules of the set. Raises DatasetProblem with every broken rule."""
    problems = []
    ids = Counter(c.case_id for c in cases)
    problems += [f"{i}: the case ID is used {n} times" for i, n in ids.items() if n > 1]
    seen: dict[str, Case] = {}
    for c in cases:
        if c.expected.needs_human != bool(c.expected.rule):
            problems.append(f"{c.case_id}: needs_human and rule disagree")
        if c.text.strip():
            other = seen.get(text_key(c.text))
            if other is not None and other.split != c.split:
                problems.append(f"{c.case_id}: the same text is in {other.split} ({other.case_id}) and {c.split}")
            seen[text_key(c.text)] = c
        if not c.label.by:
            problems.append(f"{c.case_id}: no labeller recorded")
    if problems:
        raise DatasetProblem("; ".join(problems))


def coverage(cases: list[Case]) -> dict[str, dict[str, int]]:
    """How many cases each slice has, per split: the table that shows what the set is missing."""
    table: dict[str, dict[str, int]] = {}
    for c in cases:
        table.setdefault(c.slice, Counter())[c.split] += 1
    return {s: dict(table[s]) for s in sorted(table)}


def save_cases(cases: list[Case], path: Path) -> None:
    """Write cases in the file's own format (one JSON object per line, keys sorted)."""
    path.write_text("".join(json.dumps(c.model_dump(), ensure_ascii=False, sort_keys=True) + "\n" for c in cases),
                    encoding="utf-8")
