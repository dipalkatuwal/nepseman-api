"""
cache.py
--------
Lightweight in-memory TTL cache for NEPSE API responses.

Usage:
    from app.core.cache import cache

    @cache.ttl(seconds=30)
    async def get_live_market():
        ...

Or manually:
    value = cache.get("key")
    cache.set("key", value, ttl=600)
"""

import logging
import time
from functools import wraps
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """Thread-safe in-memory TTL cache."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (value, time.monotonic() + ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()
        logger.info("Cache cleared.")

    def stats(self) -> dict:
        now = time.monotonic()
        active = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        return {
            "active_keys": active,
            "total_keys": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(
                self._hits / (self._hits + self._misses) * 100, 1
            ) if (self._hits + self._misses) > 0 else 0.0,
        }

    def ttl(self, seconds: int):
        """
        Decorator for async functions.

        @cache.ttl(seconds=30)
        async def get_live_market():
            ...
        """
        def decorator(fn):
            @wraps(fn)
            async def wrapper(*args, **kwargs):
                key = f"{fn.__module__}.{fn.__qualname__}:{args}:{sorted(kwargs.items())}"
                cached = self.get(key)
                if cached is not None:
                    logger.debug(f"Cache HIT: {key[:80]}")
                    return cached
                result = await fn(*args, **kwargs)
                if result is not None:
                    self.set(key, result, ttl=seconds)
                return result
            return wrapper
        return decorator


# Singleton
cache = TTLCache()
