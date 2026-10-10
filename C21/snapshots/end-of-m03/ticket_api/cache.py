"""A shared cache in Valkey (the scaling course, Module 3).

Valkey (BSD licence) is an open-source fork of Redis and speaks the same protocol, so the
client is the `redis` package. Every API process uses the same cache, so a result that
one process computed is a hit for all of them.

The rules for keys (the authentication course uses the same words):
- A key holds EVERYTHING that changes the answer: the kind of result and its format
  version, the versions of the prompt, the model and the data it was made from, the
  caller's identity scope (who may see it), and the request's own values.
- The identity scope comes from the request's caller, never from the question text.
- Changing data does not search for keys to delete: it bumps a generation number that
  is part of the key (explicit invalidation). Old keys are never read again and expire.

When the cache does not answer (it is down, or slower than CACHE_TIMEOUT), the API works
without it: every request is a miss, and the cache is not tried again for a few seconds.
"""

import hashlib
import json
import logging
import time
import uuid

import redis
import redis.asyncio

logger = logging.getLogger("ticket_api")

PREFIX = "ta"  # the ticket API's keys; other apps on the same Valkey use their own


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def normalize_question(question: str) -> str:
    """The same question with other spaces or capitals gets the same key."""
    return " ".join(question.lower().split())


class Cache:
    """get / set with a time to live (TTL), a lock per key against stampedes, generations.
    The methods are async (redis.asyncio): a cache call never blocks the server's other
    requests (Module 2)."""

    def __init__(self, url: str, timeout: float = 0.05, retry_after_failure: float = 5.0):
        self.client = redis.asyncio.Redis.from_url(
            url, socket_timeout=timeout, socket_connect_timeout=timeout, decode_responses=True
        )
        self.retry_after_failure = retry_after_failure
        self.down_until = 0.0
        self.hits = self.misses = self.errors = 0

    # ----- the cache may fail: then it is a miss, and we stop trying for a few seconds -----

    def available(self) -> bool:
        return time.monotonic() >= self.down_until

    def _failed(self, error: Exception) -> None:
        self.errors += 1
        if self.available():
            logger.warning("cache not available (%s): working without it", error)
        self.down_until = time.monotonic() + self.retry_after_failure

    async def get(self, key: str) -> dict | None:
        if not self.available():
            return None
        try:
            raw = await self.client.get(key)
        except redis.RedisError as error:
            self._failed(error)
            return None
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return json.loads(raw)

    async def set(self, key: str, value: dict, ttl: float) -> None:
        if not self.available() or ttl <= 0:
            return
        try:
            await self.client.set(key, json.dumps(value), px=int(ttl * 1000))
        except redis.RedisError as error:
            self._failed(error)

    # ----- one refresh at a time (the stampede guard) -----

    async def lock(self, key: str, seconds: float) -> str | None:
        """A token if this caller may compute the value of `key`; None if another does."""
        if not self.available():
            return None
        token = uuid.uuid4().hex
        try:
            if await self.client.set(f"{key}:lock", token, nx=True, px=int(seconds * 1000)):
                return token
        except redis.RedisError as error:
            self._failed(error)
        return None

    async def unlock(self, key: str, token: str) -> None:
        # Delete the lock only if it is still ours (it may have expired and been taken).
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        try:
            await self.client.eval(script, 1, f"{key}:lock", token)
        except redis.RedisError as error:
            self._failed(error)

    # ----- explicit invalidation: generations -----

    async def generation(self, scope: str) -> int:
        """The current generation of a scope's data (0 if it never changed)."""
        if not self.available():
            return 0
        try:
            return int(await self.client.get(f"{PREFIX}:gen:{scope}") or 0)
        except redis.RedisError as error:
            self._failed(error)
            return 0

    async def invalidate(self, scope: str) -> None:
        """Every cached result of this scope is old now: the next key is a new one."""
        try:
            await self.client.incr(f"{PREFIX}:gen:{scope}")
        except redis.RedisError as error:
            # Not fatal for the change itself, but cached answers may stay old until their
            # TTL ends: log it.
            logger.warning("cache invalidation of %s failed: %s", scope, error)

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except redis.RedisError:
            return False

    async def close(self) -> None:
        await self.client.aclose()


def answer_key(scope: str, generation: int, question: str, versions: dict) -> str:
    """The key of a cached answer. Everything that changes the answer is in it."""
    v = ":".join(f"{k}={versions[k]}" for k in sorted(versions))
    return f"{PREFIX}:answer:v1:{v}:{scope}:g{generation}:{digest(normalize_question(question))}"


def embedding_key(model: str, dimensions: int, text: str) -> str:
    """An embedding depends only on the model and the exact text: no identity scope is
    needed, because only a caller who has the text can make this key."""
    return f"{PREFIX}:embedding:v1:{model}:{dimensions}:{digest(text)}"


def make_cache(url: str | None, timeout: float) -> Cache | None:
    return Cache(url, timeout=timeout) if url else None
