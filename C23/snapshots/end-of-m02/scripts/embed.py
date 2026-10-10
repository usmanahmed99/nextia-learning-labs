"""Make ticket vectors again from the tickets' text (optional: needs an embedding model).

    python -m pip install -r requirements-embed.txt   once: sentence-transformers and torch (CPU)
    python -m scripts.embed --check                   compare fresh vectors with the stored ones
    python -m scripts.embed --rebuild                 delete the vectors, then make them again
    python -m scripts.embed --version minilm-v1       vectors from another model, a new version
    python -m scripts.embed --version minilm-v1 --make-current

Vectors are a copy: they are made from the ticket text (the original, in the tickets
table) by a model. With the same text, the same model and the same revision, you get
the same vectors back. The model is downloaded once (about 470 MB for e5-small).
Only tickets that already have a vector of the current version are embedded (all
200 in the small data, the newest 10,000 in the large data), unless you give --all.
"""

import argparse
import hashlib
import os
import sys
import time

import psycopg

from ticket_api.config import load_env, read_secret

MODELS = {  # embedding version: (model, revision, prefix, licence)
    "e5-small-v1": (
        "intfloat/multilingual-e5-small",
        "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "query: ",
        "MIT",
    ),
    "minilm-v1": (
        "sentence-transformers/all-MiniLM-L6-v2",
        "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "",
        "Apache-2.0",
    ),
}


def has_versions(conn) -> bool:
    return conn.execute("SELECT to_regclass('public.embedding_versions') IS NOT NULL").fetchone()[0]


def model_for(version: str):
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    try:
        from sentence_transformers import SentenceTransformer
        from transformers.utils import logging as transformers_logging

        transformers_logging.disable_progress_bar()
    except ImportError:
        raise SystemExit(
            "The embedding model is not installed: python -m pip install -r requirements-embed.txt"
        ) from None
    name, revision, prefix, _ = MODELS[version]
    return SentenceTransformer(name, revision=revision, device="cpu"), prefix


def embed(texts: list[str], version: str) -> list[list[float]]:
    model, prefix = model_for(version)
    vectors = model.encode(
        [prefix + t for t in texts],
        batch_size=64,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check", action="store_true", help="compare fresh vectors with the stored ones"
    )
    mode.add_argument(
        "--rebuild", action="store_true", help="delete and make the current version again"
    )
    mode.add_argument("--version", choices=sorted(MODELS), help="make vectors of another version")
    parser.add_argument(
        "--make-current", action="store_true", help="search with the new version from now on"
    )
    parser.add_argument(
        "--all", action="store_true", help="every ticket, not only those with a vector"
    )
    args = parser.parse_args(argv)
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL")) as conn:
        versioned = has_versions(conn)
        current = (
            conn.execute("SELECT version FROM embedding_versions WHERE is_current").fetchone()[0]
            if versioned
            else "e5-small-v1"
        )
        where = (
            ""
            if args.all
            else " WHERE t.ticket_id IN (SELECT ticket_id FROM ticket_embeddings"
            + (" WHERE embedding_version = %(v)s)" if versioned else ")")
        )
        rows = conn.execute(
            f"SELECT t.ticket_id, t.subject || E'\\n' || t.body FROM tickets t{where}"
            " ORDER BY t.ticket_id",
            {"v": current},
        ).fetchall()
        # From the authentication course on, every vector belongs to its ticket's organization.
        tenant_of = {}
        if conn.execute(
            "SELECT 1 FROM information_schema.columns"
            " WHERE table_name = 'ticket_embeddings' AND column_name = 'tenant_id'"
        ).fetchone():
            tenant_of = dict(conn.execute("SELECT ticket_id, tenant_id FROM tickets").fetchall())
        version = args.version or current
        started = time.perf_counter()
        vectors = embed([r[1] for r in rows], version)
        seconds = time.perf_counter() - started
        print(f"Embedded {len(rows)} tickets with {MODELS[version][0]} in {seconds:.1f} s.")
        if args.check:
            stored = dict(
                conn.execute(
                    "SELECT ticket_id, embedding::text FROM ticket_embeddings"
                    + (" WHERE embedding_version = %(v)s" if versioned else ""),
                    {"v": current},
                ).fetchall()
            )
            worst = 0.0
            for (tid, _), v in zip(rows, vectors, strict=True):
                old = [float(x) for x in stored[tid].strip("[]").split(",")]
                worst = max(worst, max(abs(a - b) for a, b in zip(old, v, strict=True)))
            print(
                f"Largest difference from the stored vectors: {worst:.2e}"
                + (" (the same, apart from rounding)." if worst < 1e-4 else ".")
            )
            return 0
        text = {r[0]: r[1] for r in rows}
        with conn.transaction():
            if versioned:
                name, revision, _, _ = MODELS[version]
                conn.execute(
                    "INSERT INTO embedding_versions (version, model, revision, dimensions)"
                    " VALUES (%s, %s, %s, %s) ON CONFLICT (version) DO NOTHING",
                    (version, name, revision, len(vectors[0])),
                )
                conn.execute(
                    "DELETE FROM ticket_embeddings WHERE embedding_version = %s", (version,)
                )
            else:
                conn.execute("DELETE FROM ticket_embeddings")
            cols = "ticket_id, embedding" + (
                ", embedding_version, source_sha256" if versioned else ""
            )
            cols += ", tenant_id" if tenant_of else ""
            with conn.cursor().copy(f"COPY ticket_embeddings ({cols}) FROM STDIN") as copy:
                for (tid, _), v in zip(rows, vectors, strict=True):
                    row = [tid, "[" + ",".join(f"{x:.7g}" for x in v) + "]"]
                    if versioned:
                        row += [version, hashlib.sha256(text[tid].encode()).hexdigest()]
                    if tenant_of:
                        row.append(tenant_of[tid])
                    copy.write_row(row)
            if versioned and args.make_current:
                conn.execute("UPDATE embedding_versions SET is_current = false WHERE is_current")
                conn.execute(
                    "UPDATE embedding_versions SET is_current = true WHERE version = %s", (version,)
                )
        print(
            f"Stored {len(rows)} vectors of version {version}"
            + (" (now the current version)." if args.make_current else ".")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
