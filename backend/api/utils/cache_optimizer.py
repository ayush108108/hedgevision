"""
Advanced caching optimization utilities.

Provides cache warming, invalidation patterns, performance monitoring,
and smart caching strategies for sub-100ms response times.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from api.utils.cache import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Metrics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    avg_hit_time_ms: float = 0.0
    avg_miss_time_ms: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)

    def record_hit(self, duration_ms: float):
        """Record a cache hit."""
        self.hits += 1
        self.total_requests += 1
        self.hit_rate = self.hits / self.total_requests
        # Running average
        self.avg_hit_time_ms = (
            self.avg_hit_time_ms * (self.hits - 1) + duration_ms
        ) / self.hits

    def record_miss(self, duration_ms: float):
        """Record a cache miss."""
        self.misses += 1
        self.total_requests += 1
        self.hit_rate = self.hits / self.total_requests
        # Running average
        self.avg_miss_time_ms = (
            ((self.avg_miss_time_ms * (self.misses - 1) + duration_ms) / self.misses)
            if self.misses > 0
            else duration_ms
        )

    def reset(self):
        """Reset metrics."""
        self.__init__()

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate * 100, 2),
            "avg_hit_time_ms": round(self.avg_hit_time_ms, 2),
            "avg_miss_time_ms": round(self.avg_miss_time_ms, 2),
            "time_saved_ms": (
                round((self.avg_miss_time_ms - self.avg_hit_time_ms) * self.hits, 2)
                if self.hits > 0
                else 0
            ),
            "last_reset": self.last_reset.isoformat(),
        }


class CacheOptimizer:
    """
    Advanced cache optimization with warming, invalidation, and monitoring.
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize cache optimizer.

        Args:
            cache_manager: Cache manager instance
        """
        self.cache_mgr = cache_manager or get_cache_manager()
        self.metrics: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)
        self.warm_cache_keys: Set[str] = set()
        self.invalidation_patterns: Dict[str, List[str]] = {}

    def monitored_cache(self, key_prefix: str, ttl: int = 3600, warm: bool = False):
        """
        Decorator for monitored caching with optional warming.

        Args:
            key_prefix: Cache key prefix for organizing metrics
            ttl: Time-to-live in seconds
            warm: Whether to warm this cache on startup

        Returns:
            Decorated function
        """

        def decorator(func: Callable):
            # Track warm cache if requested
            if warm:
                self.warm_cache_keys.add(f"{key_prefix}:{func.__name__}")

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{self.cache_mgr.get_cache_key(*args, **kwargs)}"

                # Try to get from cache
                start_time = time.time()
                cached_value = self.cache_mgr.get(cache_key)

                if cached_value is not None:
                    # Cache hit
                    duration_ms = (time.time() - start_time) * 1000
                    self.metrics[key_prefix].record_hit(duration_ms)
                    logger.debug(f"Cache hit: {cache_key} ({duration_ms:.2f}ms)")
                    return cached_value

                # Cache miss - call function
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                self.metrics[key_prefix].record_miss(duration_ms)

                # Cache the result
                self.cache_mgr.set(cache_key, result, ttl)
                logger.debug(f"Cache miss: {cache_key} ({duration_ms:.2f}ms)")

                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{func.__name__}:{self.cache_mgr.get_cache_key(*args, **kwargs)}"

                # Try to get from cache
                start_time = time.time()
                cached_value = self.cache_mgr.get(cache_key)

                if cached_value is not None:
                    # Cache hit
                    duration_ms = (time.time() - start_time) * 1000
                    self.metrics[key_prefix].record_hit(duration_ms)
                    logger.debug(f"Cache hit: {cache_key} ({duration_ms:.2f}ms)")
                    return cached_value

                # Cache miss - call function
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                self.metrics[key_prefix].record_miss(duration_ms)

                # Cache the result
                self.cache_mgr.set(cache_key, result, ttl)
                logger.debug(f"Cache miss: {cache_key} ({duration_ms:.2f}ms)")

                return result

            # Return appropriate wrapper based on function type
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def register_invalidation_pattern(
        self, trigger_pattern: str, invalidate_patterns: List[str]
    ):
        """
        Register cache invalidation pattern.

        When a key matching trigger_pattern is updated/deleted,
        all keys matching invalidate_patterns will be invalidated.

        Args:
            trigger_pattern: Pattern that triggers invalidation
            invalidate_patterns: Patterns to invalidate

        Example:
            optimizer.register_invalidation_pattern(
                "asset:*:update",
                ["correlation:*", "pairs:*"]
            )
        """
        self.invalidation_patterns[trigger_pattern] = invalidate_patterns
        logger.info(
            f"Registered invalidation: {trigger_pattern} -> {invalidate_patterns}"
        )

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            Number of keys invalidated
        """
        # For Redis, we can use SCAN and DELETE
        # For memory cache, we need to iterate
        if self.cache_mgr.redis_cache:
            try:
                redis_client = self.cache_mgr.redis_cache.redis
                prefix = self.cache_mgr.redis_cache.prefix
                full_pattern = f"{prefix}{pattern}"

                # Use SCAN to avoid blocking
                keys_to_delete = []
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(
                        cursor, match=full_pattern, count=100
                    )
                    keys_to_delete.extend(keys)
                    if cursor == 0:
                        break

                if keys_to_delete:
                    redis_client.delete(*keys_to_delete)
                    logger.info(
                        f"Invalidated {len(keys_to_delete)} keys matching {pattern}"
                    )
                    return len(keys_to_delete)

                return 0
            except Exception as e:
                logger.error(f"Error invalidating pattern {pattern}: {e}")
                return 0
        else:
            # Memory cache - iterate and delete
            keys_to_delete = [
                key
                for key in self.cache_mgr.memory_cache.cache.keys()
                if self._match_pattern(key, pattern)
            ]

            for key in keys_to_delete:
                self.cache_mgr.memory_cache.delete(
                    key.replace(self.cache_mgr.prefix, "")
                )

            logger.info(f"Invalidated {len(keys_to_delete)} keys matching {pattern}")
            return len(keys_to_delete)

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching with * wildcard."""
        import re

        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", key))

    async def warm_cache(self, warm_functions: Dict[str, Callable]):
        """
        Warm cache with frequently accessed data.

        Args:
            warm_functions: Dictionary of {key: async_function} to warm

        Example:
            await optimizer.warm_cache({
                "top_pairs": lambda: get_top_pairs(limit=50),
                "correlation_matrix": lambda: get_correlation_matrix()
            })
        """
        logger.info(f"Starting cache warming for {len(warm_functions)} functions")
        start_time = time.time()

        results = {}
        for key, func in warm_functions.items():
            try:
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                results[key] = "success"
                logger.debug(f"Warmed cache: {key}")
            except Exception as e:
                results[key] = f"error: {str(e)}"
                logger.error(f"Failed to warm cache for {key}: {e}")

        duration = time.time() - start_time
        success_count = sum(1 for v in results.values() if v == "success")
        logger.info(
            f"Cache warming complete: {success_count}/{len(warm_functions)} "
            f"succeeded in {duration:.2f}s"
        )

        return results

    def get_metrics(self, key_prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache performance metrics.

        Args:
            key_prefix: Optional prefix to filter metrics

        Returns:
            Dictionary of metrics
        """
        if key_prefix:
            return {"prefix": key_prefix, "metrics": self.metrics[key_prefix].to_dict()}

        return {
            "overall": {
                "total_prefixes": len(self.metrics),
                "total_hits": sum(m.hits for m in self.metrics.values()),
                "total_misses": sum(m.misses for m in self.metrics.values()),
                "total_requests": sum(m.total_requests for m in self.metrics.values()),
                "overall_hit_rate": round(
                    sum(m.hits for m in self.metrics.values())
                    / max(sum(m.total_requests for m in self.metrics.values()), 1)
                    * 100,
                    2,
                ),
            },
            "by_prefix": {
                prefix: metrics.to_dict() for prefix, metrics in self.metrics.items()
            },
        }

    def reset_metrics(self, key_prefix: Optional[str] = None):
        """
        Reset cache metrics.

        Args:
            key_prefix: Optional prefix to reset (resets all if None)
        """
        if key_prefix:
            if key_prefix in self.metrics:
                self.metrics[key_prefix].reset()
                logger.info(f"Reset metrics for {key_prefix}")
        else:
            self.metrics.clear()
            logger.info("Reset all metrics")

    def get_cache_health(self) -> Dict[str, Any]:
        """
        Get overall cache health status.

        Returns:
            Dictionary with health information
        """
        metrics = self.get_metrics()

        overall = metrics["overall"]
        hit_rate = overall["overall_hit_rate"]

        # Determine health status
        if hit_rate >= 80:
            status = "excellent"
        elif hit_rate >= 60:
            status = "good"
        elif hit_rate >= 40:
            status = "fair"
        else:
            status = "poor"

        return {
            "status": status,
            "hit_rate": hit_rate,
            "total_requests": overall["total_requests"],
            "cache_backend": "redis" if self.cache_mgr.redis_cache else "memory",
            "warm_cache_keys": len(self.warm_cache_keys),
            "invalidation_patterns": len(self.invalidation_patterns),
            "recommendations": self._get_recommendations(hit_rate),
        }

    def _get_recommendations(self, hit_rate: float) -> List[str]:
        """Get recommendations based on cache performance."""
        recommendations = []

        if hit_rate < 60:
            recommendations.append(
                "Consider increasing TTL for frequently accessed data"
            )
            recommendations.append("Review cache key strategies for better hit rates")

        if not self.cache_mgr.redis_cache:
            recommendations.append(
                "Enable Redis for better cache performance and persistence"
            )

        if len(self.warm_cache_keys) == 0:
            recommendations.append("Implement cache warming for critical endpoints")

        if len(self.invalidation_patterns) == 0:
            recommendations.append(
                "Set up cache invalidation patterns for data consistency"
            )

        return recommendations


# Global cache optimizer instance
_cache_optimizer = None


def get_cache_optimizer() -> CacheOptimizer:
    """
    Get the global cache optimizer instance.

    Returns:
        CacheOptimizer instance
    """
    global _cache_optimizer
    if _cache_optimizer is None:
        _cache_optimizer = CacheOptimizer()

        # Register common invalidation patterns
        _cache_optimizer.register_invalidation_pattern(
            "asset:*:update", ["correlation:*", "pairs:*", "metrics:*"]
        )
        _cache_optimizer.register_invalidation_pattern(
            "price:*:update", ["correlation:*", "pairs:*", "backtest:*"]
        )
        _cache_optimizer.register_invalidation_pattern(
            "screener:*:config", ["screener:*:results"]
        )

        logger.info("Initialized global cache optimizer")

    return _cache_optimizer
