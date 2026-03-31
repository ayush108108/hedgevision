"""
Rate limiting middleware for API endpoints.

Implements token bucket algorithm with Redis backend for distributed rate limiting.
"""

import logging
import time
from typing import Optional, Tuple

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiter:
    """
    Token bucket rate limiter using Redis.

    Supports multiple rate limit tiers and endpoints.
    """

    def __init__(
        self,
        redis_client,
        default_requests: int = 100,
        default_window: int = 60,
        prefix: str = "rate_limit",
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            default_requests: Default number of requests allowed
            default_window: Default time window in seconds
            prefix: Redis key prefix
        """
        self.redis = redis_client
        self.default_requests = default_requests
        self.default_window = default_window
        self.prefix = prefix

    def _get_key(self, identifier: str, endpoint: str = "global") -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.prefix}:{endpoint}:{identifier}"

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the request.

        Priority:
        1. User ID from authentication (if available)
        2. API key (if provided)
        3. Client IP address
        """
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Try to get API key from headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            # Hash the API key for privacy
            import hashlib

            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"apikey:{key_hash}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str = "global",
        requests: Optional[int] = None,
        window: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier for the client
            endpoint: API endpoint being accessed
            requests: Number of requests allowed (uses default if None)
            window: Time window in seconds (uses default if None)

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        if not self.redis:
            # Rate limiting disabled if Redis unavailable
            return True, -1, 0

        requests = requests or self.default_requests
        window = window or self.default_window

        key = self._get_key(identifier, endpoint)

        try:
            # Use Redis pipeline for atomicity
            pipe = self.redis.pipeline()

            # Get current count
            pipe.get(key)

            # Execute pipeline
            results = pipe.execute()
            current_count = int(results[0]) if results[0] else 0

            if current_count >= requests:
                # Rate limit exceeded
                ttl = self.redis.ttl(key)
                retry_after = max(ttl, window)
                return False, 0, retry_after

            # Increment counter
            pipe = self.redis.pipeline()
            pipe.incr(key)

            # Set expiry if this is the first request in the window
            if current_count == 0:
                pipe.expire(key, window)

            pipe.execute()

            remaining = requests - (current_count + 1)
            return True, remaining, 0

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting system fails
            return True, -1, 0

    async def check_request(
        self,
        request: Request,
        requests: Optional[int] = None,
        window: Optional[int] = None,
    ) -> None:
        """
        Check if request should be allowed (raises exception if not).

        Args:
            request: FastAPI request object
            requests: Number of requests allowed
            window: Time window in seconds

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        identifier = self._get_identifier(request)
        endpoint = request.url.path

        is_allowed, remaining, retry_after = self.check_rate_limit(
            identifier, endpoint, requests, window
        )

        # Add rate limit headers to response
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = requests or self.default_requests

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {endpoint}. "
                f"Retry after {retry_after}s"
            )
            raise RateLimitExceeded(retry_after=retry_after)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API endpoints.
    """

    def __init__(self, app, rate_limiter: RateLimiter, enabled: bool = True):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.enabled = enabled

        # Exempt certain endpoints from rate limiting
        self.exempt_paths = {
            "/health",
            "/ready",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""

        # Skip rate limiting if disabled or for exempt paths
        if not self.enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        # Apply different rate limits based on endpoint
        requests, window = self._get_endpoint_limits(request.url.path)

        try:
            # Check rate limit
            await self.rate_limiter.check_request(request, requests, window)

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            if hasattr(request.state, "rate_limit_remaining"):
                response.headers["X-RateLimit-Limit"] = str(
                    request.state.rate_limit_limit
                )
                response.headers["X-RateLimit-Remaining"] = str(
                    request.state.rate_limit_remaining
                )
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)

            return response

        except RateLimitExceeded as e:
            # Return rate limit error response
            return JSONResponse(
                status_code=e.status_code, content=e.detail, headers=e.headers
            )

    def _get_endpoint_limits(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit configuration for specific endpoint.

        Args:
            path: Request path

        Returns:
            Tuple of (requests_allowed, window_seconds)
        """
        # Expensive computational endpoints - stricter limits
        if any(
            substr in path for substr in ["/cointegration", "/backtest", "/screener"]
        ):
            return 20, 60  # 20 requests per minute

        # Data fetching endpoints - moderate limits
        if any(
            substr in path for substr in ["/correlation", "/pair-analysis", "/data"]
        ):
            return 60, 60  # 60 requests per minute

        # Cache and lightweight endpoints - generous limits
        if "/cache" in path or "/websocket" in path or "/ws" in path:
            return 300, 60  # 300 requests per minute

        # Default rate limit
        return 100, 60  # 100 requests per minute


def get_rate_limiter(redis_client, enabled: bool = True) -> RateLimiter:
    """
    Factory function to create rate limiter instance.

    Args:
        redis_client: Redis client instance
        enabled: Whether rate limiting should be enabled

    Returns:
        RateLimiter instance
    """
    if not enabled or not redis_client:
        logger.warning(
            "Rate limiting disabled - Redis unavailable or disabled in config"
        )

    return RateLimiter(
        redis_client=redis_client if enabled else None,
        default_requests=100,
        default_window=60,
        prefix="statarb:rate_limit",
    )


# Decorator for route-specific rate limiting
def rate_limit(requests: int, window: int = 60):
    """
    Decorator for applying custom rate limits to specific routes.

    Args:
        requests: Number of requests allowed
        window: Time window in seconds

    Example:
        @app.get("/expensive-endpoint")
        @rate_limit(requests=10, window=60)
        async def expensive_operation():
            pass
    """

    def decorator(func):
        func._rate_limit_requests = requests
        func._rate_limit_window = window
        return func

    return decorator
