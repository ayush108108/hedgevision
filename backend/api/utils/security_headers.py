"""
Security headers middleware.

Adds security headers to all HTTP responses to protect against common vulnerabilities.
"""

from api.utils.config import config
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # XSS protection (legacy, but still good to include)
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (disable unused features)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
        }

        # Add HSTS only in production (HTTPS)
        if not config.get("API_DEBUG", False):
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy (adjust based on your needs)
        # This is a basic policy - customize for your application
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Needed for docs
            "style-src 'self' 'unsafe-inline'",  # Needed for docs
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
        ]
        security_headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Apply headers
        for header, value in security_headers.items():
            response.headers[header] = value

        return response
