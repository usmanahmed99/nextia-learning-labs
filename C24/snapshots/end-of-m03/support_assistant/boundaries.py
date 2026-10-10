"""The trust-boundary map (trust_boundaries.json) and a check that it matches the code.

A map that is out of date is worse than none. `check` compares the map with the tools the code really
offers: a tool the map does not describe is a capability nobody threat-modelled.
"""

import json

from .data import PROJECT
from .tools import READ_SPECS, WRITE_SPECS

MAP = PROJECT / "trust_boundaries.json"


def load() -> dict:
    return json.loads(MAP.read_text(encoding="utf-8"))


def check(m: dict) -> list[str]:
    """Problems with the map: '' none. Every tool in the code is in the map with the right kind."""
    problems = []
    code = {**{n: "read" for n in READ_SPECS}, **{n: "write" for n in WRITE_SPECS}}
    for name, kind in code.items():
        if name not in m["tools"]:
            problems.append(f"the tool {name} is in the code but not in the map")
        elif m["tools"][name]["kind"] != kind:
            problems.append(f"the map says {name} is a {m['tools'][name]['kind']} tool; the code says {kind}")
    for name in m["tools"]:
        if name not in code:
            problems.append(f"the map has a tool {name} that the code does not have")
    for name, t in m["tools"].items():
        if t["kind"] == "write" and not t.get("changes"):
            problems.append(f"the write tool {name} does not say what it changes")
    return problems
