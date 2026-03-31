"""
Authentication service using Supabase Auth.

This module provides authentication functionality including user registration,
login, profile management, and session handling.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import jwt
from api.utils.config import config
from fastapi import HTTPException, status
from jwt import PyJWKClient
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)

try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available. Install with: pip install supabase")


class UserProfile(BaseModel):
    """User profile model."""

    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: str = "free"
    preferences: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class UserRegistration(BaseModel):
    """User registration request model."""

    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request model."""

    email: EmailStr
    password: str


class UserUpdateProfile(BaseModel):
    """User profile update model."""

    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class AuthResponse(BaseModel):
    """Authentication response model."""

    access_token: str
    refresh_token: str
    user: UserProfile
    expires_in: int


class AuthService:
    """Authentication service using Supabase Auth."""

    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client not available")

        self.url = config.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
        self.key = config.get("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.service_key = config.get("SUPABASE_SERVICE_KEY") or os.getenv(
            "SUPABASE_SERVICE_KEY"
        )

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

        self.client: Client = create_client(self.url, self.key)

        # Service client for admin operations
        if self.service_key:
            self.service_client: Client = create_client(self.url, self.service_key)
        else:
            self.service_client = None
            logger.warning(
                "SUPABASE_SERVICE_KEY not set - admin operations unavailable"
            )

        # JWKS (JWT signing keys) setup for RS256 verification
        self.jwks_url = (
            config.get("SUPABASE_JWKS_URL")
            or os.getenv("SUPABASE_JWKS_URL")
            or (f"{self.url.rstrip('/')}/auth/v1/keys" if self.url else None)
        )
        self.jwks_client: Optional[PyJWKClient] = None
        if self.jwks_url:
            try:
                self.jwks_client = PyJWKClient(self.jwks_url)
                logger.info("AuthService initialized with JWKS verification")
            except Exception as e:
                logger.warning(f"Failed to initialize JWKS client: {e}")
        else:
            logger.info("AuthService initialized (no JWKS URL configured)")

    async def register_user(self, registration: UserRegistration) -> AuthResponse:
        """Register a new user."""
        try:
            # Register user with Supabase Auth
            auth_response = self.client.auth.sign_up(
                {
                    "email": registration.email,
                    "password": registration.password,
                    "options": {"data": {"full_name": registration.full_name}},
                }
            )

            if auth_response.user is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account",
                )

            # Create user profile
            profile_data = {
                "id": auth_response.user.id,
                "email": registration.email,
                "full_name": registration.full_name,
                "subscription_tier": "free",
                "preferences": {
                    "default_granularity": "daily",
                    "default_correlation_method": "spearman",
                    "default_min_correlation": 0.7,
                    "theme": "dark",
                    "notifications_enabled": True,
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Insert profile into profiles table
            profile_result = (
                self.client.table("user_profiles").insert(profile_data).execute()
            )

            if not profile_result.data:
                logger.error("Failed to create user profile")
                # Clean up auth user if profile creation fails
                if self.service_client:
                    self.service_client.auth.admin.delete_user(auth_response.user.id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user profile",
                )

            # Create user profile model
            user_profile = UserProfile(**profile_result.data[0])

            logger.info(f"User registered successfully: {registration.email}")

            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=user_profile,
                expires_in=auth_response.session.expires_in or 3600,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed",
            )

    async def login_user(self, login: UserLogin) -> AuthResponse:
        """Authenticate user login."""
        try:
            # Authenticate with Supabase
            auth_response = self.client.auth.sign_in_with_password(
                {"email": login.email, "password": login.password}
            )

            if auth_response.user is None or auth_response.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )

            # Get user profile
            profile_result = (
                self.client.table("user_profiles")
                .select("*")
                .eq("id", auth_response.user.id)
                .single()
                .execute()
            )

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            user_profile = UserProfile(**profile_result.data)

            logger.info(f"User logged in successfully: {login.email}")

            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=user_profile,
                expires_in=auth_response.session.expires_in or 3600,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
            )

    async def refresh_token(self, refresh_token: str) -> AuthResponse:
        """Refresh user session token."""
        try:
            auth_response = self.client.auth.refresh_session(refresh_token)

            if auth_response.user is None or auth_response.session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            # Get updated user profile
            profile_result = (
                self.client.table("user_profiles")
                .select("*")
                .eq("id", auth_response.user.id)
                .single()
                .execute()
            )

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            user_profile = UserProfile(**profile_result.data)

            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                user=user_profile,
                expires_in=auth_response.session.expires_in or 3600,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed"
            )

    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Get user profile by ID."""
        try:
            profile_result = (
                self.client.table("user_profiles")
                .select("*")
                .eq("id", user_id)
                .single()
                .execute()
            )

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            return UserProfile(**profile_result.data)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get user profile error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user profile",
            )

    async def update_user_profile(
        self, user_id: str, updates: UserUpdateProfile
    ) -> UserProfile:
        """Update user profile."""
        try:
            update_data = updates.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow().isoformat()

            profile_result = (
                self.client.table("user_profiles")
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )

            if not profile_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User profile not found",
                )

            logger.info(f"User profile updated: {user_id}")

            return UserProfile(**profile_result.data[0])

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Update user profile error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile",
            )

    async def logout_user(self, access_token: str) -> bool:
        """Logout user and invalidate session."""
        try:
            # Set the session
            self.client.auth.set_session(access_token, None)

            # Sign out
            self.client.auth.sign_out()

            logger.info("User logged out successfully")
            return True

        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return False

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user claims.

        Supports RS256 verification using JWKS (recommended), with HS256 fallback
        using SUPABASE_JWT_SECRET for backward compatibility.
        """
        # 1) Try RS256 with JWKS (new method)
        if self.jwks_client and self.url:
            try:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
                issuer = f"{self.url.rstrip('/')}/auth/v1"
                payload = jwt.decode(
                    token,
                    signing_key,
                    algorithms=["RS256"],
                    options={"verify_aud": False},
                    issuer=issuer,
                )
                return payload
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
                )
            except jwt.InvalidTokenError as e:
                # If RS256 fails, try HS256 fallback next
                logger.debug(f"RS256 verification failed: {e}")
            except Exception as e:
                logger.debug(f"JWKS verification error: {e}")
                # Continue to HS256 fallback

        # 2) HS256 fallback with SUPABASE_JWT_SECRET (legacy)
        try:
            jwt_secret = config.get("SUPABASE_JWT_SECRET") or os.getenv(
                "SUPABASE_JWT_SECRET"
            )
            if not jwt_secret:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="JWT verification failed (no JWKS or secret configured)",
                )
            payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed",
            )


# Global auth service instance
_auth_service = None


def get_auth_service() -> Optional[AuthService]:
    """Get the global auth service instance."""
    global _auth_service

    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase not available for authentication")
        return None

    if _auth_service is None:
        try:
            _auth_service = AuthService()
        except Exception as e:
            logger.error(f"Failed to initialize auth service: {str(e)}")
            return None

    return _auth_service
