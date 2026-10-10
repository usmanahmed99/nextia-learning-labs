"""See each leak that the organization prevents, by leaving it out on purpose.

    python -m scripts.leak_demo search      similar tickets without the organization filter
    python -m scripts.leak_demo cache       a cache key without the organization, or the role
    python -m scripts.leak_demo file        a signed link made for anyone who has the file's ID
    python -m scripts.leak_demo all

Each demo builds the WRONG version next to the right one, with your database and the
made-up data (constructed for the course; the API's own code is the right version).
Nothing is changed in the database.
"""

import sys
import urllib.request

import psycopg
from psycopg.rows import dict_row

from ticket_api import repository
from ticket_api.cache import TtlCache, cache_key
from ticket_api.config import load_env, load_settings, read_secret

VERSION = "e5-small-v1"


def subject(conn, ticket_id: str) -> str:
    return conn.execute(
        "SELECT tenant_id || ': ' || subject AS s FROM tickets WHERE ticket_id = %s", (ticket_id,)
    ).fetchone()["s"]


def search(conn) -> None:
    print("1. Similar tickets of Bramble Books' T-40001, WITHOUT the organization filter (wrong):")
    source = conn.execute(
        "SELECT embedding::text AS v FROM ticket_embeddings WHERE ticket_id = 'T-40001'"
    ).fetchone()["v"]
    rows = conn.execute(
        "SELECT ticket_id, embedding <=> %s::vector AS d FROM ticket_embeddings"
        " WHERE ticket_id <> 'T-40001' ORDER BY d LIMIT 5",
        (source,),
    ).fetchall()
    for r in rows:
        print(f"   {r['ticket_id']}  {r['d']:.3f}  {subject(conn, r['ticket_id'])}")
    print("   WITH the filter (the API's code):")
    for r in repository.similar_tickets(conn, "T-40001", tenant_id="bramble", k=5, version=VERSION):
        print(f"   {r['ticket_id']}  {r['distance']:.3f}  {subject(conn, r['ticket_id'])}")


def cache(conn) -> None:
    print("2a. A cache key without the organization (wrong): key = ('similar', ticket, k)")
    wrong = TtlCache(60)
    # Grace (Larkfield) asks first; the answer is kept under a key with no organization.
    grace = repository.similar_tickets(conn, "T-30002", tenant_id="larkfield", k=3, version=VERSION)
    wrong.set(("similar", "T-30002", 3), grace)
    # Ines (Bramble Books) passes the membership check for HER organization, then asks for the
    # same ticket ID. The cache answers before the query, and the query had the filter:
    hit = wrong.get(("similar", "T-30002", 3))
    print(f"   Ines gets: {[r['ticket_id'] + ' ' + r['subject'] for r in hit]}")
    right = TtlCache(60)
    right.set(cache_key("larkfield", "similar", "T-30002", 3), grace)
    print(
        f"   With the organization in the key, Ines's key misses: "
        f"{right.get(cache_key('bramble', 'similar', 'T-30002', 3))}"
    )
    print("2b. A key without the access level (wrong): Sam (staff) asks first, then Omar")
    sam = repository.search_documents(conn, "refund approval", tenant_id="larkfield", staff=True)
    docs = TtlCache(60)
    docs.set(("larkfield", "documents", "refund approval"), sam)
    omar = docs.get(("larkfield", "documents", "refund approval"))
    print(f"   Omar (read-only) gets: {[(d['doc_id'], d['access']) for d in omar]}")


def file(conn) -> None:
    from ticket_api.files import make_store

    print("3. A signed download link is a key on its own (constructed: the link is made for")
    print("   Bramble Books' receipt, as a route would make it if it signed before checking):")
    store = make_store(load_settings())
    if store is None:
        print("   skipped: no object storage (STORAGE_CONNECTION_STRING is not set).")
        return
    row = conn.execute(
        "SELECT object_key, file_name FROM attachments WHERE tenant_id = 'bramble'"
        " AND content_type = 'application/pdf' ORDER BY object_key LIMIT 1"
    ).fetchone()
    url, until = store.download_url(row["object_key"], 300, row["file_name"])
    with urllib.request.urlopen(url, timeout=10) as response:
        data = response.read()
    print(f"   GET {url.split('?')[0]}?...  (no token, no session)")
    print(
        f"   -> {response.status}, {len(data)} bytes. Whoever has the link has the file until"
        f" {until:%H:%M:%S} UTC."
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    which = argv[0] if argv else "all"
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL"), row_factory=dict_row) as conn:
        for name, demo in (("search", search), ("cache", cache), ("file", file)):
            if which in (name, "all"):
                demo(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
