"""A small in-process cache with a time limit (the authentication course, Module 4).

The scaling course adds a shared cache (Redis); the rule for keys is the same there:
a key holds EVERYTHING that changes the answer. For an organization's data that means
the organization first, then what the caller may see (for example the access level),
then the request's own values and the data version.

    key = cache_key("bramble", "similar", "T-40001", 5, None, None, "e5-small-v1")
"""

import threading
import time


def cache_key(tenant_id: str, name: str, *parts) -> tuple:
    if not tenant_id:
        raise ValueError("a cache key of an organization's data needs the organization")
    return (tenant_id, name, *parts)


class TtlCache:
    def __init__(self, seconds: float = 60, max_items: int = 10_000):
        self.seconds = seconds
        self.max_items = max_items
        self.hits = self.misses = 0
        self._items: dict[tuple, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple):
        with self._lock:
            found = self._items.get(key)
            if found is None or found[0] < time.monotonic():
                self._items.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return found[1]

    def set(self, key: tuple, value) -> None:
        if self.seconds <= 0:
            return
        with self._lock:
            if len(self._items) >= self.max_items:
                self._items.clear()  # simple and safe: start again
            self._items[key] = (time.monotonic() + self.seconds, value)

    def drop_tenant(self, tenant_id: str) -> int:
        """Forget everything of one organization (when its data or members change)."""
        with self._lock:
            keys = [k for k in self._items if k[0] == tenant_id]
            for k in keys:
                del self._items[k]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
