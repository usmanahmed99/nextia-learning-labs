"""Logs: one JSON object per line, on stderr.

On a stdio server, stdout belongs to the protocol: one stray print() there breaks the client.
So every log line goes to stderr. Each event says who called what, in which organization, and
what happened.
"""

import json
import sys
import time
from datetime import UTC, datetime


def ms_since(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


class Logger:
    def __init__(self, stream=None):
        self.stream = stream

    def event(self, name: str, caller=None, **fields) -> dict:
        record = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), "event": name}
        if caller is not None:
            record |= {"user": caller.user_id, "tenant": caller.tenant, "role": caller.role, "client": caller.client_id}
        record |= fields
        stream = self.stream or sys.stderr  # looked up at call time (tests capture stderr)
        print(json.dumps(record, ensure_ascii=False), file=stream, flush=True)
        return record


_LOGGER = Logger()


def get_logger() -> Logger:
    return _LOGGER
