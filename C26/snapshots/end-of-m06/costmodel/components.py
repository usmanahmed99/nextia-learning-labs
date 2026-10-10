"""The architecture's components (Module 2): one responsibility each, and on the diagram.

architecture/components.toml lists every part of the design. The check fails when a part has
no responsibility or owner, or when it is missing from the container diagram (draw.io source).
"""

from pathlib import Path

from .inputs import ROOT, InputError, read_toml

FIELDS = ("name", "kind", "responsibility", "owner", "stores")


def load_components(path: Path | None = None) -> dict:
    data = read_toml(path or ROOT / "architecture" / "components.toml").get("components", {})
    if not data:
        raise InputError("architecture/components.toml has no [components.*] tables")
    for key, c in data.items():
        for f in FIELDS:
            if f not in c or (f != "stores" and not str(c[f]).strip()):
                raise InputError(f"component '{key}' has no {f}")
    return data


def check_diagram(components: dict, diagram: Path | None = None) -> list[str]:
    """Names missing from the container diagram."""
    diagram = diagram or ROOT / "architecture" / "container.drawio"
    if not diagram.exists():
        return [c["name"] for c in components.values()]
    text = diagram.read_text(encoding="utf-8")
    return [c["name"] for c in components.values() if c["name"] not in text]


def components_table(components: dict) -> str:
    lines = [f"  {'component':<22} {'kind':<10} {'owner':<8} responsibility"]
    for c in components.values():
        lines.append(f"  {c['name']:<22} {c['kind']:<10} {c['owner']:<8} {c['responsibility']}")
    missing = check_diagram(components)
    lines.append(f"{len(components)} components, each with one responsibility and an owner; "
                 + ("all are on the container diagram" if not missing else f"NOT on the diagram: {', '.join(missing)}"))
    return "\n".join(lines)
