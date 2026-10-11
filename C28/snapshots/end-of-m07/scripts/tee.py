"""Watch the messages between any host and a stdio server: put this script in between.

    python -m scripts.tee --out messages.jsonl -- python -m support_mcp

It starts the server command, passes every line from the host to the server and back unchanged,
and writes each line to --out with the time and the direction (-> host to server, <- server to
host). The server's stderr (its logs) passes through to this script's stderr.
"""

import argparse
import json
import subprocess
import sys
import threading
import time


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        print("usage: python -m scripts.tee --out FILE -- COMMAND ...", file=sys.stderr)
        return 2
    split = argv.index("--")
    p = argparse.ArgumentParser(prog="python -m scripts.tee")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv[:split])
    proc = subprocess.Popen(
        argv[split + 1 :], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1
    )
    t0 = time.perf_counter()
    lock = threading.Lock()
    out = open(a.out, "a", encoding="utf-8")

    def record(direction: str, line: str) -> None:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            message = {"not_json": line.rstrip("\n")}
        with lock:
            out.write(
                json.dumps(
                    {
                        "t_ms": round((time.perf_counter() - t0) * 1000, 1),
                        "dir": direction,
                        "bytes": len(line.encode()),
                        "message": message,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            out.flush()

    def server_to_host():
        for line in proc.stdout:
            record("<-", line)
            sys.stdout.write(line)
            sys.stdout.flush()

    th = threading.Thread(target=server_to_host, daemon=True)
    th.start()
    for line in sys.stdin:
        record("->", line)
        proc.stdin.write(line)
        proc.stdin.flush()
    proc.stdin.close()
    proc.wait()
    th.join(timeout=5)
    out.close()
    return proc.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
