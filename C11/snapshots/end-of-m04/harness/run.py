"""Runs: the saved outputs of one system on the evaluation set, under a stable run ID.

A run records everything needed to repeat or question it: the system (a name), the prompt version and
the SHA-256 of the prompt file, the model, the dataset version, the repeat number and the time. The
run ID is built from these, so two runs with different settings never share an ID.

The outputs of the course's runs were recorded from real models (see recordings/RUNS.md in the
reference folder of the course); this project only reads them. You never need to run the assistant.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .dataset import PROJECT

OUTPUTS = PROJECT / "outputs"
MANIFEST = OUTPUTS / "runs.json"


class Run(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    system: str            # "baseline", "candidate", ...
    prompt: str            # "v2", "v3"
    prompt_sha256: str     # of the prompt file that built the requests
    model: str             # the deployment name, for example chat-small
    model_version: str     # what the provider reported, for example gpt-6-luna-2026-09-22
    dataset_version: str   # the version of cases.jsonl when the run was recorded
    inputs_version: str    # the version of the texts the system saw (labels not included)
    splits: list[str]
    repeat: int
    started: str
    finished: str
    cases: int
    note: str = ""


def make_run_id(system: str, prompt: str, prompt_sha256: str, model: str, dataset_version: str, repeat: int,
                started: str) -> str:
    """A readable, stable run ID: the settings in words, and 6 hex characters of a hash of all of them."""
    settings = json.dumps([system, prompt, prompt_sha256, model, dataset_version, repeat, started])
    return f"{system}-{prompt}-{model}-r{repeat}-{hashlib.sha256(settings.encode()).hexdigest()[:6]}"


@dataclass(frozen=True)
class Output:
    """One saved output: what the system returned for one case, and what it cost."""
    run_id: str
    case_id: str
    answer: dict | None      # the parsed JSON answer, or None
    raw_text: str | None     # the text exactly as the model returned it
    finish_reason: str
    error: str               # a provider error, or ""
    tokens_in: int
    tokens_out: int
    reasoning_tokens: int
    latency_s: float
    cost_usd: float
    recorded_at: str

    @property
    def reply(self) -> str:
        return (self.answer or {}).get("reply", "")


def load_runs(path: Path = MANIFEST) -> dict[str, Run]:
    return {r["run_id"]: Run.model_validate(r) for r in json.loads(path.read_text(encoding="utf-8"))}


def find_run(name: str, runs: dict[str, Run] | None = None) -> Run:
    """A run by its ID, or by a short name: "baseline" means the baseline's repeat 1."""
    runs = runs or load_runs()
    if name in runs:
        return runs[name]
    matches = [r for r in runs.values() if r.system == name and r.repeat == 1]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"No run {name!r}. Runs: {', '.join(sorted(runs))}")


def load_outputs(run: Run | str) -> dict[str, Output]:
    """The saved outputs of a run, by case ID."""
    run_id = run.run_id if isinstance(run, Run) else run
    path = OUTPUTS / f"{run_id}.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {r["case_id"]: Output(**r) for r in rows}
