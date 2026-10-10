"""Compute the vectors of Bramble Books' tickets with the databases course's model, on the CPU.

    python embed_bramble.py            # after build_data.py; writes out/bramble/ticket_embeddings.*

Needs sentence-transformers 6.1.0 and torch 2.14.1 (the databases course's requirements-embed.txt);
the model is downloaded once into the Hugging Face cache. Same text, prefix and normalization as the
databases course's vectors ("query: " + subject + "\\n" + body), so Bramble's vectors and Larkfield's
can be compared: that is what makes a search without a shop filter leak the other shop's tickets.
A second run writes the same bytes (checked with SHA-256).
"""

import csv
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "bramble" if (HERE / "bramble").exists() else HERE / "out" / "bramble"
MODEL = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


def main() -> None:
    import sentence_transformers
    import torch

    torch.set_num_threads(4)
    with open(OUT / "tickets.csv", newline="", encoding="utf-8") as f:
        rows = [(r["ticket_id"], f"{r['subject']}\n{r['body']}") for r in csv.DictReader(f)]
    model = sentence_transformers.SentenceTransformer(MODEL, revision=REVISION, device="cpu")
    started = time.perf_counter()
    vectors = model.encode(["query: " + t for _, t in rows], batch_size=64, normalize_embeddings=True,
                           convert_to_numpy=True, show_progress_bar=False)
    seconds = time.perf_counter() - started
    data = b"".join(struct.pack("<384f", *v.tolist()) for v in vectors)
    (OUT / "ticket_embeddings.f32").write_bytes(data)
    (OUT / "ticket_embeddings.ids").write_text("".join(tid + "\n" for tid, _ in rows))
    meta = {
        "model": MODEL, "revision": REVISION, "licence": "MIT", "embedding_version": "e5-small-v1",
        "dimensions": int(vectors.shape[1]), "count": len(rows), "normalized": True,
        "text": "'query: ' + subject + '\\n' + body",
        "versions": {"sentence-transformers": sentence_transformers.__version__, "torch": torch.__version__},
        "f32_sha256": hashlib.sha256(data).hexdigest(),
    }
    (OUT / "ticket_embeddings.json").write_text(json.dumps(meta, indent=2) + "\n")
    sys.path.insert(0, str(HERE))
    try:
        from build_data import sha256sums
    except ImportError:  # the labs repository's name for the same builder
        from build_bramble import sha256sums

    sha256sums(OUT)
    print(f"{len(rows)} tickets embedded in {seconds:.1f} s; SHA-256 {meta['f32_sha256'][:12]}")


if __name__ == "__main__":
    main()
