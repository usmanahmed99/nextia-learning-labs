"""The evaluation set: load the cases, check them, and give the dataset a version.

One case is one support ticket with its labels: the expected team and needs_human (with the rule of
Grace's policy), the next step that a good reply contains, and the criteria for the reply. Each case
belongs to one split: `dev` (used while you change a prompt), `holdout` (frozen: used once, for the
release decision) or `contaminated` (tickets the prompt was written and tuned on).
"""

import hashlib
import json
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


def version(path: Path = CASES) -> str:
    """The dataset version: the first 12 hex characters of the SHA-256 of the file.

    Change one character of one case and the version changes, so a score always names the exact data."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def load_cases(path: Path = CASES, split: str | None = None) -> list[Case]:
    """All cases, or the cases of one split. The holdout set is never loaded by accident: ask for it."""
    cases = [Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if split is None:
        return [c for c in cases if c.split != "holdout"]
    if split == "all":
        return cases
    if split not in SPLITS:
        raise ValueError(f"Unknown split {split!r}: use dev, holdout, contaminated or all.")
    return [c for c in cases if c.split == split]


def by_id(cases: list[Case]) -> dict[str, Case]:
    return {c.case_id: c for c in cases}


def save_cases(cases: list[Case], path: Path) -> None:
    """Write cases in the file's own format (one JSON object per line, keys sorted)."""
    path.write_text("".join(json.dumps(c.model_dump(), ensure_ascii=False, sort_keys=True) + "\n" for c in cases),
                    encoding="utf-8")
