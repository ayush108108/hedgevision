"""
Compatibility adapter that mimics Flask-Caching's interface using the
project's CacheManager implementation.

Many business_calculations helpers expect an object that exposes a
``memoize`` decorator. Those functions were originally written for the
legacy Flask/Dash stack. This adapter lets the FastAPI backend share the same
logic without rewriting it by delegating to ``CacheManager`` for storage.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from api.utils.cache import CacheManager, get_cache_manager


class CacheAdapter:
    """Lightweight adapter that provides a Flask-like ``memoize`` decorator."""

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        default_ttl: int = 3600,
    ) -> None:
        self._cache_manager = cache_manager or get_cache_manager()
        self._default_ttl = default_ttl

    def memoize(
        self, timeout: Optional[int] = None
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Return a decorator that caches function results for ``timeout`` seconds."""

        ttl = timeout if timeout is not None else self._default_ttl

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            cache_key_prefix = f"{func.__module__}:{func.__qualname__}"

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Build a deterministic cache key using repr to keep things simple.
                cache_key = self._cache_manager.get_cache_key(
                    cache_key_prefix,
                    repr(args),
                    repr(sorted(kwargs.items(), key=lambda item: item[0])),
                )

                cached_value = self._cache_manager.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = func(*args, **kwargs)
                self._cache_manager.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator


def get_cache_adapter(default_ttl: int = 3600) -> CacheAdapter:
    """Convenience helper used by routers to obtain a shared adapter instance."""

    return CacheAdapter(get_cache_manager(), default_ttl=default_ttl)
