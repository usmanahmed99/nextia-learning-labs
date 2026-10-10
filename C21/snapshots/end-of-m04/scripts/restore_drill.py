"""A restore drill: restore a backup into a new, empty database and check that it is complete.

    python -m scripts.restore_drill backups/tickets-20261009-120000.dump
    python -m scripts.restore_drill backups/....dump --keep      keep the restored database

A backup that was never restored is only a hope. The drill restores the dump into
<your database>_restore_drill (your own database does not change), then checks:

  1. the dump file is the one the manifest describes (SHA-256)
  2. pg_restore finished with no error
  3. the same migrations are applied
  4. every table has the same number of rows, with the same contents (checksums)
  5. every constraint is valid
  6. similar-ticket search works (the vector extension came back)
  7. every stored attachment's file is still in the object storage (not in the dump!)

and prints PASS or FAIL for each, and the time the restore took.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import psycopg

from scripts.backup import dbname, manifest, tool
from ticket_api.config import load_env, load_settings, read_secret


def check(results: list, name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "ok": ok, "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {detail}" if detail else ""))


def restore(url: str, dump: Path, keep: bool = False, files: bool = True) -> list[dict]:
    info = json.loads(dump.with_suffix(".json").read_text())
    results = []
    check(
        results,
        "dump matches its manifest",
        hashlib.sha256(dump.read_bytes()).hexdigest() == info["sha256"],
    )
    base = url.rsplit("/", 1)[0]
    target = f"{dbname(url)}_restore_drill"
    with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {target} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {target}")
    target_url = f"{base}/{target}"
    command = tool("pg_restore", url)
    args = ["--no-owner", "-d", target_url] if len(command) == 1 else ["--no-owner", "-d", target]
    started = time.perf_counter()
    with open(dump, "rb") as f:
        done = subprocess.run(command + args, stdin=f, capture_output=True, text=True)
    seconds = time.perf_counter() - started
    errors = [ln for ln in done.stderr.splitlines() if ln.strip()]
    check(
        results,
        "pg_restore finished",
        done.returncode == 0,
        f"{seconds:.1f} s" if done.returncode == 0 else "; ".join(errors[:3]),
    )
    try:
        now = manifest(target_url)
    except psycopg.Error as error:
        check(results, "restored database can be read", False, str(error).strip().splitlines()[0])
        return results
    check(
        results,
        "same migrations",
        now["migrations"] == info["migrations"],
        f"{len(now['migrations'])} of {len(info['migrations'])}",
    )
    wrong = [t for t, v in info["tables"].items() if now["tables"].get(t) != v]
    check(
        results,
        "same rows and contents in every table",
        not wrong,
        "all " + str(len(info["tables"])) + " tables"
        if not wrong
        else "different: "
        + ", ".join(
            f"{t} ({now['tables'].get(t, {}).get('rows')} rows, backup had"
            f" {info['tables'][t]['rows']})"
            for t in wrong
        ),
    )
    with psycopg.connect(target_url) as conn:
        invalid = conn.execute(
            "SELECT conname FROM pg_constraint WHERE NOT convalidated"
        ).fetchall()
        check(results, "every constraint is valid", not invalid, ", ".join(r[0] for r in invalid))
        try:
            row = conn.execute(
                "SELECT count(*) FROM (SELECT e.ticket_id FROM ticket_embeddings e"
                " ORDER BY e.embedding <=> (SELECT embedding FROM ticket_embeddings LIMIT 1)"
                " LIMIT 5) s"
            ).fetchone()
            check(
                results,
                "similar-ticket search works",
                row[0] == min(5, info["tables"]["ticket_embeddings"]["rows"]),
                f"{row[0]} results",
            )
        except psycopg.Error as error:
            check(results, "similar-ticket search works", False, str(error).strip().splitlines()[0])
            conn.rollback()
        keys = [
            r[0]
            for r in conn.execute(
                "SELECT object_key FROM attachments WHERE status = 'stored'"
                if "status"
                in [
                    c[0]
                    for c in conn.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name ="
                        " 'attachments'"
                    )
                ]
                else "SELECT object_key FROM attachments"
            )
        ]
    if files:
        files_check(results, keys)
    else:
        print("SKIP  attachment files are in the object storage (--skip-files)")
    if not keep:
        with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
            conn.execute(f"DROP DATABASE IF EXISTS {target} WITH (FORCE)")
    return results


def files_check(results: list, keys: list[str]) -> None:
    try:
        from ticket_api.files import make_store
    except ImportError:
        check(
            results,
            "attachment files are in the object storage",
            False,
            "no object storage in this project yet",
        )
        return
    store = make_store(load_settings())
    if store is None:
        check(
            results,
            "attachment files are in the object storage",
            False,
            "STORAGE_CONNECTION_STRING is not set",
        )
        return
    present = set(store.keys("tickets/"))
    missing = [k for k in keys if k not in present]
    check(
        results,
        "attachment files are in the object storage",
        not missing,
        f"{len(keys) - len(missing)} of {len(keys)} found"
        + (f"; missing e.g. {missing[0]}" if missing else ""),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dump", type=Path)
    parser.add_argument("--keep", action="store_true", help="keep the restored database")
    parser.add_argument("--skip-files", action="store_true", help="do not check the object storage")
    args = parser.parse_args(argv)
    load_env()
    results = restore(read_secret("DATABASE_URL"), args.dump, args.keep, not args.skip_files)
    failed = [r for r in results if not r["ok"]]
    print(f"Restore drill: {len(results) - len(failed)} of {len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
