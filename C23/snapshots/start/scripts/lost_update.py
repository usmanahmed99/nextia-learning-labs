"""Two sessions add a message to the same ticket at the same time. Watch an update get lost.

    python -m scripts.lost_update                 read, then write: one of the two updates is lost
    python -m scripts.lost_update --lock          SELECT ... FOR UPDATE: the second session waits
    python -m scripts.lost_update --atomic        UPDATE ... SET n = n + 1: one statement
    python -m scripts.lost_update --json          the steps as JSON (for the explorer)

The two sessions are two real database connections, A and B. The script runs their
steps in a fixed order, so the result is the same every time (a constructed case:
in real life the timing is luck). Each session counts the ticket's messages the way
a careless program would: read message_count, add one in Python, write it back.
The ticket's count is put back as it was at the end.
"""

import argparse
import json
import sys
import threading
import time

import psycopg

from ticket_api.config import load_env, read_secret

TICKET = "T-30002"


def run(url: str, mode: str, ticket: str = TICKET) -> dict:
    steps = []

    def log(session: str, action: str, value=None):
        steps.append({"session": session, "action": action, "value": value})

    a = psycopg.connect(url)
    b = psycopg.connect(url)
    try:
        start = a.execute(
            "SELECT message_count FROM tickets WHERE ticket_id = %s", (ticket,)
        ).fetchone()[0]
        a.commit()
        log("-", "start", start)
        lock = " FOR UPDATE" if mode == "lock" else ""
        read = f"SELECT message_count FROM tickets WHERE ticket_id = %s{lock}"
        if mode == "atomic":
            add_one = "UPDATE tickets SET message_count = message_count + 1 WHERE ticket_id = %s"
            a.execute(add_one, (ticket,))
            log("A", "UPDATE ... SET message_count = message_count + 1 (locks the row)")
            done = threading.Event()
            t = threading.Thread(target=lambda: (b.execute(add_one, (ticket,)), done.set()))
            t.start()
            if not done.wait(0.5):
                log(
                    "B",
                    "UPDATE ... SET message_count = message_count + 1: waits, because A has"
                    " locked the row",
                )
            a.commit()
            log("A", "COMMIT")
            t.join()
            log("B", "the UPDATE runs now, on A's committed value")
            b.commit()
            log("B", "COMMIT")
        else:
            seen_a = a.execute(read, (ticket,)).fetchone()[0]
            log("A", "read" + (" (lock the row)" if lock else ""), seen_a)
            seen_b = None
            done = threading.Event()

            def session_b():
                nonlocal seen_b
                seen_b = b.execute(read, (ticket,)).fetchone()[0]  # with FOR UPDATE: waits for A
                done.set()

            t = threading.Thread(target=session_b)
            t.start()
            if done.wait(0.5):
                log("B", "read", seen_b)
            else:
                log("B", "read: waits, because A has locked the row")
            a.execute(
                "UPDATE tickets SET message_count = %s WHERE ticket_id = %s", (seen_a + 1, ticket)
            )
            log("A", "write", seen_a + 1)
            a.commit()
            log("A", "COMMIT")
            t.join()
            if lock:
                log("B", "read (after A's commit)", seen_b)
            b.execute(
                "UPDATE tickets SET message_count = %s WHERE ticket_id = %s", (seen_b + 1, ticket)
            )
            log("B", "write", seen_b + 1)
            b.commit()
            log("B", "COMMIT")
        end = a.execute(
            "SELECT message_count FROM tickets WHERE ticket_id = %s", (ticket,)
        ).fetchone()[0]
        a.commit()
        log("-", "end", end)
        # Put the count back.
        a.execute("UPDATE tickets SET message_count = %s WHERE ticket_id = %s", (start, ticket))
        a.commit()
    finally:
        a.close()
        b.close()
    return {
        "mode": mode,
        "ticket": ticket,
        "start": start,
        "end": end,
        "expected": start + 2,
        "lost_updates": start + 2 - end,
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--lock", action="store_true")
    group.add_argument("--atomic", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    load_env()
    url = read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    mode = "lock" if args.lock else "atomic" if args.atomic else "read-then-write"
    started = time.perf_counter()
    result = run(url, mode)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    for s in result["steps"]:
        value = "" if s["value"] is None else f"  message_count = {s['value']}"
        print(f"{s['session']:>2}  {s['action']}{value}")
    print(
        f"Two messages were added: the count should be {result['expected']}. It is {result['end']}"
        + (f": {result['lost_updates']} update lost." if result["lost_updates"] else ".")
        + f" ({time.perf_counter() - started:.2f} s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
