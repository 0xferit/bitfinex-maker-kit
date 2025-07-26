"""
Cache service for Maker-Kit.

Provides intelligent caching with multiple backends, TTL management,
and advanced cache strategies for trading data optimization.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheBackend(Enum):
    """Available cache backends."""

    MEMORY = "memory"
    REDIS = "redis"
    HYBRID = "hybrid"


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""

    key: str
    value: Any
    timestamp: float
    ttl: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl

    def touch(self) -> None:
        """Update access metadata."""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class CacheStats:
    """Cache statistics for monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    memory_usage: int = 0

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheBackendInterface(ABC):
    """Abstract interface for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: float) -> None:
        """Set value in cache with TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass


class MemoryCacheBackend(CacheBackendInterface):
    """In-memory cache backend with LRU eviction."""

    def __init__(self, max_size: int = 1000):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of entries
        """
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from memory cache."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None

            entry.touch()
            self._stats.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: float) -> None:
        """Set value in memory cache."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()

            entry = CacheEntry(key=key, value=value, timestamp=time.time(), ttl=ttl)

            self._cache[key] = entry
            self._stats.size = len(self._cache)

    async def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._stats = CacheStats()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.size = len(self._cache)
        return self._stats

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_access)

        del self._cache[lru_key]
        self._stats.evictions += 1


class CacheService:
    """
    Intelligent cache service with multiple strategies and backends.

    Provides high-level caching operations with TTL management,
    intelligent cache warming, and performance monitoring.
    """

    def __init__(self, backend: CacheBackendInterface, default_ttl: float = 30.0):
        """
        Initialize cache service.

        Args:
            backend: Cache backend implementation
            default_ttl: Default TTL in seconds
        """
        self.backend = backend
        self.default_ttl = default_ttl
        self._key_prefix = "maker_kit:"

        # Cache warming configuration
        self._warming_tasks: dict[str, asyncio.Task] = {}
        self._warming_callbacks: dict[str, Callable] = {}

    def _make_key(self, namespace: str, key: str) -> str:
        """Create namespaced cache key."""
        # Create deterministic key from namespace and key
        combined = f"{namespace}:{key}"
        return f"{self._key_prefix}{combined}"

    async def get(self, namespace: str, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._make_key(namespace, key)
        return await self.backend.get(cache_key)

    async def set(self, namespace: str, key: str, value: Any, ttl: float | None = None) -> None:
        """
        Set value in cache.

        Args:
            namespace: Cache namespace
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        cache_key = self._make_key(namespace, key)
        cache_ttl = ttl if ttl is not None else self.default_ttl

        await self.backend.set(cache_key, value, cache_ttl)

        logger.debug(f"Cached {cache_key} with TTL {cache_ttl}s")

    async def get_or_set(
        self, namespace: str, key: str, fetch_func: Callable, ttl: float | None = None
    ) -> Any:
        """
        Get value from cache or fetch and cache if not found.

        Args:
            namespace: Cache namespace
            key: Cache key
            fetch_func: Function to fetch value if not cached
            ttl: Time to live in seconds

        Returns:
            Cached or freshly fetched value
        """
        # Try to get from cache first
        value = await self.get(namespace, key)

        if value is not None:
            return value

        # Fetch value and cache it
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                value = await fetch_func()
            else:
                value = fetch_func()

            await self.set(namespace, key, value, ttl)
            return value

        except Exception as e:
            logger.error(f"Error fetching value for {namespace}:{key}: {e}")
            raise

    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        cache_key = self._make_key(namespace, key)
        return await self.backend.delete(cache_key)

    async def clear_namespace(self, namespace: str) -> None:
        """
        Clear all keys in a namespace.

        Args:
            namespace: Namespace to clear
        """
        # Note: This is a simplified implementation
        # A real implementation would need to scan keys by prefix
        logger.warning(f"Clear namespace {namespace} not fully implemented")

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: Pattern to match (simplified glob-style)

        Returns:
            Number of keys invalidated
        """
        # Simplified implementation - real version would scan keys
        logger.warning(f"Invalidate pattern {pattern} not fully implemented")
        return 0

    def register_warming_callback(self, namespace: str, callback: Callable) -> None:
        """
        Register callback for cache warming.

        Args:
            namespace: Namespace to warm
            callback: Async function to fetch data for warming
        """
        self._warming_callbacks[namespace] = callback
        logger.info(f"Registered warming callback for namespace: {namespace}")

    async def warm_cache(self, namespace: str, keys: list) -> None:
        """
        Warm cache with specified keys.

        Args:
            namespace: Namespace to warm
            keys: List of keys to warm
        """
        if namespace not in self._warming_callbacks:
            logger.warning(f"No warming callback registered for namespace: {namespace}")
            return

        callback = self._warming_callbacks[namespace]

        async def warm_key(key: str) -> None:
            try:
                # Check if already cached
                if await self.get(namespace, key) is not None:
                    return

                # Fetch and cache
                value = await callback(key)
                if value is not None:
                    await self.set(namespace, key, value)
                    logger.debug(f"Warmed cache for {namespace}:{key}")

            except Exception as e:
                logger.error(f"Error warming cache for {namespace}:{key}: {e}")

        # Warm keys concurrently
        tasks = [warm_key(key) for key in keys]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"Cache warming completed for {namespace} ({len(keys)} keys)")

    async def start_background_warming(
        self, namespace: str, keys: list, interval: float = 300.0
    ) -> None:
        """
        Start background cache warming task.

        Args:
            namespace: Namespace to warm
            keys: List of keys to warm periodically
            interval: Warming interval in seconds
        """

        async def warming_loop() -> None:
            while True:
                try:
                    await self.warm_cache(namespace, keys)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    logger.info(f"Background warming stopped for {namespace}")
                    break
                except Exception as e:
                    logger.error(f"Error in background warming for {namespace}: {e}")
                    await asyncio.sleep(interval)

        # Cancel existing warming task if any
        if namespace in self._warming_tasks:
            self._warming_tasks[namespace].cancel()

        # Start new warming task
        task = asyncio.create_task(warming_loop())
        self._warming_tasks[namespace] = task

        logger.info(f"Started background warming for {namespace} (interval: {interval}s)")

    async def stop_background_warming(self, namespace: str) -> None:
        """
        Stop background cache warming for namespace.

        Args:
            namespace: Namespace to stop warming
        """
        if namespace in self._warming_tasks:
            self._warming_tasks[namespace].cancel()
            del self._warming_tasks[namespace]
            logger.info(f"Stopped background warming for {namespace}")

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.backend.get_stats()

    async def cleanup(self) -> None:
        """Clean up cache service resources."""
        # Stop all warming tasks
        for namespace in list(self._warming_tasks.keys()):
            await self.stop_background_warming(namespace)

        # Clear cache
        await self.backend.clear()

        logger.info("Cache service cleaned up")


def create_cache_service(
    backend_type: CacheBackend = CacheBackend.MEMORY,
    max_size: int = 1000,
    default_ttl: float = 30.0,
) -> CacheService:
    """
    Create cache service with specified backend.

    Args:
        backend_type: Type of cache backend to use
        max_size: Maximum cache size (for memory backend)
        default_ttl: Default TTL in seconds

    Returns:
        Configured CacheService instance
    """
    if backend_type == CacheBackend.MEMORY:
        backend = MemoryCacheBackend(max_size=max_size)
    else:
        raise ValueError(f"Unsupported cache backend: {backend_type}")

    return CacheService(backend, default_ttl)
