"""Compute the ticket embeddings of the course data with a small open model on the CPU.

    python embed.py --size small          # every ticket of out/small
    python embed.py --size large          # the newest 10,000 tickets of out/large

Needs sentence-transformers and torch (see the versions in reference/c20/BRIEF.md §4); the model is
downloaded once into the Hugging Face cache. Writes, next to the CSV files:

    ticket_embeddings.f32    float32, little-endian, one row of 384 numbers per ticket
    ticket_embeddings.ids    the ticket IDs, one per line, in the same order
    ticket_embeddings.json   model, revision, licence, embedding version, time, checksums

The text of a ticket is "query: " + subject + "\\n" + body. The e5 models ask for the prefix
"query: " on both sides of a symmetric task (finding similar tickets is one). Vectors are normalized,
so cosine distance and inner product give the same order.
"""

import argparse
import csv
import hashlib
import json
import platform
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
VERSION = "e5-small-v1"
LARGE_SUBSET = 10_000


def ticket_text(subject: str, body: str) -> str:
    return f"{subject}\n{body}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["small", "large"], required=True)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    import sentence_transformers
    import torch
    torch.set_num_threads(args.threads)
    out = HERE / "out" / args.size
    with open(out / "tickets.csv", newline="", encoding="utf-8") as f:
        rows = [(r["ticket_id"], ticket_text(r["subject"], r["body"])) for r in csv.DictReader(f)]
    if args.size == "large":
        rows = rows[-LARGE_SUBSET:]
    model = sentence_transformers.SentenceTransformer(MODEL, revision=REVISION, device="cpu")
    started = time.perf_counter()
    vectors = model.encode(["query: " + t for _, t in rows], batch_size=64, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)
    seconds = time.perf_counter() - started
    data = b"".join(struct.pack("<384f", *v.tolist()) for v in vectors)
    (out / "ticket_embeddings.f32").write_bytes(data)
    (out / "ticket_embeddings.ids").write_text("".join(tid + "\n" for tid, _ in rows))
    meta = {
        "model": MODEL, "revision": REVISION, "licence": "MIT", "embedding_version": VERSION,
        "dimensions": int(vectors.shape[1]), "count": len(rows), "normalized": True,
        "text": "'query: ' + subject + '\\n' + body",
        "source_sha256": "sha256 of subject + '\\n' + body (UTF-8), per ticket, computed by the loader",
        "seconds": round(seconds, 1), "threads": args.threads,
        "machine": f"{platform.system()} {platform.machine()}, Python {sys.version.split()[0]}",
        "versions": {"sentence-transformers": sentence_transformers.__version__, "torch": torch.__version__},
        "f32_sha256": hashlib.sha256(data).hexdigest(),
        "ids_sha256": hashlib.sha256((out / "ticket_embeddings.ids").read_bytes()).hexdigest(),
    }
    (out / "ticket_embeddings.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"{args.size}: {len(rows):,} tickets embedded in {seconds:.1f} s -> {out}/ticket_embeddings.*")


if __name__ == "__main__":
    main()
