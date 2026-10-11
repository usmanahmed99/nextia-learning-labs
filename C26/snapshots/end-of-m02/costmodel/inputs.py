"""Read the design pack's input files and check them.

Every number in the cost model is one of three kinds:
- measured:   from a real run (measured.toml says which run),
- price:      a published list price (prices.toml says where it comes from),
- assumption: a value we chose, written as a range [low, base, high] (demand.toml).
The loaders below refuse a number that does not say what it is.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = ("low", "base", "high")


class InputError(ValueError):
    """An input file is missing something, or a value does not make sense."""


@dataclass(frozen=True)
class Price:
    name: str
    value: float
    unit: str
    source: str


@dataclass(frozen=True)
class Measured:
    name: str
    value: float
    unit: str
    source: str


def read_toml(path: Path) -> dict:
    if not path.exists():
        raise InputError(f"{path.name} is missing (expected at {path})")
    with path.open("rb") as f:
        try:
            return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise InputError(f"{path.name}: {e}") from None


def _entries(data: dict, kind: str, cls, path: Path) -> dict:
    out = {}
    for name, entry in data.items():
        if not isinstance(entry, dict):
            continue
        for key in ("value", "unit", "source"):
            if key not in entry:
                raise InputError(f"{path.name}: {kind} '{name}' has no {key}")
        if not isinstance(entry["value"], int | float) or isinstance(entry["value"], bool):
            raise InputError(f"{path.name}: {kind} '{name}' must be a number")
        if entry["value"] < 0:
            raise InputError(f"{path.name}: {kind} '{name}' is negative")
        if not str(entry["source"]).strip():
            raise InputError(f"{path.name}: {kind} '{name}' has an empty source")
        out[name] = cls(name, float(entry["value"]), entry["unit"], entry["source"])
    return out


def load_prices(path: Path | None = None) -> dict[str, Price]:
    path = path or ROOT / "prices.toml"
    return _entries(read_toml(path), "price", Price, path)


def load_measured(path: Path | None = None) -> dict[str, Measured]:
    path = path or ROOT / "measured.toml"
    return _entries(read_toml(path), "measured value", Measured, path)


def check_range(name: str, value) -> tuple[float, float, float]:
    """A range is [low, base, high] with low <= base <= high."""
    if not (isinstance(value, list) and len(value) == 3 and all(isinstance(v, int | float) for v in value)):
        raise InputError(f"'{name}' must be a range [low, base, high], got {value!r}")
    low, base, high = (float(v) for v in value)
    if not low <= base <= high:
        raise InputError(f"'{name}': low <= base <= high is not true for {value}")
    if low < 0:
        raise InputError(f"'{name}' is negative")
    return low, base, high


def pick(value: tuple[float, float, float], scenario: str) -> float:
    return value[SCENARIOS.index(scenario)]
