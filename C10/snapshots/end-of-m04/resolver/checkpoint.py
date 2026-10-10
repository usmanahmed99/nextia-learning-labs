"""The checkpoint store: the whole TaskState, saved after every step in a local SQLite file.

A task can stop at any point (a crash, a closed laptop, an approval that takes three days) and resume
from its last checkpoint. The store keeps the state, not the process: nothing lives only in memory.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

from .data import WORK
from .state import TaskState, now

RUNS_DB = WORK / "runs.sqlite"


class CheckpointStore:
    def __init__(self, path: Path | None = None):
        path = path or RUNS_DB
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, "
                       "variant TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL, "
                       "state TEXT NOT NULL)")
            db.commit()

    def save(self, state: TaskState) -> None:
        state.updated_at = now()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
                       (state.run_id, state.task_id, state.variant, state.model, state.status, state.updated_at,
                        state.model_dump_json()))
            db.commit()

    def load(self, run_id: str) -> TaskState:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT state FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"No run {run_id}. Run `python -m resolver runs` to see the saved runs.")
        return TaskState.model_validate_json(row[0])

    def latest(self, task_id: str | None = None) -> TaskState | None:
        query = "SELECT state FROM runs" + (" WHERE task_id = ?" if task_id else "") + " ORDER BY updated_at DESC, rowid DESC LIMIT 1"
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute(query, (task_id,) if task_id else ()).fetchone()
        return TaskState.model_validate_json(row[0]) if row else None

    def list(self) -> list[tuple]:
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT run_id, task_id, variant, model, status, updated_at FROM runs "
                              "ORDER BY updated_at, rowid").fetchall()
