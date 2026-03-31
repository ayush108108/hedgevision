"""
Authentication middleware and dependencies for FastAPI.

This module provides authentication middleware, dependency injection for protected routes,
and utilities for handling user sessions.
"""

import logging
from typing import Any, Dict, Optional

from api.services.auth_service import UserProfile, get_auth_service
from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


class AuthUser:
    """Authenticated user context."""

    def __init__(
        self,
        user_id: str,
        email: str,
        profile: UserProfile,
        token_claims: Dict[str, Any],
    ):
        self.user_id = user_id
        self.email = email
        self.profile = profile
        self.token_claims = token_claims
        self.is_authenticated = True

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Basic role-based permissions
        if self.profile.subscription_tier == "pro":
            return True
        elif self.profile.subscription_tier == "free":
            free_permissions = [
                "view_correlations",
                "view_pair_analysis",
                "run_basic_backtests",
                "view_screener",
            ]
            return permission in free_permissions

        return False

    def is_premium_user(self) -> bool:
        """Check if user has premium subscription."""
        return self.profile.subscription_tier in ["pro", "enterprise"]


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """
    Get current authenticated user from JWT token.
    Returns None if no token provided (for optional authentication).
    """
    if not credentials:
        return None

    auth_service = get_auth_service()
    if not auth_service:
        logger.warning("Auth service not available")
        return None

    try:
        # Verify token and get claims
        token_claims = auth_service.verify_token(credentials.credentials)
        user_id = token_claims.get("sub")

        if not user_id:
            return None

        # Get user profile
        user_profile = await auth_service.get_user_profile(user_id)

        return AuthUser(
            user_id=user_id,
            email=user_profile.email,
            profile=user_profile,
            token_claims=token_claims,
        )

    except HTTPException:
        # Token is invalid, but we're not raising an error for optional auth
        return None
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return None


async def get_authenticated_user(
    current_user: Optional[AuthUser] = Depends(get_current_user),
) -> AuthUser:
    """
    Get current authenticated user (required).
    Raises 401 if user is not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


async def get_premium_user(
    current_user: AuthUser = Depends(get_authenticated_user),
) -> AuthUser:
    """
    Get current authenticated premium user.
    Raises 403 if user doesn't have premium subscription.
    """
    if not current_user.is_premium_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required",
        )

    return current_user


def require_permission(permission: str):
    """
    Dependency factory for requiring specific permissions.

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: AuthUser = Depends(require_permission("admin_access"))):
            pass
    """

    async def permission_dependency(
        current_user: AuthUser = Depends(get_authenticated_user),
    ) -> AuthUser:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user

    return permission_dependency


class RateLimiter:
    """Simple in-memory rate limiter for authentication endpoints."""

    def __init__(self):
        self.requests = {}

    def is_allowed(
        self, key: str, max_requests: int = 5, window_minutes: int = 15
    ) -> bool:
        """Check if request is allowed within rate limit."""
        import time

        now = time.time()
        window_start = now - (window_minutes * 60)

        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]
        else:
            self.requests[key] = []

        # Check if under limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """Rate limiting dependency for authentication endpoints."""
    client_ip = get_client_ip(request)

    if not rate_limiter.is_allowed(
        f"auth:{client_ip}", max_requests=10, window_minutes=15
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )


class AuthMiddleware:
    """Authentication middleware for FastAPI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add user context to request state if authenticated
        request = Request(scope, receive)

        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                auth_service = get_auth_service()

                if auth_service:
                    token_claims = auth_service.verify_token(token)
                    user_id = token_claims.get("sub")

                    if user_id:
                        user_profile = await auth_service.get_user_profile(user_id)
                        scope["state"]["user"] = AuthUser(
                            user_id=user_id,
                            email=user_profile.email,
                            profile=user_profile,
                            token_claims=token_claims,
                        )
        except Exception as e:
            logger.debug(f"Auth middleware error: {str(e)}")
            # Continue without authentication

        await self.app(scope, receive, send)
