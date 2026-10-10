"""Audit events: who did, or tried, what, in which organization, and the result
(the authentication course, Modules 5 and 6).

An event never holds a token, a cookie, a password, a secret or a message's text. The
`details` of an event are cleaned before they are written: keys that name a secret are
dropped, and any value that looks like a JWT is replaced.
"""

import json
import logging
import re

import psycopg
from psycopg.types.json import Jsonb

from ticket_api.db import Database

logger = logging.getLogger("ticket_api")

SECRET_KEYS = re.compile(r"token|secret|password|cookie|authorization|code", re.I)
JWT = re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]*")


def clean(details: dict | None) -> dict:
    out = {}
    for key, value in (details or {}).items():
        if SECRET_KEYS.search(key):
            continue
        if isinstance(value, str):
            value = JWT.sub("[removed]", value)
        out[key] = value
    return out


def write(
    conn: psycopg.Connection,
    *,
    action: str,
    result: str,
    actor_id: str | None,
    actor_kind: str = "user",
    tenant_id: str | None = None,
    target: str | None = None,
    reason: str | None = None,
    request_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Write one event in the caller's transaction (it commits with the change it records)."""
    conn.execute(
        "INSERT INTO audit_events (actor_id, actor_kind, tenant_id, action, target, result,"
        " reason, request_id, details) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            actor_id,
            actor_kind,
            tenant_id,
            action,
            target,
            result,
            reason,
            request_id,
            Jsonb(clean(details)),
        ),
    )


def record(db: Database, **event) -> None:
    """Write one event in its own short transaction (for refusals: nothing else commits)."""
    try:
        with db.connection() as conn:
            write(conn, **event)
    except Exception:  # an audit failure must not hide the answer; it is logged instead
        logger.exception("audit event not written: %s", json.dumps(clean(event), default=str))
