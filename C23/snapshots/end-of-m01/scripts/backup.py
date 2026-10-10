"""Back up the database with pg_dump, and write a manifest that a restore drill can check.

    python -m scripts.backup                 writes backups/<database>-<time>.dump and .json

The dump is PostgreSQL's custom format (pg_dump -Fc): compressed, and pg_restore can
restore all of it or a part. The manifest has what the restore must give back: the
migrations, the number of rows in each table, a checksum of each table's contents, and
the dump's own SHA-256. The files in object storage are NOT in the dump: back them up
separately (the restore drill checks that they are still there).

It uses pg_dump on your computer if it has the server's major version (18); else it
runs pg_dump inside the Docker container (docker compose exec db).
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from ticket_api.config import load_env, read_secret

ROOT = Path(__file__).resolve().parent.parent
BACKUPS = ROOT / "backups"
TABLES = {  # table: the columns that order its rows for the checksum
    "customers": "customer_id",
    "tickets": "ticket_id",
    "messages": "message_id",
    "attachments": "attachment_id",
    "documents": "doc_id, version",
    "ai_runs": "run_id",
    "ticket_embeddings": "ticket_id",
}


def server_major(url: str) -> int:
    with psycopg.connect(url) as conn:
        return int(conn.execute("SHOW server_version_num").fetchone()[0]) // 10000


def tool(name: str, url: str) -> list[str]:
    """The command for pg_dump or pg_restore: local if it fits the server, else in Docker."""
    local = shutil.which(name)
    if local:
        out = subprocess.run([local, "--version"], capture_output=True, text=True).stdout
        if out.split()[-1].split(".")[0] == str(server_major(url)):
            return [local]
    if shutil.which("docker"):
        return ["docker", "compose", "exec", "-T", "db", name, "-U", user(url)]
    raise SystemExit(f"{name} {server_major(url)} was not found, and Docker is not available.")


def user(url: str) -> str:
    return psycopg.conninfo.conninfo_to_dict(url).get("user", "postgres")


def dbname(url: str) -> str:
    return psycopg.conninfo.conninfo_to_dict(url)["dbname"]


def manifest(url: str, conn: psycopg.Connection | None = None) -> dict:
    """What the database has: migrations, rows and a checksum of each table. With `conn`, it
    reads inside that connection's transaction (the same snapshot as the dump)."""
    if conn is None:
        with psycopg.connect(url) as own:
            return manifest(url, own)
    out = {
        "migrations": [
            r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")
        ],
        "tables": {},
    }
    for table, order in TABLES.items():
        cols = "embedding_version, " if table == "ticket_embeddings" else ""
        n, digest = conn.execute(
            "SELECT count(*), md5(coalesce(string_agg(t::text, E'\\n' ORDER BY"
            f" {cols}{order}), ''))"
            f" FROM {table} t"
        ).fetchone()
        out["tables"][table] = {"rows": n, "md5": digest}
    out["stored_files"] = conn.execute(
        "SELECT count(*) FROM attachments"
        + (" WHERE status = 'stored'" if has_status(conn) else "")
    ).fetchone()[0]
    return out


def has_status(conn) -> bool:
    return conn.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns"
        " WHERE table_name = 'attachments' AND column_name = 'status')"
    ).fetchone()[0]


def backup(url: str) -> Path:
    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = BACKUPS / f"{dbname(url)}-{stamp}.dump"
    command = tool("pg_dump", url)
    with psycopg.connect(url) as conn:
        # One snapshot for the dump and the manifest: rows written while the backup runs are in
        # neither, so the manifest describes exactly what the dump has.
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        snapshot = conn.execute("SELECT pg_export_snapshot()").fetchone()[0]
        target = url if len(command) == 1 else dbname(url)
        args = ["-Fc", f"--snapshot={snapshot}", "-d", target]
        started = time.perf_counter()
        with open(path, "wb") as f:
            subprocess.run(command + args, stdout=f, check=True)
        seconds = time.perf_counter() - started
        contents = manifest(url, conn)
    info = {
        "database": dbname(url),
        "made_at": stamp,
        "dump": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "seconds": round(seconds, 2),
        "pg_dump": subprocess.run(
            command + ["--version"], capture_output=True, text=True
        ).stdout.strip(),
        **contents,
    }
    path.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    load_env()
    url = read_secret("DATABASE_URL")
    path = backup(url)
    info = json.loads(path.with_suffix(".json").read_text())
    print(f"Backup: {path.relative_to(ROOT)} ({info['bytes'] / 1e6:.1f} MB, {info['seconds']} s)")
    print(
        f"Manifest: {path.with_suffix('.json').relative_to(ROOT)}: {len(info['migrations'])}"
        " migrations, " + ", ".join(f"{t} {v['rows']}" for t, v in info["tables"].items())
    )
    print(
        "Not in the backup: the files in object storage. A backup is not proven until a"
        " restore works:"
        f" python -m scripts.restore_drill {path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
