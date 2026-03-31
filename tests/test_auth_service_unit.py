"""
Unit tests for AuthService authentication and authorization functionality.

This test module covers:
- User registration and login workflows
- Token generation, verification, and refresh
- JWT token operations (RS256 and HS256)
- User profile management
- Error handling for authentication failures
- Session management and logout

All tests use mocked Supabase clients to avoid external dependencies.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import jwt
import pytest
from api.services.auth_service import (
    AuthResponse,
    AuthService,
    UserLogin,
    UserProfile,
    UserRegistration,
    UserUpdateProfile,
    get_auth_service,
)
from fastapi import HTTPException


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for authentication."""
    client = MagicMock()
    
    # Mock auth operations
    client.auth = MagicMock()
    client.auth.sign_up = MagicMock()
    client.auth.sign_in_with_password = MagicMock()
    client.auth.refresh_session = MagicMock()
    client.auth.sign_out = MagicMock()
    client.auth.set_session = MagicMock()
    client.auth.admin = MagicMock()
    client.auth.admin.delete_user = MagicMock()
    
    # Mock table operations
    client.table = MagicMock()
    
    return client


@pytest.fixture
def mock_jwks_client():
    """Mock PyJWKClient for RS256 JWT verification."""
    client = MagicMock()
    signing_key = MagicMock()
    signing_key.key = "mock-signing-key"
    client.get_signing_key_from_jwt = MagicMock(return_value=signing_key)
    return client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "full_name": "Test User",
        "avatar_url": None,
        "subscription_tier": "free",
        "preferences": {
            "default_granularity": "daily",
            "theme": "dark",
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_auth_response():
    """Sample Supabase auth response."""
    mock_response = MagicMock()
    mock_response.user = MagicMock()
    mock_response.user.id = "user-123"
    mock_response.session = MagicMock()
    mock_response.session.access_token = "mock-access-token"
    mock_response.session.refresh_token = "mock-refresh-token"
    mock_response.session.expires_in = 3600
    return mock_response


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
@patch("api.services.auth_service.create_client")
class TestAuthServiceUserRegistration:
    """Test user registration functionality."""

    async def test_register_user_successful(self, mock_create_client, mock_supabase_client, sample_user_data, sample_auth_response):
        """Test successful user registration creates auth user and profile."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful auth sign up
        mock_supabase_client.auth.sign_up.return_value = sample_auth_response
        
        # Mock successful profile creation
        profile_result = MagicMock()
        profile_result.data = [sample_user_data]
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        registration = UserRegistration(
            email="test@example.com",
            password="SecurePass123!",
            full_name="Test User"
        )
        
        result = await auth_service.register_user(registration)
        
        # Verify auth sign up called
        mock_supabase_client.auth.sign_up.assert_called_once()
        call_args = mock_supabase_client.auth.sign_up.call_args[0][0]
        assert call_args["email"] == "test@example.com"
        assert call_args["password"] == "SecurePass123!"
        
        # Verify profile creation
        mock_supabase_client.table.assert_called_with("user_profiles")
        
        # Verify response
        assert isinstance(result, AuthResponse)
        assert result.access_token == "mock-access-token"
        assert result.refresh_token == "mock-refresh-token"
        assert result.user.email == "test@example.com"
        assert result.expires_in == 3600

    async def test_register_user_auth_failure(self, mock_create_client, mock_supabase_client):
        """Test registration fails when Supabase auth returns None user."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock failed auth response
        mock_auth_response = MagicMock()
        mock_auth_response.user = None
        mock_supabase_client.auth.sign_up.return_value = mock_auth_response
        
        auth_service = AuthService()
        registration = UserRegistration(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(registration)
        
        assert exc_info.value.status_code == 400
        assert "Failed to create user account" in exc_info.value.detail

    async def test_register_user_profile_creation_failure(self, mock_create_client, mock_supabase_client, sample_auth_response):
        """Test registration cleans up auth user if profile creation fails."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful auth
        mock_supabase_client.auth.sign_up.return_value = sample_auth_response
        
        # Mock failed profile creation
        profile_result = MagicMock()
        profile_result.data = []
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        auth_service.service_client = mock_supabase_client  # Enable cleanup
        
        registration = UserRegistration(email="test@example.com", password="SecurePass123!")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(registration)
        
        # Verify cleanup called
        mock_supabase_client.auth.admin.delete_user.assert_called_once_with("user-123")
        assert exc_info.value.status_code == 500


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
@patch("api.services.auth_service.create_client")
class TestAuthServiceUserLogin:
    """Test user login functionality."""

    async def test_login_user_successful(self, mock_create_client, mock_supabase_client, sample_user_data, sample_auth_response):
        """Test successful user login returns access token and profile."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful login
        mock_supabase_client.auth.sign_in_with_password.return_value = sample_auth_response
        
        # Mock profile retrieval
        profile_result = MagicMock()
        profile_result.data = sample_user_data
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        login = UserLogin(email="test@example.com", password="SecurePass123!")
        
        result = await auth_service.login_user(login)
        
        # Verify auth called
        mock_supabase_client.auth.sign_in_with_password.assert_called_once()
        
        # Verify response
        assert isinstance(result, AuthResponse)
        assert result.access_token == "mock-access-token"
        assert result.user.email == "test@example.com"

    async def test_login_user_invalid_credentials(self, mock_create_client, mock_supabase_client):
        """Test login fails with invalid credentials."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock failed auth
        mock_auth_response = MagicMock()
        mock_auth_response.user = None
        mock_auth_response.session = None
        mock_supabase_client.auth.sign_in_with_password.return_value = mock_auth_response
        
        auth_service = AuthService()
        login = UserLogin(email="test@example.com", password="WrongPassword")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user(login)
        
        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail

    async def test_login_user_profile_not_found(self, mock_create_client, mock_supabase_client, sample_auth_response):
        """Test login fails if user profile doesn't exist."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful auth but missing profile
        mock_supabase_client.auth.sign_in_with_password.return_value = sample_auth_response
        
        profile_result = MagicMock()
        profile_result.data = None
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        login = UserLogin(email="test@example.com", password="SecurePass123!")
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user(login)
        
        assert exc_info.value.status_code == 404
        assert "User profile not found" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
@patch("api.services.auth_service.create_client")
class TestAuthServiceTokenOperations:
    """Test token refresh and verification."""

    async def test_refresh_token_successful(self, mock_create_client, mock_supabase_client, sample_user_data, sample_auth_response):
        """Test successful token refresh returns new tokens."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful refresh
        mock_supabase_client.auth.refresh_session.return_value = sample_auth_response
        
        # Mock profile retrieval
        profile_result = MagicMock()
        profile_result.data = sample_user_data
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        result = await auth_service.refresh_token("old-refresh-token")
        
        # Verify refresh called
        mock_supabase_client.auth.refresh_session.assert_called_once_with("old-refresh-token")
        
        # Verify new tokens returned
        assert result.access_token == "mock-access-token"
        assert result.refresh_token == "mock-refresh-token"

    async def test_refresh_token_invalid(self, mock_create_client, mock_supabase_client):
        """Test refresh fails with invalid token."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock failed refresh
        mock_auth_response = MagicMock()
        mock_auth_response.user = None
        mock_auth_response.session = None
        mock_supabase_client.auth.refresh_session.return_value = mock_auth_response
        
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_token("invalid-token")
        
        assert exc_info.value.status_code == 401
        assert "Invalid refresh token" in exc_info.value.detail

    @patch("api.services.auth_service.jwt.decode")
    def test_verify_token_rs256_with_jwks(self, mock_jwt_decode, mock_create_client, mock_supabase_client, mock_jwks_client):
        """Test RS256 token verification using JWKS."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock JWT decode success
        expected_payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        mock_jwt_decode.return_value = expected_payload
        
        with patch("api.services.auth_service.PyJWKClient", return_value=mock_jwks_client):
            auth_service = AuthService()
            result = auth_service.verify_token("valid-jwt-token")
        
        # Verify JWT decode called with RS256
        mock_jwt_decode.assert_called_once()
        assert result == expected_payload

    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    @patch("api.services.auth_service.jwt.decode")
    def test_verify_token_hs256_fallback(self, mock_jwt_decode, mock_create_client, mock_supabase_client):
        """Test HS256 token verification fallback when JWKS unavailable."""
        mock_create_client.return_value = mock_supabase_client
        
        expected_payload = {"sub": "user-123", "email": "test@example.com"}
        
        # Only HS256 decode is called (no JWKS client)
        mock_jwt_decode.return_value = expected_payload
        
        auth_service = AuthService()
        auth_service.jwks_client = None  # Disable JWKS
        
        result = auth_service.verify_token("valid-jwt-token")
        
        # Verify HS256 was used
        assert result == expected_payload
        mock_jwt_decode.assert_called_once()

    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    @patch("api.services.auth_service.jwt.decode")
    def test_verify_token_expired(self, mock_jwt_decode, mock_create_client, mock_supabase_client):
        """Test token verification fails with expired token in HS256 fallback."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock ExpiredSignatureError from jwt.decode
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError("Token expired")
        
        auth_service = AuthService()
        auth_service.jwks_client = None  # Disable JWKS
        
        with pytest.raises(HTTPException) as exc_info:
            auth_service.verify_token("expired-token")
        
        assert exc_info.value.status_code == 401
        assert "Token has expired" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
@patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
@patch("api.services.auth_service.create_client")
class TestAuthServiceProfileManagement:
    """Test user profile operations."""

    async def test_get_user_profile_successful(self, mock_create_client, mock_supabase_client, sample_user_data):
        """Test retrieving user profile by ID."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock profile retrieval
        profile_result = MagicMock()
        profile_result.data = sample_user_data
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        result = await auth_service.get_user_profile("user-123")
        
        assert isinstance(result, UserProfile)
        assert result.id == "user-123"
        assert result.email == "test@example.com"

    async def test_get_user_profile_not_found(self, mock_create_client, mock_supabase_client):
        """Test get profile fails when user doesn't exist."""
        mock_create_client.return_value = mock_supabase_client
        
        profile_result = MagicMock()
        profile_result.data = None
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.get_user_profile("nonexistent-user")
        
        assert exc_info.value.status_code == 404
        assert "User profile not found" in exc_info.value.detail

    async def test_update_user_profile_successful(self, mock_create_client, mock_supabase_client, sample_user_data):
        """Test updating user profile fields."""
        mock_create_client.return_value = mock_supabase_client
        
        # Mock successful update
        updated_data = sample_user_data.copy()
        updated_data["full_name"] = "Updated Name"
        profile_result = MagicMock()
        profile_result.data = [updated_data]
        mock_supabase_client.table.return_value.update.return_value.eq.return_value.execute.return_value = profile_result
        
        auth_service = AuthService()
        updates = UserUpdateProfile(full_name="Updated Name")
        
        result = await auth_service.update_user_profile("user-123", updates)
        
        # Verify update called
        mock_supabase_client.table.assert_called_with("user_profiles")
        
        assert result.full_name == "Updated Name"

    async def test_logout_user_successful(self, mock_create_client, mock_supabase_client):
        """Test user logout invalidates session."""
        mock_create_client.return_value = mock_supabase_client
        
        auth_service = AuthService()
        result = await auth_service.logout_user("access-token")
        
        # Verify session set and sign out called
        mock_supabase_client.auth.set_session.assert_called_once_with("access-token", None)
        mock_supabase_client.auth.sign_out.assert_called_once()
        assert result is True


@pytest.mark.unit
@patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "test-key"})
@patch("api.services.auth_service.create_client")
def test_get_auth_service_singleton(mock_create_client):
    """Test get_auth_service returns singleton instance."""
    mock_create_client.return_value = MagicMock()
    
    # Clear global instance
    import api.services.auth_service
    api.services.auth_service._auth_service = None
    
    # Get service twice
    service1 = get_auth_service()
    service2 = get_auth_service()
    
    # Should return same instance
    assert service1 is service2
    assert service1 is not None


@pytest.mark.unit
def test_auth_service_initialization_missing_credentials():
    """Test AuthService initialization fails without credentials."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            AuthService()
        
        assert "SUPABASE_URL and SUPABASE_ANON_KEY must be set" in str(exc_info.value)
