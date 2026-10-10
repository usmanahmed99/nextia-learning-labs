"""A rate limit per caller (the scaling course, Module 4): at most N new tickets per minute.

A fixed window: one counter per caller and minute in the shared cache (so every API
process counts together). Over the limit, the API answers 429 with Retry-After = the
seconds until the next minute starts. Without a cache, there is no limit (fail open):
a cache failure must not stop customers from sending tickets.
"""

import time

from ticket_api.cache import PREFIX, Cache


class RateLimited(Exception):
    def __init__(self, retry_after: int, limit: int):
        super().__init__(f"more than {limit} requests in one minute")
        self.retry_after = retry_after
        self.limit = limit


async def check(cache: Cache | None, actor: str, limit: int, now: float | None = None) -> None:
    if cache is None or limit <= 0:
        return
    now = time.time() if now is None else now
    window = int(now // 60)
    count = await cache.count(f"{PREFIX}:rate:{actor}:{window}", 60)
    if count is not None and count > limit:
        raise RateLimited(max(1, 60 - int(now % 60)), limit)
