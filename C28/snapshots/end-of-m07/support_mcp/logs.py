"""Structured logs: one JSON object per line, on stderr, with secrets and personal data removed.

On a stdio server, stdout belongs to the protocol: one stray print() there breaks the client.
So every log line goes to stderr. Each event says who called what, in which organization, and
what happened, so that a failure can be diagnosed later. It never holds a token, an e-mail
address or the text of a ticket.
"""

import json
import re
import sys
import time
from datetime import UTC, datetime

BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+")
JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
SECRET_KEYS = {"authorization", "token", "access_token", "api_key", "password", "secret"}


def redact(value):
    """A copy of `value` without tokens, secrets or e-mail addresses."""
    if isinstance(value, dict):
        return {k: "[redacted]" if k.lower() in SECRET_KEYS else redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = BEARER.sub("Bearer [redacted]", value)
        value = JWT.sub("[token]", value)
        return EMAIL.sub("[email]", value)
    return value


def ms_since(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


class Logger:
    def __init__(self, stream=None):
        self.stream = stream

    def event(self, name: str, caller=None, **fields) -> dict:
        record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "event": name}
        if caller is not None:
            record |= {"user": caller.user_id, "tenant": caller.tenant, "role": caller.role, "client": caller.client_id}
        record |= redact(fields)
        stream = self.stream or sys.stderr  # looked up at call time (tests capture stderr)
        print(json.dumps(record, ensure_ascii=False), file=stream, flush=True)
        return record


_LOGGER = Logger()


def get_logger() -> Logger:
    return _LOGGER
