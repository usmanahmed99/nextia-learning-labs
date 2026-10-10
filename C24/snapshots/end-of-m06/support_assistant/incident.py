"""Incident controls: turn a tool off, and revoke a user, without a new release.

When detection raises an alert, the first job is to stop the harm. These switches live in the
database, so they work at once, for every run:

- `disable_tool(world, "fetch_url", reason)`: the tool is removed from the model's tool list, and a
  call to it is refused (code `tool_disabled`) and logged;
- `revoke_user(world, "usr-sam", reason)`: the user's runs stop before sign-in (stop `revoked`).

`restore` undoes one switch. Every change is written to the audit log with its reason.
"""

from contextlib import closing

from .state import ToolEvent
from .systems import now

TABLE = """CREATE TABLE IF NOT EXISTS incident_switches (kind TEXT NOT NULL, name TEXT NOT NULL, reason TEXT NOT NULL,
                                                     actor TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (kind, name))"""
OFF_MESSAGE = "This tool is turned off for now. Leave this part for a person."


def _con(world):
    con = world._con()
    con.execute(TABLE)
    return con


def _set(world, kind: str, name: str, reason: str, actor: str) -> None:
    with closing(_con(world)) as con:
        con.execute("INSERT OR REPLACE INTO incident_switches VALUES (?,?,?,?,?)", (kind, name, reason, actor, now()))
        con.commit()
    world.log(actor, "", f"incident_{kind}", "off", name=name, reason=reason)


def disable_tool(world, tool: str, reason: str, actor: str = "usr-kwame") -> None:
    _set(world, "tool", tool, reason, actor)


def revoke_user(world, sub: str, reason: str, actor: str = "usr-kwame") -> None:
    _set(world, "user", sub, reason, actor)


def restore(world, kind: str, name: str, actor: str = "usr-kwame") -> bool:
    with closing(_con(world)) as con:
        n = con.execute("DELETE FROM incident_switches WHERE kind=? AND name=?", (kind, name)).rowcount
        con.commit()
    if n:
        world.log(actor, "", f"incident_{kind}", "restored", name=name)
    return bool(n)


def switches(world) -> list[dict]:
    with closing(_con(world)) as con:
        return [dict(r) for r in con.execute("SELECT * FROM incident_switches ORDER BY at")]


def disabled_tools(world) -> set[str]:
    return {s["name"] for s in switches(world) if s["kind"] == "tool"}


def revoked(world, sub: str) -> bool:
    return any(s["kind"] == "user" and s["name"] == sub for s in switches(world))


def refuse_disabled(tool: str, step: int, session, world):
    """The outcome of a call to a turned-off tool (the model may still ask for it)."""
    from .tools import ToolOutcome, _json
    event = ToolEvent(step=step, tool=tool, allowed=False, code="tool_disabled", blocked_reason="tool turned off")
    world.log(session.sub, session.tenant, tool, "blocked", code="tool_disabled")
    return ToolOutcome(_json({"ok": False, "error": OFF_MESSAGE}), event)
