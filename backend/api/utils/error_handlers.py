"""
Standardized error handling for API endpoints.

Provides consistent error responses, proper HTTP status codes, and secure error logging
that prevents sensitive data leakage.
"""

import logging
from typing import Any, Dict, Optional

from api.utils.config import config
from api.utils.security import sanitize_error_message
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors with standardized structure."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize API error.

        Args:
            message: User-friendly error message
            status_code: HTTP status code
            error_code: Application-specific error code (e.g., "DATA_NOT_FOUND")
            details: Additional error details (sanitized before sending)
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self._get_default_error_code(status_code)
        self.details = details or {}
        super().__init__(self.message)

    @staticmethod
    def _get_default_error_code(status_code: int) -> str:
        """Get default error code based on status code."""
        error_codes = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }
        return error_codes.get(status_code, "UNKNOWN_ERROR")

    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        response = {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
        }

        if include_details and self.details:
            response["details"] = self.details

        return response


# Specific error classes for common scenarios
class DataNotFoundError(APIError):
    """Raised when requested data is not found."""

    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="DATA_NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class ValidationError(APIError):
    """Raised when input validation fails."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"Validation failed for {field}: {reason}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details={"field": field, "reason": reason},
        )


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(APIError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
        )


class ExternalServiceError(APIError):
    """Raised when external service call fails."""

    def __init__(self, service: str, operation: str):
        super().__init__(
            message=f"External service error: {service}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "operation": operation},
        )


class DatabaseError(APIError):
    """Raised when database operation fails."""

    def __init__(self, operation: str, reason: Optional[str] = None):
        message = f"Database error during {operation}"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details={"operation": operation},
        )


class CacheError(APIError):
    """Raised when cache operation fails (non-critical)."""

    def __init__(self, operation: str):
        super().__init__(
            message=f"Cache operation failed: {operation}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
            details={"operation": operation},
        )


class InsufficientDataError(APIError):
    """Raised when insufficient data for analysis."""

    def __init__(self, required: int, available: int):
        super().__init__(
            message=f"Insufficient data: need {required}, have {available}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INSUFFICIENT_DATA",
            details={"required": required, "available": available},
        )


def handle_api_error(error: APIError, request: Request) -> JSONResponse:
    """
    Handle APIError and return standardized JSON response.

    Args:
        error: APIError instance
        request: FastAPI request object

    Returns:
        JSONResponse with error details
    """
    # Log error with sanitized message
    log_message = sanitize_error_message(error)
    logger.error(
        f"API Error: {error.error_code} - {log_message} "
        f"[{request.method} {request.url.path}]"
    )

    # Include details only in debug mode
    include_details = config.get("API_DEBUG", False)

    return JSONResponse(
        status_code=error.status_code,
        content=error.to_dict(include_details=include_details),
    )


def handle_http_exception(exc: HTTPException, request: Request) -> JSONResponse:
    """
    Handle FastAPI HTTPException and return standardized JSON response.

    Args:
        exc: HTTPException instance
        request: FastAPI request object

    Returns:
        JSONResponse with error details
    """
    # Sanitize detail message
    detail = sanitize_error_message(Exception(exc.detail))

    # Log error
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {detail} "
        f"[{request.method} {request.url.path}]"
    )

    # Convert to standardized format
    api_error = APIError(message=str(detail), status_code=exc.status_code)

    return JSONResponse(
        status_code=exc.status_code,
        content=api_error.to_dict(include_details=config.get("API_DEBUG", False)),
    )


def handle_validation_error(
    exc: RequestValidationError, request: Request
) -> JSONResponse:
    """
    Handle Pydantic validation errors and return standardized JSON response.

    Args:
        exc: RequestValidationError instance
        request: FastAPI request object

    Returns:
        JSONResponse with validation error details
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    # Log validation error
    logger.warning(
        f"Validation Error: {len(errors)} field(s) failed validation "
        f"[{request.method} {request.url.path}]"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "status_code": 422,
            "errors": errors,
        },
    )


def handle_generic_exception(exc: Exception, request: Request) -> JSONResponse:
    """
    Handle unexpected exceptions and return safe error response.

    Args:
        exc: Exception instance
        request: FastAPI request object

    Returns:
        JSONResponse with safe error message
    """
    # Log error with sanitized message
    sanitized_msg = sanitize_error_message(exc)
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {sanitized_msg} "
        f"[{request.method} {request.url.path}]",
        exc_info=True,  # Include stack trace in logs
    )

    # Return safe error response (no internal details exposed)
    if config.get("API_DEBUG", False):
        # In debug mode, include exception details
        message = f"{type(exc).__name__}: {sanitized_msg}"
    else:
        # In production, generic message
        message = "An internal error occurred. Please try again later."

    api_error = APIError(
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
    )

    return JSONResponse(
        status_code=500,
        content=api_error.to_dict(include_details=config.get("API_DEBUG", False)),
    )


# Exception handler decorators for FastAPI
def register_error_handlers(app):
    """
    Register all error handlers with FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return handle_api_error(exc, request)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return handle_http_exception(exc, request)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ):
        return handle_http_exception(
            HTTPException(status_code=exc.status_code, detail=exc.detail), request
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return handle_validation_error(exc, request)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return handle_generic_exception(exc, request)

    logger.info("Registered standardized error handlers")
