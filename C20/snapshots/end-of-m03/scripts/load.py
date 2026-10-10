"""Load Larkfield's help-desk data into PostgreSQL.

    python -m scripts.load                  the small data (40 customers, 200 tickets)
    python -m scripts.load --size large     the large data (20,000 customers, 300,000 tickets)
    python -m scripts.load --reset          delete the help-desk data first, then load
    python -m scripts.load --size large --vectors FOLDER
                                            take the large data's vectors from a folder (for
                                            example labs C20/data/large) instead of downloading
                                            them; or set LARGE_VECTORS_DIR

It applies the migrations first, so the tables exist. Then it copies the CSV files of
data/<size>/ into the tables with COPY, adds the ticket vectors, and prints the counts.
The large data is made on your computer the first time (python data/generate.py).
The database comes from DATABASE_URL (in .env). All the data is made up for the course.
"""

import argparse
import csv
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psycopg

from ticket_api import migrate
from ticket_api.config import load_env, load_settings, read_secret

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TABLES = ["customers", "tickets", "messages", "attachments", "documents", "ai_runs"]
HELP_DESK = TABLES + ["ticket_embeddings"]
# The large vectors are one 15 MB file. The labs repository keeps it; it is downloaded once.
LARGE_VECTORS_URL = (
    "https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C20/data/large/"
)
LARGE_VECTORS_SHA256 = "b675097e1a237121867f298847976f732a418b7fcedbea8b5f22843b8cbea888"
EMBEDDING_VERSION = "e5-small-v1"
DIMENSIONS = 384


def columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns"
        " WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
        (table,),
    ).fetchall()
    return [r[0] for r in rows]


def table_exists(conn: psycopg.Connection, table: str) -> bool:
    return conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()[0]


def check_files(folder: Path) -> None:
    """Compare every data file with SHA256SUMS: a changed or broken file stops the load."""
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = folder / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit(
                f"{path} is missing or changed. Make the data again: python data/generate.py"
            )


VECTOR_FILES = ("ticket_embeddings.f32", "ticket_embeddings.ids", "ticket_embeddings.json")


def make_large(vectors_from: Path | None = None) -> None:
    if not (DATA / "large" / "tickets.csv").exists():
        print("Making the large data (once, about 15 seconds) ...")
        subprocess.run(
            [sys.executable, str(DATA / "generate.py"), "--size", "large", "--out", str(DATA)],
            check=True,
        )
    vectors = DATA / "large" / "ticket_embeddings.f32"
    vectors_from = vectors_from or (
        Path(os.environ["LARGE_VECTORS_DIR"]) if os.environ.get("LARGE_VECTORS_DIR") else None
    )
    if vectors_from is not None:
        print(f"Copying the vectors of the large data from {vectors_from} ...")
        for name in VECTOR_FILES:
            if not (vectors_from / name).exists():
                raise SystemExit(f"{vectors_from / name} does not exist.")
            shutil.copyfile(vectors_from / name, DATA / "large" / name)
        if hashlib.sha256(vectors.read_bytes()).hexdigest() != LARGE_VECTORS_SHA256:
            vectors.unlink()
            raise SystemExit(f"The vectors in {vectors_from} are not the expected file.")
    elif not vectors.exists():
        print("Downloading the vectors of the large data (15 MB, once) ...")
        try:
            for name in VECTOR_FILES:
                urllib.request.urlretrieve(LARGE_VECTORS_URL + name, DATA / "large" / name)
        except OSError as error:
            print(f"Could not download the vectors ({error}). The data loads without them.")
            return
        if hashlib.sha256(vectors.read_bytes()).hexdigest() != LARGE_VECTORS_SHA256:
            vectors.unlink()
            raise SystemExit("The downloaded vectors are not the expected file. Try again.")


def copy_csv(conn: psycopg.Connection, table: str, path: Path, target: str | None = None) -> None:
    """COPY a CSV file into a table, with the columns named in the file's header."""
    with open(path, encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    cols = ", ".join(header)
    with conn.cursor() as cur, open(path, "rb") as f:
        with cur.copy(
            f"COPY {target or table} ({cols}) FROM STDIN WITH (FORMAT csv, HEADER true)"
        ) as copy:
            while block := f.read(1 << 20):
                copy.write(block)


def load_messages(conn: psycopg.Connection, path: Path) -> int:
    """Messages go through a temporary table. When messages has its foreign key (Module 2),
    the messages whose ticket does not exist go to orphaned_messages instead."""
    conn.execute("CREATE TEMP TABLE staging_messages (LIKE messages) ON COMMIT DROP")
    copy_csv(conn, "messages", path, target="staging_messages")
    orphans = 0
    if table_exists(conn, "orphaned_messages"):
        orphans = conn.execute(
            "WITH o AS (INSERT INTO orphaned_messages SELECT s.* FROM staging_messages s"
            " WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.ticket_id = s.ticket_id)"
            " RETURNING 1)"
            " SELECT count(*) FROM o"
        ).fetchone()[0]
        conn.execute(
            "DELETE FROM staging_messages s"
            " WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.ticket_id = s.ticket_id)"
        )
    conn.execute("INSERT INTO messages SELECT * FROM staging_messages")
    return orphans


def load_vectors(conn: psycopg.Connection, folder: Path) -> int:
    """Copy the precomputed ticket vectors (made by an embedding model) into ticket_embeddings."""
    raw = folder / "ticket_embeddings.f32"
    if not raw.exists():
        return 0
    ids = (folder / "ticket_embeddings.ids").read_text().split()
    data = raw.read_bytes()
    size = 4 * DIMENSIONS
    cols = columns(conn, "ticket_embeddings")
    versioned = "embedding_version" in cols
    texts = {}
    if versioned:  # Module 5 adds the version and a checksum of the text that was embedded
        texts = dict(
            conn.execute(
                "SELECT ticket_id, encode(sha256(convert_to(subject || E'\\n' || body,"
                " 'UTF8')), 'hex')"
                " FROM tickets WHERE ticket_id = ANY(%s)",
                (ids,),
            ).fetchall()
        )
    names = "ticket_id, embedding" + (", embedding_version, source_sha256" if versioned else "")
    with conn.cursor() as cur, cur.copy(f"COPY ticket_embeddings ({names}) FROM STDIN") as copy:
        for i, tid in enumerate(ids):
            numbers = struct.unpack_from(f"<{DIMENSIONS}f", data, i * size)
            row = [tid, "[" + ",".join(f"{x:.7g}" for x in numbers) + "]"]
            if versioned:
                row += [EMBEDDING_VERSION, texts[tid]]
            copy.write_row(row)
    return len(ids)


def after_load(conn: psycopg.Connection) -> None:
    """Make the columns that later modules add agree with the loaded rows."""
    for table, col in (("messages", "message_id"), ("ai_runs", "run_id")):
        conn.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'),"
            f" GREATEST((SELECT max({col}) FROM {table}), 1))"
        )
    if "message_count" in columns(conn, "tickets"):  # Module 2: the deliberate copy of the counts
        conn.execute(
            "UPDATE tickets t SET message_count = s.n, last_message_at = s.last_at"
            " FROM (SELECT ticket_id, count(*) AS n, max(created_at) AS last_at"
            " FROM messages GROUP BY ticket_id) s WHERE s.ticket_id = t.ticket_id"
        )
    if "status" in columns(conn, "attachments"):  # Module 5: loaded files are complete uploads
        conn.execute(
            "UPDATE attachments SET status = 'stored' WHERE status = 'pending' AND sha256 IS"
            " NOT NULL"
        )
    if table_exists(conn, "embedding_versions"):  # Module 5: the version that the vectors have
        conn.execute(
            "INSERT INTO embedding_versions (version, model, revision, dimensions, is_current)"
            " VALUES (%s, 'intfloat/multilingual-e5-small',"
            " '614241f622f53c4eeff9890bdc4f31cfecc418b3', 384, true)"
            " ON CONFLICT (version) DO NOTHING",
            (EMBEDDING_VERSION,),
        )


def upload_files(folder: Path, reset: bool) -> int:
    """Module 5: put the small data's files into the object storage (Azurite), if it is set up."""
    from ticket_api.files import make_store

    store = make_store(load_settings())
    if store is None:
        return 0
    store.ensure_container()
    if reset:
        for key in list(store.keys("tickets/")):
            store.delete(key)
    files = sorted(p for p in (folder / "files").rglob("*") if p.is_file())
    for p in files:
        key = p.relative_to(folder / "files").as_posix()
        kind = "application/pdf" if p.suffix == ".pdf" else "image/png"
        store.put(key, p.read_bytes(), kind)
    return len(files)


def load(
    url: str,
    size: str = "small",
    reset: bool = False,
    quiet: bool = False,
    files: bool = True,
    vectors_from: Path | None = None,
) -> dict:
    folder = DATA / size
    if size == "large":
        make_large(vectors_from)
    check_files(folder)
    with psycopg.connect(url) as conn:
        conn.execute("SET client_min_messages = warning")
        existing = conn.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND tablename = 'customers'"
        ).fetchone()[0]
        if existing and conn.execute("SELECT EXISTS (SELECT 1 FROM customers)").fetchone()[0]:
            if not reset:
                raise SystemExit(
                    "The help-desk tables already have data. "
                    "Run again with --reset to delete it and load again."
                )
    if migrate.main([], url=url, quiet=quiet) != 0:
        raise SystemExit("The migrations failed: nothing was loaded.")
    started = time.perf_counter()
    with psycopg.connect(url) as conn:
        extra = ["orphaned_messages", "file_deletions", "erasures"]  # tables that later modules add
        present = [t for t in HELP_DESK + extra if table_exists(conn, t)]
        if reset:
            conn.execute(f"TRUNCATE {', '.join(present)} RESTART IDENTITY CASCADE")
        for table in TABLES:
            if table == "messages":
                orphans = load_messages(conn, folder / "messages.csv")
            else:
                copy_csv(conn, table, folder / f"{table}.csv")
        vectors = load_vectors(conn, folder)
        after_load(conn)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("ANALYZE")
        counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in HELP_DESK}
    uploaded = 0
    if files and size == "small" and (folder / "files").exists() and _has_storage():
        uploaded = upload_files(folder, reset)
    seconds = time.perf_counter() - started
    if not quiet:
        print(f"Loaded the {size} data in {seconds:.1f} s:")
        for t, n in counts.items():
            print(f"  {t:<18} {n:>9,}")
        if uploaded:
            print(f"  {uploaded} files uploaded to the object storage.")
        if orphans:
            print(f"  {orphans} messages have no ticket: they are in orphaned_messages.")
        if size == "large" and not vectors:
            print(
                "  The large data has no vectors: python -m scripts.load --size large --reset"
                " to try again."
            )
    return {"seconds": seconds, "counts": counts, "orphans": orphans}


def _has_storage() -> bool:
    try:
        import ticket_api.files  # noqa: F401  (Module 5 adds it)
    except ImportError:
        return False
    return bool(read_secret("STORAGE_CONNECTION_STRING"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", choices=["small", "large"], default="small")
    parser.add_argument("--reset", action="store_true", help="delete the help-desk data first")
    parser.add_argument(
        "--vectors", type=Path, help="a folder with the large data's vectors (no download)"
    )
    args = parser.parse_args(argv)
    load_env()
    url = read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set. Copy .env.example to .env and set it.", file=sys.stderr)
        return 1
    try:
        load(url, args.size, args.reset, vectors_from=args.vectors)
    except psycopg.OperationalError as error:
        print(
            f"Cannot connect to the database: {str(error).strip().splitlines()[0]}", file=sys.stderr
        )
        print("Is PostgreSQL running? With Docker: docker compose up -d db", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
