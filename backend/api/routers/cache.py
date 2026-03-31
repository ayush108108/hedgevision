"""
Cache management and testing endpoints.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from api.utils.cache import get_cache_manager
from api.utils.cache_adapter import get_cache_adapter
from api.utils.cache_optimizer import get_cache_optimizer
from api.utils.config import config
from api.utils.error_handlers import DatabaseError, ValidationError
from api.utils.security import sanitize_error_message
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])

cache = get_cache_adapter(default_ttl=config["REDIS_TTL"])
cache_manager = get_cache_manager()
cache_optimizer = get_cache_optimizer()


@router.get("/health")
async def cache_health(detailed: bool = False) -> Dict[str, Any]:
    """
    Test cache connection and basic functionality.

    Args:
        detailed: If True, includes optimizer health metrics and recommendations

    Returns:
        Cache health status with optional detailed metrics
    """

    try:
        test_key = f"health_check_{int(time.time())}"
        test_value = {"timestamp": datetime.utcnow().isoformat(), "test": "data"}

        # Test set operation
        set_success = cache_manager.set(test_key, test_value, ttl=60)
        if not set_success:
            raise Exception("Failed to set test value in cache")

        # Test get operation
        retrieved_value = cache_manager.get(test_key)
        if retrieved_value != test_value:
            raise Exception("Retrieved value doesn't match set value")

        # Test delete operation
        delete_success = cache_manager.delete(test_key)

        # Check Redis vs Memory cache
        cache_type = "redis" if cache_manager.redis_cache else "memory"

        result = {
            "status": "healthy",
            "cache_type": cache_type,
            "redis_available": cache_manager.redis_cache is not None,
            "set_success": set_success,
            "get_success": retrieved_value == test_value,
            "delete_success": delete_success,
            "config": {
                "redis_host": config.get("REDIS_HOST"),
                "redis_port": config.get("REDIS_PORT"),
                "redis_db": config.get("REDIS_DB"),
                "redis_prefix": config.get("REDIS_PREFIX"),
                "redis_ttl": config.get("REDIS_TTL"),
            },
        }

        # Add detailed metrics if requested
        if detailed:
            try:
                health_metrics = cache_optimizer.get_cache_health()
                result["detailed"] = health_metrics
            except Exception as detail_error:
                logger.warning(
                    f"Failed to get detailed health metrics: {str(detail_error)}"
                )
                result["detailed"] = {"error": "Detailed metrics unavailable"}

        return result

    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Cache health check failed: {str(e)}"
        )


@router.post("/clear")
async def clear_cache() -> Dict[str, str]:
    """Clear all cache entries (use with caution)."""

    try:
        success = cache_manager.clear()

        if success:
            logger.info("Cache cleared successfully")
            return {"status": "success", "message": "Cache cleared successfully"}
        else:
            raise Exception("Failed to clear cache")

    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/stats")
async def cache_stats() -> Dict[str, Any]:
    """Get cache statistics and configuration."""

    try:
        cache_type = "redis" if cache_manager.redis_cache else "memory"

        stats = {
            "cache_type": cache_type,
            "redis_available": cache_manager.redis_cache is not None,
            "configuration": {
                "redis_host": config.get("REDIS_HOST"),
                "redis_port": config.get("REDIS_PORT"),
                "redis_db": config.get("REDIS_DB"),
                "redis_prefix": config.get("REDIS_PREFIX"),
                "default_ttl": config.get("REDIS_TTL"),
            },
        }

        # Add Redis-specific stats if available
        if cache_manager.redis_cache:
            try:
                redis_info = cache_manager.redis_cache.redis.info()
                stats["redis_info"] = {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "N/A"),
                    "total_commands_processed": redis_info.get(
                        "total_commands_processed", 0
                    ),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0),
                }

                # Calculate hit rate
                hits = redis_info.get("keyspace_hits", 0)
                misses = redis_info.get("keyspace_misses", 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                stats["redis_info"]["hit_rate_percent"] = round(hit_rate, 2)

            except Exception as e:
                logger.warning(f"Failed to get Redis info: {str(e)}")
                stats["redis_info"] = {"error": "Failed to retrieve Redis info"}

        return stats

    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/key/{cache_key}")
async def delete_cache_key(cache_key: str) -> Dict[str, Any]:
    """Delete a specific cache key."""

    try:
        success = cache_manager.delete(cache_key)

        return {
            "status": "success" if success else "not_found",
            "message": (
                f"Key '{cache_key}' deleted"
                if success
                else f"Key '{cache_key}' not found"
            ),
            "deleted": success,
        }

    except Exception as e:
        logger.error(f"Failed to delete cache key {cache_key}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete cache key: {str(e)}"
        )


@router.get("/performance-test")
async def cache_performance_test(iterations: int = 100) -> Dict[str, Any]:
    """Run a performance test on the cache system."""

    if iterations > 1000:
        raise ValidationError("iterations", "Maximum 1000 iterations allowed")

    try:
        results = {
            "iterations": iterations,
            "cache_type": "redis" if cache_manager.redis_cache else "memory",
        }

        # Test SET performance
        set_times = []
        for i in range(iterations):
            start_time = time.time()
            cache_manager.set(
                f"perf_test_{i}", {"iteration": i, "data": f"test_data_{i}"}, ttl=300
            )
            set_times.append((time.time() - start_time) * 1000)  # Convert to ms

        results["set_performance"] = {
            "avg_ms": round(sum(set_times) / len(set_times), 3),
            "min_ms": round(min(set_times), 3),
            "max_ms": round(max(set_times), 3),
        }

        # Test GET performance
        get_times = []
        for i in range(iterations):
            start_time = time.time()
            cache_manager.get(f"perf_test_{i}")
            get_times.append((time.time() - start_time) * 1000)  # Convert to ms

        results["get_performance"] = {
            "avg_ms": round(sum(get_times) / len(get_times), 3),
            "min_ms": round(min(get_times), 3),
            "max_ms": round(max(get_times), 3),
        }

        # Clean up test keys
        for i in range(iterations):
            cache_manager.delete(f"perf_test_{i}")

        return results

    except Exception as e:
        logger.error(f"Cache performance test failed: {sanitize_error_message(e)}")
        raise DatabaseError("cache performance test")


@router.get("/metrics")
async def get_cache_metrics(prefix: Optional[str] = None) -> Dict[str, Any]:
    """
    Get cache performance metrics.

    Args:
        prefix: Optional prefix to filter metrics

    Returns:
        Cache performance metrics
    """
    try:
        metrics = cache_optimizer.get_metrics(prefix)
        return {
            "status": "success",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {sanitize_error_message(e)}")
        raise DatabaseError("get cache metrics")


@router.post("/metrics/reset")
async def reset_cache_metrics(prefix: Optional[str] = None) -> Dict[str, str]:
    """
    Reset cache performance metrics.

    Args:
        prefix: Optional prefix to reset (resets all if None)

    Returns:
        Success message
    """
    try:
        cache_optimizer.reset_metrics(prefix)
        message = f"Metrics reset for {prefix}" if prefix else "All metrics reset"
        return {"status": "success", "message": message}
    except Exception as e:
        logger.error(f"Failed to reset metrics: {sanitize_error_message(e)}")
        raise DatabaseError("reset cache metrics")


# Deprecated: Use GET /cache/health?detailed=true instead
# @router.get("/health/detailed")
# Removed to consolidate health endpoints


@router.post("/invalidate/{pattern}")
async def invalidate_cache_pattern(pattern: str) -> Dict[str, Any]:
    """
    Invalidate all cache keys matching pattern.

    Args:
        pattern: Pattern to match (supports * wildcard)

    Returns:
        Number of keys invalidated
    """
    try:
        count = cache_optimizer.invalidate_pattern(pattern)
        return {
            "status": "success",
            "pattern": pattern,
            "invalidated_count": count,
            "message": f"Invalidated {count} keys matching {pattern}",
        }
    except Exception as e:
        logger.error(
            f"Failed to invalidate pattern {pattern}: {sanitize_error_message(e)}"
        )
        raise DatabaseError("invalidate cache pattern")
