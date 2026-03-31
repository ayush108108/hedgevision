"""
Base API client with common functionality for rate limiting, session management, and error handling.
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Base rate limit configuration."""

    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    max_retries: int = 5
    base_delay: float = 1.0

    def get_delay_seconds(self) -> float:
        """Calculate minimum delay between requests."""
        delays = []
        if self.requests_per_minute:
            delays.append(60.0 / self.requests_per_minute)
        if self.requests_per_hour:
            delays.append(3600.0 / self.requests_per_hour)
        if self.requests_per_day:
            delays.append(86400.0 / self.requests_per_day)
        return max(delays) if delays else self.base_delay


class BaseAPIClient(ABC):
    """
    Abstract base class for API clients.

    Provides:
    - Session management
    - Rate limiting with exponential backoff
    - Retry logic with configurable attempts
    - Error handling and logging
    - Request/response tracking
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        rate_limit_config: Optional[RateLimitConfig] = None,
    ):
        """
        Initialize base API client.

        Args:
            api_key: API authentication key
            base_url: Base URL for API endpoints
            rate_limit_config: Rate limit configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = rate_limit_config or RateLimitConfig()

        # Rate limiting trackers
        self.last_request_time = 0.0
        self.minute_request_count = 0
        self.hour_request_count = 0
        self.day_request_count = 0
        self.minute_start_time = time.time()
        self.hour_start_time = time.time()
        self.day_start_time = time.time()

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _reset_rate_limit_counters(self):
        """Reset rate limit counters based on time windows."""
        current_time = time.time()

        # Reset minute counter
        if current_time - self.minute_start_time >= 60:
            self.minute_request_count = 0
            self.minute_start_time = current_time

        # Reset hour counter
        if current_time - self.hour_start_time >= 3600:
            self.hour_request_count = 0
            self.hour_start_time = current_time

        # Reset day counter
        if current_time - self.day_start_time >= 86400:
            self.day_request_count = 0
            self.day_start_time = current_time

    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits."""
        await self._reset_rate_limit_counters()

        # Calculate required delay
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_delay = self.rate_limit.get_delay_seconds()

        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            logger.debug(
                f"{self.__class__.__name__}: Rate limit wait {sleep_time:.2f}s"
            )
            await asyncio.sleep(sleep_time)

    def _increment_request_counters(self):
        """Increment all request counters."""
        self.minute_request_count += 1
        self.hour_request_count += 1
        self.day_request_count += 1
        self.last_request_time = time.time()

    async def _rate_limited_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Make rate-limited HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or path (relative to base_url)
            params: Query parameters
            data: Request body data
            headers: Request headers
            retry_count: Current retry attempt

        Returns:
            JSON response data

        Raises:
            Exception: If all retries exhausted
        """
        await self._ensure_session()
        await self._wait_for_rate_limit()

        # Build full URL if relative path provided
        if not url.startswith("http"):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

        # Add authentication
        params = params or {}
        headers = headers or {}
        params = self._add_auth_params(params)
        headers = self._add_auth_headers(headers)

        try:
            async with self.session.request(
                method=method, url=url, params=params, json=data, headers=headers
            ) as response:
                self._increment_request_counters()

                if response.status == 200:
                    return await response.json()

                elif response.status == 429:  # Rate limit exceeded
                    if retry_count < self.rate_limit.max_retries:
                        delay = self.rate_limit.base_delay * (2**retry_count)
                        logger.warning(
                            f"{self.__class__.__name__}: Rate limited (429), "
                            f"retrying in {delay}s (attempt {retry_count + 1}/{self.rate_limit.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        return await self._rate_limited_request(
                            method, url, params, data, headers, retry_count + 1
                        )
                    else:
                        raise Exception(
                            f"Rate limit exceeded after {self.rate_limit.max_retries} retries"
                        )

                elif response.status >= 500:  # Server error
                    if retry_count < self.rate_limit.max_retries:
                        delay = self.rate_limit.base_delay * (2**retry_count)
                        logger.warning(
                            f"{self.__class__.__name__}: Server error ({response.status}), "
                            f"retrying in {delay}s (attempt {retry_count + 1}/{self.rate_limit.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        return await self._rate_limited_request(
                            method, url, params, data, headers, retry_count + 1
                        )
                    else:
                        raise Exception(
                            f"Server error {response.status} after {self.rate_limit.max_retries} retries"
                        )

                else:  # Client error (4xx)
                    error_text = await response.text()
                    raise Exception(
                        f"{self.__class__.__name__}: HTTP {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            if retry_count < self.rate_limit.max_retries:
                delay = self.rate_limit.base_delay * (2**retry_count)
                logger.warning(
                    f"{self.__class__.__name__}: Network error, "
                    f"retrying in {delay}s (attempt {retry_count + 1}/{self.rate_limit.max_retries}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._rate_limited_request(
                    method, url, params, data, headers, retry_count + 1
                )
            else:
                raise Exception(
                    f"Network error after {self.rate_limit.max_retries} retries: {e}"
                )

    @abstractmethod
    def _add_auth_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add authentication to query parameters.
        Override in subclass if API key goes in params.
        """
        return params

    @abstractmethod
    def _add_auth_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Add authentication to headers.
        Override in subclass if API key goes in headers.
        """
        return headers

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info(f"{self.__class__.__name__}: Session closed")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            "minute_count": self.minute_request_count,
            "hour_count": self.hour_request_count,
            "day_count": self.day_request_count,
            "last_request": self.last_request_time,
            "limits": {
                "per_minute": self.rate_limit.requests_per_minute,
                "per_hour": self.rate_limit.requests_per_hour,
                "per_day": self.rate_limit.requests_per_day,
            },
        }
