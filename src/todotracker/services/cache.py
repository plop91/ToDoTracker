"""Simple in-memory cache for static data."""

import asyncio
from datetime import datetime, timedelta
from typing import TypeVar, Generic, Callable, Awaitable

T = TypeVar("T")


class AsyncCache(Generic[T]):
    """Simple async-aware in-memory cache with TTL support.

    Designed for caching static or rarely-changing data like priority levels.
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with a time-to-live in seconds.

        Args:
            ttl_seconds: How long cached data remains valid (default 5 minutes).
        """
        self._data: T | None = None
        self._expires_at: datetime | None = None
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()

    def is_valid(self) -> bool:
        """Check if cached data is still valid."""
        if self._data is None or self._expires_at is None:
            return False
        return datetime.now() < self._expires_at

    def get(self) -> T | None:
        """Get cached data if valid, otherwise None."""
        if self.is_valid():
            return self._data
        return None

    def set(self, data: T) -> None:
        """Set cached data with current TTL."""
        self._data = data
        self._expires_at = datetime.now() + self._ttl

    def invalidate(self) -> None:
        """Invalidate the cache, forcing next access to refresh."""
        self._data = None
        self._expires_at = None

    async def get_or_fetch(self, fetch_func: Callable[[], Awaitable[T]]) -> T:
        """Get cached data or fetch it if cache is invalid.

        Thread-safe: uses async lock to prevent thundering herd.

        Args:
            fetch_func: Async function to call if cache miss.

        Returns:
            Cached or freshly fetched data.
        """
        # Fast path: check cache without lock
        cached = self.get()
        if cached is not None:
            return cached

        # Slow path: acquire lock and fetch
        async with self._lock:
            # Double-check after acquiring lock
            cached = self.get()
            if cached is not None:
                return cached

            # Fetch and cache
            data = await fetch_func()
            self.set(data)
            return data


# Global cache instances for commonly accessed static data
priority_cache: AsyncCache[list] = AsyncCache(ttl_seconds=300)  # 5 minutes
