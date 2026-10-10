"""Look into the shared cache (Valkey).

python -m scripts.cache stats          hits, misses, keys, memory
python -m scripts.cache keys [--match 'ta:answer:*']   keys with their time to live
python -m scripts.cache flush          delete the ticket API's keys (ta:*)
"""

import argparse
import sys

import redis

from ticket_api.config import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["stats", "keys", "flush"])
    parser.add_argument("--match", default="ta:*")
    args = parser.parse_args(argv)
    url = load_settings().cache_url
    if not url:
        print("CACHE_URL is not set (see .env.example).", file=sys.stderr)
        return 1
    client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
    try:
        if args.command == "stats":
            s = client.info("stats")
            m = client.info("memory")
            hits, misses = s["keyspace_hits"], s["keyspace_misses"]
            rate = hits / (hits + misses) if hits + misses else 0.0
            n = sum(1 for _ in client.scan_iter("ta:*", count=500))
            print(f"Keys of the ticket API: {n} | memory used: {m['used_memory_human']}")
            print(
                f"Since the cache started: {hits} hits, {misses} misses (hit rate {rate:.0%}); "
                "this counts every read, including generations and locks"
            )
        elif args.command == "keys":
            for key in sorted(client.scan_iter(args.match, count=500)):
                ttl = client.pttl(key)
                print(f"{key}  ({'no expiry' if ttl < 0 else f'{ttl / 1000:.0f} s left'})")
        else:
            keys = list(client.scan_iter("ta:*", count=500))
            if keys:
                client.delete(*keys)
            print(f"Deleted {len(keys)} keys.")
    except redis.RedisError as error:
        print(
            f"The cache does not answer: {error}. With Docker: docker compose up -d cache",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
