"""
Data Cache Manager - Track what data has been fetched to avoid redundant API calls.

Uses Redis for caching metadata about fetched data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)


class DataCacheManager:
    """
    Manages cache metadata for fetched financial data.

    Tracks:
    - Last fetch timestamp for each symbol/provider combination
    - Date range coverage for EOD data
    - Latest intraday candle timestamp
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize cache manager.

        Args:
            redis_client: Redis client instance (creates new if None)
        """
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis client from environment or defaults
            import os

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis = redis.from_url(redis_url, decode_responses=True)

        self.key_prefix = "statarb:data_cache:"

    def _make_key(self, *parts: str) -> str:
        """Create Redis key from parts."""
        return self.key_prefix + ":".join(parts)

    # EOD Data Cache Methods

    def get_eod_coverage(self, symbol: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get EOD data coverage information for a symbol.

        Args:
            symbol: Asset symbol
            provider: Data provider name

        Returns:
            Dictionary with coverage info or None
        """
        key = self._make_key("eod", provider, symbol)
        data = self.redis.get(key)

        if not data:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in cache for {key}")
            return None

    def set_eod_coverage(
        self,
        symbol: str,
        provider: str,
        start_date: datetime,
        end_date: datetime,
        record_count: int,
    ):
        """
        Record EOD data coverage for a symbol.

        Args:
            symbol: Asset symbol
            provider: Data provider name
            start_date: Start of coverage
            end_date: End of coverage
            record_count: Number of records fetched
        """
        key = self._make_key("eod", provider, symbol)

        coverage = {
            "symbol": symbol,
            "provider": provider,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "record_count": record_count,
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Store with 24 hour expiry
        self.redis.setex(key, 86400, json.dumps(coverage))
        logger.debug(f"Cached EOD coverage for {symbol} ({provider})")

    def is_eod_fresh(self, symbol: str, provider: str, max_age_hours: int = 24) -> bool:
        """
        Check if EOD data is fresh (recently fetched).

        Args:
            symbol: Asset symbol
            provider: Data provider name
            max_age_hours: Maximum age in hours to consider fresh

        Returns:
            True if data is fresh
        """
        coverage = self.get_eod_coverage(symbol, provider)

        if not coverage:
            return False

        try:
            last_updated = datetime.fromisoformat(coverage["last_updated"])
            age = datetime.utcnow() - last_updated

            is_fresh = age < timedelta(hours=max_age_hours)

            if is_fresh:
                logger.debug(
                    f"EOD data for {symbol} ({provider}) is fresh ({age.total_seconds()/3600:.1f}h old)"
                )
            else:
                logger.debug(
                    f"EOD data for {symbol} ({provider}) is stale ({age.total_seconds()/3600:.1f}h old)"
                )

            return is_fresh

        except (KeyError, ValueError) as e:
            logger.error(f"Error checking EOD freshness for {symbol}: {e}")
            return False

    def get_missing_eod_dates(
        self,
        symbol: str,
        provider: str,
        required_start: datetime,
        required_end: datetime,
    ) -> Optional[tuple]:
        """
        Determine what EOD date range is missing (needs to be fetched).

        Args:
            symbol: Asset symbol
            provider: Data provider name
            required_start: Start date needed
            required_end: End date needed

        Returns:
            Tuple of (fetch_start, fetch_end) or None if all data is available
        """
        coverage = self.get_eod_coverage(symbol, provider)

        if not coverage:
            # No coverage - need to fetch full range
            return (required_start, required_end)

        try:
            covered_start = datetime.fromisoformat(coverage["start_date"])
            covered_end = datetime.fromisoformat(coverage["end_date"])

            # Check if we need new data
            if required_start >= covered_start and required_end <= covered_end:
                # Fully covered
                logger.debug(f"EOD data for {symbol} ({provider}) is fully covered")
                return None

            # Calculate missing range
            fetch_start = (
                required_start if required_start < covered_start else covered_end
            )
            fetch_end = required_end

            logger.debug(
                f"EOD data for {symbol} ({provider}) needs update: "
                f"{fetch_start.date()} to {fetch_end.date()}"
            )

            return (fetch_start, fetch_end)

        except (KeyError, ValueError) as e:
            logger.error(f"Error calculating missing dates for {symbol}: {e}")
            return (required_start, required_end)

    # Intraday Data Cache Methods

    def get_latest_intraday_timestamp(
        self, symbol: str, provider: str
    ) -> Optional[datetime]:
        """
        Get timestamp of latest intraday candle fetched.

        Args:
            symbol: Asset symbol
            provider: Data provider name

        Returns:
            Datetime of latest candle or None
        """
        key = self._make_key("intraday", provider, symbol)
        data = self.redis.get(key)

        if not data:
            return None

        try:
            info = json.loads(data)
            return datetime.fromisoformat(info["latest_timestamp"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error reading intraday cache for {symbol}: {e}")
            return None

    def set_latest_intraday_timestamp(
        self, symbol: str, provider: str, candle_timestamp: datetime
    ):
        """
        Record latest intraday candle timestamp.

        Args:
            symbol: Asset symbol
            provider: Data provider name
            candle_timestamp: Timestamp of the candle
        """
        key = self._make_key("intraday", provider, symbol)

        info = {
            "symbol": symbol,
            "provider": provider,
            "latest_timestamp": candle_timestamp.isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Store with 4 hour expiry (since candles are 4h)
        self.redis.setex(key, 14400, json.dumps(info))
        logger.debug(f"Cached intraday timestamp for {symbol} ({provider})")

    def should_fetch_intraday(
        self, symbol: str, provider: str, min_interval_hours: int = 4
    ) -> bool:
        """
        Check if we should fetch new intraday candle.

        Args:
            symbol: Asset symbol
            provider: Data provider name
            min_interval_hours: Minimum hours between fetches

        Returns:
            True if should fetch new data
        """
        latest = self.get_latest_intraday_timestamp(symbol, provider)

        if not latest:
            # No previous fetch - should fetch
            return True

        age = datetime.utcnow() - latest
        should_fetch = age >= timedelta(hours=min_interval_hours)

        if should_fetch:
            logger.debug(
                f"Should fetch intraday for {symbol} ({provider}) - {age.total_seconds()/3600:.1f}h old"
            )
        else:
            logger.debug(
                f"Skip intraday fetch for {symbol} ({provider}) - only {age.total_seconds()/3600:.1f}h old"
            )

        return should_fetch

    # Provider Rate Limit Tracking

    def increment_provider_calls(self, provider: str, period: str = "minute") -> int:
        """
        Increment and get call count for provider in a time period.

        Args:
            provider: Provider name
            period: Time period ("minute", "hour", "day")

        Returns:
            Current call count for this period
        """
        key = self._make_key("calls", provider, period)

        # Use pipeline for atomic increment + TTL
        pipe = self.redis.pipeline()
        pipe.incr(key)

        # Set expiry based on period
        if period == "minute":
            pipe.expire(key, 60)
        elif period == "hour":
            pipe.expire(key, 3600)
        elif period == "day":
            pipe.expire(key, 86400)

        result = pipe.execute()
        call_count = result[0]

        return call_count

    def get_provider_calls(self, provider: str, period: str = "minute") -> int:
        """
        Get current call count for provider in a time period.

        Args:
            provider: Provider name
            period: Time period

        Returns:
            Current call count
        """
        key = self._make_key("calls", provider, period)
        count = self.redis.get(key)

        return int(count) if count else 0

    # Bulk Operations

    def get_all_eod_coverage(self) -> List[Dict[str, Any]]:
        """
        Get EOD coverage for all cached symbols.

        Returns:
            List of coverage dictionaries
        """
        pattern = self._make_key("eod", "*", "*")
        keys = self.redis.keys(pattern)

        coverage_list = []
        for key in keys:
            data = self.redis.get(key)
            if data:
                try:
                    coverage_list.append(json.loads(data))
                except json.JSONDecodeError:
                    continue

        return coverage_list

    def clear_cache(self, pattern: Optional[str] = None):
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Redis key pattern (default: all hedgevision cache)
        """
        if not pattern:
            pattern = self.key_prefix + "*"

        keys = self.redis.keys(pattern)

        if keys:
            self.redis.delete(*keys)
            logger.info(f"Cleared {len(keys)} cache entries matching {pattern}")
        else:
            logger.info(f"No cache entries found matching {pattern}")
