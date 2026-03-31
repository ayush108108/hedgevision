"""
Security utilities for API key protection and sanitization.

This module provides utilities to prevent API key leakage in logs, errors,
and responses. All sensitive data should be sanitized before logging or
returning to clients.
"""

import logging
import re
from functools import wraps
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)

# Patterns for sensitive keys
SENSITIVE_KEY_PATTERNS = [
    r"api[_-]?key",
    r"secret",
    r"token",
    r"password",
    r"auth",
    r"credential",
    r"private[_-]?key",
    r"access[_-]?key",
    r"supabase[_-]?key",
    r"jwt",
]

# Compile regex patterns for performance
SENSITIVE_REGEX = re.compile("|".join(SENSITIVE_KEY_PATTERNS), re.IGNORECASE)


def sanitize_dict(data: Dict[str, Any], mask: str = "***REDACTED***") -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary by masking sensitive values.

    Args:
        data: Dictionary to sanitize
        mask: String to use for masking sensitive values

    Returns:
        Sanitized dictionary copy

    Example:
        >>> sanitize_dict({"api_key": "secret123", "name": "test"})
        {"api_key": "***REDACTED***", "name": "test"}
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Check if key matches sensitive pattern
        if SENSITIVE_REGEX.search(str(key)):
            sanitized[key] = mask
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, mask)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                sanitize_dict(item, mask) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_url(url: str) -> str:
    """
    Remove API keys from URLs.

    Args:
        url: URL string that may contain API keys in query params

    Returns:
        URL with API keys masked

    Example:
        >>> sanitize_url("https://api.example.com/data?apikey=secret123")
        "https://api.example.com/data?apikey=***REDACTED***"
    """
    # Mask API keys in query parameters
    url = re.sub(
        r"([?&])(apikey|api_key|token|key|auth)=([^&]+)",
        r"\1\2=***REDACTED***",
        url,
        flags=re.IGNORECASE,
    )
    return url


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to prevent API key leakage.

    Args:
        error: Exception object

    Returns:
        Sanitized error message
    """
    message = str(error)

    # Look for patterns like "key=XXX" or "api_key: XXX"
    message = re.sub(
        r'(key|token|secret|password|auth)[\s:=]+[\'"]?[\w-]{10,}[\'"]?',
        r"\1=***REDACTED***",
        message,
        flags=re.IGNORECASE,
    )

    # Sanitize URLs in error messages
    message = sanitize_url(message)

    return message


def safe_log_dict(
    logger_instance: logging.Logger, level: int, message: str, data: Dict[str, Any]
) -> None:
    """
    Safely log a dictionary with sensitive data sanitized.

    Args:
        logger_instance: Logger instance to use
        level: Logging level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        data: Dictionary to log (will be sanitized)

    Example:
        >>> safe_log_dict(logger, logging.INFO, "Config loaded", {"api_key": "secret", "debug": True})
        # Logs: "Config loaded: {'api_key': '***REDACTED***', 'debug': True}"
    """
    sanitized = sanitize_dict(data)
    logger_instance.log(level, f"{message}: {sanitized}")


def mask_api_key(key: Union[str, None], visible_chars: int = 4) -> str:
    """
    Mask an API key, showing only the first few characters.

    Args:
        key: API key to mask
        visible_chars: Number of characters to show at the start

    Returns:
        Masked key string

    Example:
        >>> mask_api_key("sk_test_ExampleKey1234567890ab")
        "sk_t...***"
    """
    if not key:
        return "None"

    if len(key) <= visible_chars:
        return "***"

    return f"{key[:visible_chars]}...***"


def validate_api_keys_configured() -> Dict[str, bool]:
    """
    Validate which API keys are configured without exposing their values.

    Returns:
        Dictionary of provider names to boolean (configured or not)
    """
    from api.utils.config import config

    providers = {
        "Supabase": (
            config.get("DATA_BACKEND") == "sqlite"
            or bool(config.get("SUPABASE_URL") and config.get("SUPABASE_KEY"))
        ),
        "Tiingo": bool(config.get("TIINGO_API_KEY")),
        "Binance": bool(config.get("BINANCE_API_KEY")),
        "Polygon": bool(config.get("POLYGON_API_KEY")),
        "Finnhub": bool(config.get("FINNHUB_API_KEY")),
        "FMP": bool(config.get("FMP_API_KEY")),
        "EODHD": bool(config.get("EODHD_API_KEY")),
        "AlphaVantage": bool(config.get("ALPHA_VANTAGE_API_KEY")),
    }

    return providers


def safe_error_response(
    error: Exception, include_details: bool = False
) -> Dict[str, Any]:
    """
    Create a safe error response that doesn't leak sensitive information.

    Args:
        error: Exception that occurred
        include_details: Whether to include error details (should be False in production)

    Returns:
        Dictionary suitable for JSON response
    """
    response = {
        "error": True,
        "error_type": type(error).__name__,
        "message": "An error occurred while processing your request.",
    }

    if include_details:
        # Sanitize error message before including
        response["details"] = sanitize_error_message(error)

    return response


def secure_headers() -> Dict[str, str]:
    """
    Generate security headers for HTTP responses.

    Returns:
        Dictionary of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }


def sanitized_config_display() -> Dict[str, Any]:
    """
    Get a sanitized version of configuration for display/debugging.

    Returns:
        Sanitized configuration dictionary
    """
    from api.utils.config import config

    display_config = {
        # Server settings
        "api_host": config.get("API_HOST"),
        "api_port": config.get("API_PORT"),
        "api_debug": config.get("API_DEBUG"),
        # Database
        "data_backend": config.get("DATA_BACKEND"),
        "use_sqlite": config.get("USE_SQLITE_DB"),
        "use_supabase": config.get("USE_SUPABASE_DB"),
        "supabase_url": config.get("SUPABASE_URL"),
        "supabase_key_configured": bool(config.get("SUPABASE_KEY")),
        # Redis
        "redis_host": config.get("REDIS_HOST"),
        "redis_port": config.get("REDIS_PORT"),
        "redis_db": config.get("REDIS_DB"),
        # API Keys (masked)
        "api_keys": {
            provider: "configured" if configured else "not_configured"
            for provider, configured in validate_api_keys_configured().items()
        },
        # Settings
        "cors_origins": config.get("CORS_ORIGINS"),
        "data_quality_min_threshold": config.get("DATA_QUALITY_MIN_THRESHOLD"),
        "computation_enabled": config.get("COMPUTATION_ENABLED"),
        "enable_external_llm": config.get("ENABLE_EXTERNAL_LLM"),
        "local_ml_backend": config.get("LOCAL_ML_BACKEND"),
        "local_ml_model_path_configured": bool(config.get("LOCAL_ML_MODEL_PATH")),
        "broker_backend": config.get("BROKER_BACKEND"),
        "ccxt_exchange": config.get("CCXT_EXCHANGE"),
    }

    return display_config


# Decorator for sanitizing function arguments in logs
def sanitize_logs(func):
    """
    Decorator to sanitize function arguments before logging.

    Example:
        @sanitize_logs
        def fetch_data(api_key: str, symbol: str):
            # If this function logs its arguments, api_key will be masked
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Log function call with sanitized arguments
            sanitized_kwargs = sanitize_dict(kwargs) if kwargs else {}
            logger.debug(
                f"Calling {func.__name__} with args={len(args)}, kwargs={sanitized_kwargs}"
            )
            return func(*args, **kwargs)
        except Exception as e:
            # Log error with sanitized message
            logger.error(f"Error in {func.__name__}: {sanitize_error_message(e)}")
            raise

    return wrapper


# Environment variable validation
def validate_required_env_vars() -> Dict[str, bool]:
    """
    Validate required environment variables are set.

    Returns:
        Dictionary of variable names to validation status
    """
    import os
    from api.utils.config import config

    use_supabase = config.get("DATA_BACKEND") == "supabase"
    required_vars = {
        "REDIS_HOST": bool(os.getenv("REDIS_HOST", "localhost")),  # Has default
    }
    if use_supabase:
        required_vars["SUPABASE_URL"] = bool(os.getenv("SUPABASE_URL"))
        required_vars["SUPABASE_KEY"] = bool(
            os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        )

    # Log missing variables (but not their values)
    missing = [var for var, present in required_vars.items() if not present]
    if missing:
        logger.warning(f"Missing required environment variables: {', '.join(missing)}")

    return required_vars


# Rate limiting helper
def create_rate_limit_key(identifier: str, endpoint: str) -> str:
    """
    Create a Redis key for rate limiting.

    Args:
        identifier: User identifier (IP, user_id, etc.)
        endpoint: API endpoint being accessed

    Returns:
        Redis key string
    """
    # Sanitize identifier to prevent injection
    safe_identifier = re.sub(r"[^a-zA-Z0-9_-]", "_", identifier)
    safe_endpoint = re.sub(r"[^a-zA-Z0-9_/-]", "_", endpoint)

    return f"rate_limit:{safe_endpoint}:{safe_identifier}"
