"""
Redis caching utilities for API responses.

This module provides utilities for caching API responses in Redis,
with fallback to an in-memory cache when Redis is not available.
"""

import hashlib
import logging
import pickle
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, cast

# Configure logging
logger = logging.getLogger(__name__)

try:
    import importlib.util

    REDIS_AVAILABLE = importlib.util.find_spec("redis") is not None
except Exception:
    REDIS_AVAILABLE = False
if not REDIS_AVAILABLE:
    logger.warning("Redis not available. Using in-memory cache instead.")

# In-memory cache as fallback
MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}


class CacheBackend:
    """Interface for cache backends."""

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in the cache with optional TTL in seconds."""
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        raise NotImplementedError

    def clear(self) -> bool:
        """Clear all values from the cache."""
        raise NotImplementedError


class RedisCache(CacheBackend):
    """Redis cache backend."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        prefix: str = "api:",
        client: Optional[Any] = None,
        connect_timeout_seconds: float = 1.0,
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host.
            port: Redis port.
            db: Redis database number.
            prefix: Key prefix.
        """
        # Allow passing a pre-configured Redis client (e.g., from a URL)
        if client is not None:
            self.redis = client
        else:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis library not available and no client provided")
            # Import locally to satisfy static analyzers
            import redis as _redis

            self.redis = _redis.Redis(
                host=host,
                port=port,
                db=db,
                socket_connect_timeout=connect_timeout_seconds,
                socket_timeout=connect_timeout_seconds,
            )
        self.prefix = prefix
        logger.info(f"Initialized Redis cache with host={host}, port={port}, db={db}")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        try:
            value = self.redis.get(f"{self.prefix}{key}")
            if value:
                # redis-py returns bytes; cast for type-checkers
                return pickle.loads(cast(bytes, value))  # type: ignore[arg-type]
            return None
        except Exception as e:
            logger.warning("Error getting from Redis: %s", str(e))
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in Redis with TTL in seconds."""
        try:
            res = self.redis.setex(
                f"{self.prefix}{key}", ttl, pickle.dumps(value)
            )
            return bool(res)
        except Exception as e:
            logger.warning("Error setting in Redis: %s", str(e))
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from Redis."""
        try:
            return bool(self.redis.delete(f"{self.prefix}{key}"))
        except Exception as e:
            logger.warning("Error deleting from Redis: %s", str(e))
            return False

    def clear(self) -> bool:
        """Clear all values with prefix from Redis."""
        try:
            keys = list(self.redis.keys(f"{self.prefix}*"))  # type: ignore
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.warning("Error clearing Redis: %s", str(e))
            return False


class MemoryCache(CacheBackend):
    """In-memory cache backend."""

    def __init__(self, prefix: str = "api:"):
        """
        Initialize memory cache.

        Args:
            prefix: Key prefix.
        """
        self.prefix = prefix
        self.cache: Dict[str, Dict[str, Any]] = {}
        logger.info("Initialized in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from memory."""
        prefixed_key = f"{self.prefix}{key}"
        if prefixed_key in self.cache:
            entry = self.cache[prefixed_key]
            # Check if entry has expired
            if "expiry" in entry and entry["expiry"] < datetime.now():
                del self.cache[prefixed_key]
                return None
            return entry["value"]
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in memory with TTL in seconds."""
        prefixed_key = f"{self.prefix}{key}"
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.cache[prefixed_key] = {"value": value, "expiry": expiry}
        return True

    def delete(self, key: str) -> bool:
        """Delete a value from memory."""
        prefixed_key = f"{self.prefix}{key}"
        if prefixed_key in self.cache:
            del self.cache[prefixed_key]
            return True
        return False

    def clear(self) -> bool:
        """Clear all values with prefix from memory."""
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(self.prefix)]
        for key in keys_to_delete:
            del self.cache[key]
        return True


class CacheManager:
    """
    Cache manager with Redis and in-memory backend.

    This class provides a unified interface to Redis and in-memory caching,
    with automatic fallback to in-memory cache when Redis is not available.
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        prefix: str = "api:",
        connect_timeout_seconds: float = 1.0,
    ):
        """
        Initialize cache manager.

        Args:
            redis_host: Redis host.
            redis_port: Redis port.
            redis_db: Redis database number.
            prefix: Key prefix.
        """
        self.prefix = prefix
        self.memory_cache = MemoryCache(prefix)

        # Try to initialize Redis cache if available
        self.redis_cache = None
        if REDIS_AVAILABLE:
            try:
                # Prefer REDIS_URL if provided (supports rediss:// for TLS like Upstash)
                import os

                redis_url = os.getenv("REDIS_URL")
                if redis_url:
                    # Import locally to ensure binding
                    import redis as _redis

                    client = _redis.from_url(
                        redis_url,
                        socket_connect_timeout=connect_timeout_seconds,
                        socket_timeout=connect_timeout_seconds,
                    )
                    self.redis_cache = RedisCache(prefix=prefix, client=client)
                    logger.info("Initialized Redis client from REDIS_URL")
                else:
                    self.redis_cache = RedisCache(
                        redis_host,
                        redis_port,
                        redis_db,
                        prefix,
                        connect_timeout_seconds=connect_timeout_seconds,
                    )
                # Test connection
                self.redis_cache.set("test", "test")
                result = self.redis_cache.get("test")
                if result != "test":
                    raise Exception("Redis connection test failed")
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {str(e)}. Using in-memory cache only."
                )
                self.redis_cache = None

        # Use memory cache as fallback if Redis is not available
        self.primary_cache = self.redis_cache or self.memory_cache

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        return self.primary_cache.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in cache with TTL in seconds."""
        return self.primary_cache.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        return self.primary_cache.delete(key)

    def clear(self) -> bool:
        """Clear all values from cache."""
        return self.primary_cache.clear()

    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        # Convert args and kwargs to a string
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "::".join(key_parts)

        # Hash the string to get a shorter key
        return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Cache decorator for functions.

    Args:
        ttl: Time-to-live in seconds.
        key_prefix: Prefix for cache keys.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_mgr = get_cache_manager()

            # Generate a cache key
            func_name = func.__name__
            cache_key = (
                f"{key_prefix}:{func_name}:{cache_mgr.get_cache_key(*args, **kwargs)}"
            )

            # Try to get from cache
            cached_value = cache_mgr.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value

            # Call the function
            logger.debug(f"Cache miss for {cache_key}")
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time

            # Cache the result
            cache_mgr.set(cache_key, result, ttl)
            logger.debug(f"Cached {cache_key} with TTL {ttl}s (took {elapsed:.3f}s)")

            return result

        return wrapper

    return decorator


# Global cache manager instance
_cache_manager = None


def get_cache_manager(
    redis_host: Optional[str] = None,
    redis_port: Optional[int] = None,
    redis_db: Optional[int] = None,
    prefix: Optional[str] = None,
) -> CacheManager:
    """
    Get the global cache manager instance.

    Args:
        redis_host: Redis host.
        redis_port: Redis port.
        redis_db: Redis database number.
        prefix: Key prefix.

    Returns:
        Cache manager instance.
    """
    global _cache_manager
    if _cache_manager is None:
        # Import config here to avoid circular imports
        from .config import config

        # Use provided values or fall back to config
        host = redis_host or config.get("REDIS_HOST", "localhost")
        port = redis_port or config.get("REDIS_PORT", 6379)
        db = redis_db or config.get("REDIS_DB", 0)
        prefix_val = prefix or config.get("REDIS_PREFIX", "statarb:api:")
        connect_timeout = float(config.get("REDIS_CONNECT_TIMEOUT_SECONDS", 1.0))

        _cache_manager = CacheManager(
            host,
            port,
            db,
            prefix_val,
            connect_timeout_seconds=connect_timeout,
        )
    return _cache_manager
