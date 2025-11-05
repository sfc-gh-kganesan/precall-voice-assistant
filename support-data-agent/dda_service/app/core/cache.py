"""
In-memory caching implementation for MVP.
Simple TTL-based cache using Python dictionary.

Phase 2 will migrate to Redis for distributed caching.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time"""

    value: Any
    expires_at: float


class InMemoryCache:
    """
    Simple in-memory cache with TTL support.
    Thread-safe implementation for single-process deployments.

    Note: This cache does not persist across restarts and is not shared
    between multiple worker processes. For production with multiple workers,
    use Redis (Phase 2).
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 900):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            default_ttl: Default TTL in seconds (15 minutes = 900s)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        logger.info(
            f"Initialized in-memory cache: max_size={max_size}, ttl={default_ttl}s"
        )

    def _generate_key(self, query: str, params: Optional[Dict[str, Any]]) -> str:
        """
        Generate cache key from query and parameters.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            str: SHA256 hash of query + params
        """
        params_str = str(sorted(params.items())) if params else ""
        content = f"{query}:{params_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Get cached result for query + params.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            DataFrame or None if not in cache or expired
        """
        if not settings.CACHE_ENABLED:
            return None

        key = self._generate_key(query, params)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            logger.debug(f"Cache miss for key: {key[:16]}...")
            return None

        # Check if expired
        if time.time() > entry.expires_at:
            self._misses += 1
            # Remove expired entry
            del self._cache[key]
            logger.debug(f"Cache expired for key: {key[:16]}...")
            return None

        self._hits += 1
        logger.debug(f"Cache hit for key: {key[:16]}...")

        # Return a copy to avoid mutations
        return (
            entry.value.copy() if isinstance(entry.value, pd.DataFrame) else entry.value
        )

    def set(
        self,
        query: str,
        params: Optional[Dict[str, Any]],
        value: pd.DataFrame,
        ttl: Optional[int] = None,
    ):
        """
        Cache result for query + params.

        Args:
            query: SQL query string
            params: Query parameters
            value: DataFrame to cache
            ttl: Time to live in seconds (uses default if None)
        """
        if not settings.CACHE_ENABLED:
            return

        key = self._generate_key(query, params)
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl

        # Implement simple LRU: if cache is full, remove oldest entry
        if len(self._cache) >= self._max_size:
            # Remove entry with earliest expiration
            oldest_key = min(
                self._cache.keys(), key=lambda k: self._cache[k].expires_at
            )
            del self._cache[oldest_key]
            logger.debug(f"Evicted oldest cache entry: {oldest_key[:16]}...")

        # Store a copy to avoid external mutations
        cache_value = value.copy() if isinstance(value, pd.DataFrame) else value
        self._cache[key] = CacheEntry(value=cache_value, expires_at=expires_at)
        logger.debug(f"Cached result for key: {key[:16]}..., ttl={ttl}s")

    def invalidate(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries.

        Args:
            pattern: If provided, only invalidate keys matching pattern.
                    If None, clear entire cache.
        """
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared entire cache: {count} entries removed")
        else:
            # Simple pattern matching: if pattern in key
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(
                f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'"
            )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including hits, misses, hit rate, size
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "enabled": settings.CACHE_ENABLED,
            "backend": "in_memory",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2f}%",
            "size": len(self._cache),
            "max_size": self._max_size,
            "default_ttl": self._default_ttl,
        }

    def cleanup_expired(self):
        """Remove all expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items() if current_time > entry.expires_at
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_cache: Optional[InMemoryCache] = None


def get_cache() -> InMemoryCache:
    """
    Get or create the global cache instance.

    Returns:
        InMemoryCache: Global cache instance
    """
    global _cache
    if _cache is None:
        _cache = InMemoryCache(
            max_size=settings.CACHE_MAX_SIZE,
            default_ttl=settings.CACHE_TTL_SECONDS,
        )
    return _cache


# Convenience functions
def get_cached_query(
    query: str, params: Optional[Dict[str, Any]] = None
) -> Optional[pd.DataFrame]:
    """Get cached query result"""
    return get_cache().get(query, params)


def cache_query_result(
    query: str,
    params: Optional[Dict[str, Any]],
    result: pd.DataFrame,
    ttl: Optional[int] = None,
):
    """Cache query result"""
    get_cache().set(query, params, result, ttl)


def invalidate_cache(pattern: Optional[str] = None):
    """Invalidate cache entries"""
    get_cache().invalidate(pattern)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return get_cache().get_stats()
