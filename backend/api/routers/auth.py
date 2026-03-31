"""
Authentication router for user registration, login, and profile management.
"""

import logging
from typing import Any, Dict

from api.services.auth_service import (
    AuthResponse,
    UserLogin,
    UserProfile,
    UserRegistration,
    UserUpdateProfile,
    get_auth_service,
)
from api.utils.auth_middleware import (
    AuthUser,
    get_authenticated_user,
    get_current_user,
    rate_limit_auth,
)
from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)]
)
async def register_user(registration: UserRegistration) -> AuthResponse:
    """Register a new user account."""

    auth_service = get_auth_service()
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        auth_response = await auth_service.register_user(registration)
        logger.info(f"User registered successfully: {registration.email}")
        return auth_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post(
    "/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)]
)
async def login_user(login: UserLogin) -> AuthResponse:
    """Authenticate user login."""

    auth_service = get_auth_service()
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        auth_response = await auth_service.login_user(login)
        logger.info(f"User logged in successfully: {login.email}")
        return auth_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(refresh_data: Dict[str, str]) -> AuthResponse:
    """Refresh user session token."""

    refresh_token = refresh_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required"
        )

    auth_service = get_auth_service()
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        auth_response = await auth_service.refresh_token(refresh_token)
        logger.info("Token refreshed successfully")
        return auth_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed"
        )


@router.post("/logout")
async def logout_user(
    current_user: AuthUser = Depends(get_authenticated_user),
) -> Dict[str, str]:
    """Logout current user."""

    auth_service = get_auth_service()
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        # Get access token from current user's token claims
        access_token = current_user.token_claims.get("access_token")

        success = await auth_service.logout_user(access_token)

        if success:
            logger.info(f"User logged out successfully: {current_user.email}")
            return {"message": "Logged out successfully"}
        else:
            return {"message": "Logout completed (session may have already expired)"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        # Don't fail logout even if there's an error
        return {"message": "Logout completed"}


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: AuthUser = Depends(get_authenticated_user),
) -> UserProfile:
    """Get current user's profile."""

    try:
        return current_user.profile

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile",
        )


@router.put("/me", response_model=UserProfile)
async def update_current_user_profile(
    updates: UserUpdateProfile, current_user: AuthUser = Depends(get_authenticated_user)
) -> UserProfile:
    """Update current user's profile."""

    auth_service = get_auth_service()
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    try:
        updated_profile = await auth_service.update_user_profile(
            current_user.user_id, updates
        )
        logger.info(f"Profile updated successfully: {current_user.email}")
        return updated_profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )


@router.get("/status")
async def auth_status(
    current_user: AuthUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get authentication status and user info."""

    if not current_user:
        return {"authenticated": False, "user": None, "subscription_tier": "anonymous"}

    return {
        "authenticated": True,
        "user": {
            "id": current_user.user_id,
            "email": current_user.email,
            "full_name": current_user.profile.full_name,
            "subscription_tier": current_user.profile.subscription_tier,
        },
        "subscription_tier": current_user.profile.subscription_tier,
        "permissions": {
            "view_correlations": current_user.has_permission("view_correlations"),
            "view_pair_analysis": current_user.has_permission("view_pair_analysis"),
            "run_basic_backtests": current_user.has_permission("run_basic_backtests"),
            "view_screener": current_user.has_permission("view_screener"),
            "advanced_backtests": current_user.has_permission("advanced_backtests"),
            "export_data": current_user.has_permission("export_data"),
            "api_access": current_user.has_permission("api_access"),
        },
    }


@router.get("/check")
async def check_auth_service() -> Dict[str, Any]:
    """Check authentication service health."""

    auth_service = get_auth_service()

    return {
        "service_available": auth_service is not None,
        "supabase_configured": auth_service is not None,
        "features": {
            "registration": True,
            "login": True,
            "profile_management": True,
            "rate_limiting": True,
            "role_based_access": True,
        },
    }
