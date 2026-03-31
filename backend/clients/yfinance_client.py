"""
Yahoo Finance client using yfinance library.
Free, no API key required, supports all asset types.

Ticker Format Examples:
- US Stocks: AAPL, MSFT, TSLA
- US ETFs: SPY, QQQ, DIA
- Crypto: BTC-USD, ETH-USD, SOL-USD
- India NSE: NIFTYBEES.NS, RELIANCE.NS
- India BSE: SENSEX.BO
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import yfinance as yf
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class YFinanceConfig:
    """Configuration for yfinance client."""

    auto_adjust: bool = True  # Auto-adjust OHLC for splits/dividends
    repair: bool = True  # Attempt to repair Yahoo data errors
    keepna: bool = False  # Don't keep NaN rows
    timeout: int = 30  # Request timeout in seconds
    threads: bool = False  # Disable multi-threading for rate limiting
    delay_between_requests: float = 60.0  # default; can be overridden via env (we'll set 20s by default in get_yfinance_client)
    respect_server: bool = True  # Enable respectful server usage


class YFinanceClient:
    """
    Yahoo Finance client using yfinance library.

    Benefits:
    - Free, no API key required
    - No rate limits (reasonable use)
    - Supports stocks, ETFs, crypto, international markets
    - Auto-adjusted prices (splits & dividends)
    - Multiple intervals: 1d, 4h, 1h, etc.

    Limitations:
    - Unofficial API (can break without notice)
    - For personal/educational use only
    - Intraday data limited to last 60 days
    """

    def __init__(self, config: Optional[YFinanceConfig] = None):
        """
        Initialize Yahoo Finance client.

        Args:
            config: Optional configuration
        """
        self.config = config or YFinanceConfig()
        self.last_request_time = 0.0
        logger.info(
            f"Initialized Yahoo Finance client (no API key required) - "
            f"Rate limit: 1 request per {self.config.delay_between_requests}s"
        )

    def _convert_symbol_to_yfinance(self, symbol: str, asset_type: Optional[str] = None) -> str:
        """
        Convert HedgeVision symbol to Yahoo Finance format.

        Args:
            symbol: HedgeVision symbol
            asset_type: Asset type hint (stock, etf, crypto)

        Returns:
            Yahoo Finance compatible symbol
        """
        # Already in Yahoo format
        if any(suffix in symbol for suffix in [".NS", ".BO", "-USD"]):
            return symbol

        # Crypto: Add -USD suffix or convert .CC format
        if asset_type == "crypto" or ".CC" in symbol:
            # Handle BTC-USD.CC → BTC-USD
            if ".CC" in symbol:
                symbol = symbol.replace(".CC", "")
            # If doesn't end with -USD, add it
            if not symbol.endswith("-USD"):
                base = symbol.split("-")[0]  # Get base currency
                return f"{base}-USD"
            return symbol

        # India NSE: .NSE → .NS suffix
        if ".NSE" in symbol:
            return symbol.replace(".NSE", ".NS")

        # India BSE: .BO suffix
        if symbol.endswith(".BSE"):
            return symbol.replace(".BSE", ".BO")

        # US stocks/ETFs: Remove .US suffix
        if symbol.endswith(".US"):
            return symbol.replace(".US", "")

        # Default: return as-is
        return symbol

    def _yfinance_to_hedgevision_df(
        self, yf_df: pd.DataFrame, symbol: str
    ) -> pd.DataFrame:
        """
        Convert yfinance DataFrame to HedgeVision format.

        Args:
            yf_df: DataFrame from yfinance
            symbol: Original symbol

        Returns:
            DataFrame in HedgeVision format
        """
        if yf_df.empty:
            return pd.DataFrame()

        # yfinance returns index as DatetimeIndex
        df = yf_df.reset_index()
        
        # Flatten MultiIndex columns if present (happens with single-symbol downloads)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Standardize column names (case-insensitive)
        # Handle both string columns and tuple columns (multi-level index)
        df.columns = [
            col.lower() if isinstance(col, str) else str(col[0]).lower()
            for col in df.columns
        ]

        # Rename to HedgeVision standard
        column_mapping = {"date": "timestamp", "datetime": "timestamp"}
        df = df.rename(columns=column_mapping)

        # Ensure timestamp column exists
        if "timestamp" not in df.columns and df.index.name:
            df["timestamp"] = df.index
            df = df.reset_index(drop=True)

        # Ensure timestamp is in UTC timezone
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            if df["timestamp"].dt.tz is None:
                # If naive, assume it's already in UTC (yfinance often returns naive UTC)
                df["timestamp"] = df["timestamp"].dt.tz_localize('UTC')
            # If already timezone-aware, ensure it's UTC
            elif df["timestamp"].dt.tz != 'UTC':
                df["timestamp"] = df["timestamp"].dt.tz_convert('UTC')

        # yfinance auto-adjusts by default, so 'close' is already adjusted
        # Add adjusted_close column (same as close when auto_adjust=True)
        if "close" in df.columns and "adjusted_close" not in df.columns:
            df["adjusted_close"] = df["close"]

        # Add metadata
        df["source"] = "yfinance"
        df["data_quality"] = 1.0

        # Select and order columns
        required_cols = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
            "source",
            "data_quality",
        ]

        # Filter to only columns that exist
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]

        return df

    async def fetch_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
    asset_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance with rate limiting.

        Args:
            symbol: Stock/ETF/Crypto symbol
            start_date: Start date (or use period='max' for all history)
            end_date: End date
            interval: Data interval (1d, 4h, 1h, etc.)
            asset_type: Asset type hint for symbol conversion

        Returns:
            DataFrame with OHLCV data
        """
        # Apply rate limiting (1 request per minute by default)
        if self.config.respect_server:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.config.delay_between_requests:
                sleep_duration = self.config.delay_between_requests - time_since_last
                logger.info(
                    f"Rate limiting: waiting {sleep_duration:.1f}s before next request "
                    f"(respectful server usage)"
                )
                await asyncio.sleep(sleep_duration)

            self.last_request_time = asyncio.get_event_loop().time()

        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        logger.info(
            f"Fetching Yahoo Finance data for {yf_symbol} "
            f"from {start_date.date()} to {end_date.date()} "
            f"(interval: {interval})"
        )

        try:
            # Run yfinance in executor to avoid blocking
            loop = asyncio.get_event_loop()
            yf_df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    yf_symbol,
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=self.config.auto_adjust,
                    repair=self.config.repair,
                    keepna=self.config.keepna,
                    progress=False,  # Disable progress bar
                    timeout=self.config.timeout,
                ),
            )

            if yf_df.empty:
                logger.warning(f"No data returned for {yf_symbol}")
                return pd.DataFrame()

            # Convert to HedgeVision format
            df = self._yfinance_to_hedgevision_df(yf_df, symbol)

            logger.info(f"Fetched {len(df)} records for {yf_symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch data for {yf_symbol}: {e}")
            return pd.DataFrame()

    async def fetch_daily_eod(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    asset_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch daily EOD data.

        Args:
            symbol: Stock/ETF/Crypto symbol
            start_date: Start date
            end_date: End date
            asset_type: Asset type hint

        Returns:
            DataFrame with daily OHLCV data
        """
        return await self.fetch_historical_data(
            symbol, start_date, end_date, interval="1d", asset_type=asset_type
        )

    async def _fetch_with_period(
        self,
        symbol: str,
        period: str,
        interval: str = "1d",
        asset_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch data using period parameter.

        Args:
            symbol: Stock/ETF/Crypto symbol
            period: Period string like 'max', '1y'
            interval: Data interval
            asset_type: Asset type hint

        Returns:
            DataFrame with OHLCV data
        """
        # Apply rate limiting
        if self.config.respect_server:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.config.delay_between_requests:
                sleep_duration = self.config.delay_between_requests - time_since_last
                logger.info(
                    f"Rate limiting: waiting {sleep_duration:.1f}s before next request"
                )
                await asyncio.sleep(sleep_duration)

            self.last_request_time = asyncio.get_event_loop().time()

        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        logger.info(f"Fetching Yahoo Finance data for {yf_symbol} (period={period}, interval={interval})")

        try:
            # Run yfinance in executor
            loop = asyncio.get_event_loop()
            yf_df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    yf_symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=self.config.auto_adjust,
                    repair=self.config.repair,
                    keepna=self.config.keepna,
                    progress=False,
                    timeout=self.config.timeout,
                ),
            )

            if yf_df is None or yf_df.empty:
                logger.warning(f"No data returned for {yf_symbol}")
                return pd.DataFrame()

            # Convert to HedgeVision format
            df = self._yfinance_to_hedgevision_df(yf_df, symbol)

            logger.info(f"Fetched {len(df)} records for {yf_symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch data for {yf_symbol}: {e}")
            return pd.DataFrame()
        """
        Fetch ALL available daily historical data (maximum history).

        Uses period='max' to get all available data from Yahoo Finance.
        This can be decades of data for some assets.

        Args:
            symbol: Stock/ETF/Crypto symbol
            asset_type: Asset type hint

        Returns:
            DataFrame with all available daily OHLCV data
        """
        # Apply rate limiting
        if self.config.respect_server:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.config.delay_between_requests:
                sleep_duration = self.config.delay_between_requests - time_since_last
                logger.info(
                    f"Rate limiting: waiting {sleep_duration:.1f}s before next request"
                )
                await asyncio.sleep(sleep_duration)

            self.last_request_time = asyncio.get_event_loop().time()

        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        logger.info(f"Fetching ALL-TIME daily data for {yf_symbol} (period=max)")

        try:
            # Run yfinance in executor with period='max' for all history
            loop = asyncio.get_event_loop()
            yf_df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    yf_symbol,
                    period="max",  # Get ALL available history
                    interval="1d",
                    auto_adjust=self.config.auto_adjust,
                    repair=self.config.repair,
                    keepna=self.config.keepna,
                    progress=False,
                    timeout=self.config.timeout,
                ),
            )

            if yf_df.empty:
                logger.warning(f"No data returned for {yf_symbol}")
                return pd.DataFrame()

            # Convert to HedgeVision format
            df = self._yfinance_to_hedgevision_df(yf_df, symbol)

            if not df.empty:
                first_date = df["timestamp"].min().date()
                last_date = df["timestamp"].max().date()
                logger.info(
                    f"Fetched {len(df)} records for {yf_symbol} "
                    f"({first_date} to {last_date})"
                )

            return df

        except Exception as e:
            logger.error(f"Failed to fetch all-time data for {yf_symbol}: {e}")
            return pd.DataFrame()

    async def fetch_all_time_4hour(
    self, symbol: str, asset_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch ALL available 4-hour historical data.

        Note: For 4-hour data, we need to use 1-hour interval and aggregate.
        Yahoo Finance provides up to 730 days of 1-hour data.

        Args:
            symbol: Stock/ETF/Crypto symbol
            asset_type: Asset type hint

        Returns:
            DataFrame with 4-hour OHLCV data
        """
        # Apply rate limiting
        if self.config.respect_server:
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.config.delay_between_requests:
                sleep_duration = self.config.delay_between_requests - time_since_last
                logger.info(
                    f"Rate limiting: waiting {sleep_duration:.1f}s before next request"
                )
                await asyncio.sleep(sleep_duration)

            self.last_request_time = asyncio.get_event_loop().time()

        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        logger.info(f"Fetching ALL-TIME 1h data for {yf_symbol} (will aggregate to 4h)")

        try:
            # Fetch maximum 1-hour data (Yahoo provides up to 730 days)
            loop = asyncio.get_event_loop()
            yf_df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    yf_symbol,
                    period="730d",  # Maximum 730 days for 1h data
                    interval="1h",
                    auto_adjust=self.config.auto_adjust,
                    repair=self.config.repair,
                    keepna=self.config.keepna,
                    progress=False,
                    timeout=self.config.timeout,
                ),
            )

            if yf_df.empty:
                logger.warning(f"No 1h data returned for {yf_symbol}")
                return pd.DataFrame()

            # Convert to HedgeVision format
            df = self._yfinance_to_hedgevision_df(yf_df, symbol)

            if df.empty:
                return df

            # Aggregate 1h to 4h (6 data points per day)
            df_4h = self._aggregate_to_4hour(df)

            if not df_4h.empty:
                first_date = df_4h["timestamp"].min().date()
                last_date = df_4h["timestamp"].max().date()
                logger.info(
                    f"Fetched {len(df_4h)} 4h candles for {yf_symbol} "
                    f"({first_date} to {last_date})"
                )

            return df_4h

        except Exception as e:
            logger.error(f"Failed to fetch all-time 4h data for {yf_symbol}: {e}")
            return pd.DataFrame()

    async def fetch_4hour_intraday(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    asset_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch 4-hour intraday data.

        Note: Intraday data limited to last 60 days in Yahoo Finance.

        Args:
            symbol: Stock/ETF/Crypto symbol
            start_date: Start date/time
            end_date: End date/time
            asset_type: Asset type hint

        Returns:
            DataFrame with 4-hour OHLCV data
        """
        # Check if date range is within last 60 days
        days_ago = (datetime.now() - start_date).days
        if days_ago > 60:
            logger.warning(
                f"Intraday data requested for {days_ago} days ago. "
                f"Yahoo Finance limits intraday to last 60 days."
            )

        # Yahoo Finance doesn't have native 4h interval
        # Use 1h and aggregate manually, or use daily
        # For now, fetch 1h data
        df = await self.fetch_historical_data(
            symbol, start_date, end_date, interval="1h", asset_type=asset_type
        )

        if df.empty:
            return df

        # Aggregate 1h to 4h
        df = self._aggregate_to_4hour(df)

        return df

    def _aggregate_to_4hour(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate 1-hour data to 4-hour candles.

        Ensures proper timezone handling (UTC) and alignment to standard 4-hour boundaries:
        00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC

        Args:
            df: DataFrame with 1-hour data

        Returns:
            DataFrame with 4-hour candles
        """
        if df.empty:
            return df

        df = df.copy()

        # Ensure timestamp is datetime and in UTC timezone
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        if df["timestamp"].dt.tz is None:
            # If naive, assume UTC
            df["timestamp"] = df["timestamp"].dt.tz_localize('UTC')
        else:
            # Convert to UTC if in different timezone
            df["timestamp"] = df["timestamp"].dt.tz_convert('UTC')

        df = df.set_index("timestamp")

        # Resample to 4-hour intervals aligned to midnight UTC
        # origin='start' aligns to the start of the data
        # offset='0H' ensures we start at hour 0 (midnight)
        # closed='left' means [start, end) interval
        # label='left' means the label is the start of the interval
        agg_dict = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "adjusted_close": "last",
        }

        df_4h = df.resample(
            "4H",
            origin='start',
            offset='0H',
            closed='left',
            label='left'
        ).agg(agg_dict)

        df_4h = df_4h.dropna()
        df_4h = df_4h.reset_index()

        df_4h["source"] = "yfinance"
        df_4h["data_quality"] = 1.0

        logger.info(f"Aggregated to {len(df_4h)} 4-hour candles")

        return df_4h

    async def fetch_latest_4hour_candle(
    self, symbol: str, asset_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch only the most recent 4-hour candle.

        Args:
            symbol: Stock/ETF/Crypto symbol
            asset_type: Asset type hint

        Returns:
            Dictionary with latest candle data or None
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=8)  # Get last 8 hours

        df = await self.fetch_4hour_intraday(symbol, start_date, end_date, asset_type)

        if df.empty:
            return None

        # Get most recent row
        latest = df.iloc[-1]

        return {
            "timestamp": latest["timestamp"],
            "open": latest["open"],
            "high": latest["high"],
            "low": latest["low"],
            "close": latest["close"],
            "volume": latest["volume"],
            "adjusted_close": latest["adjusted_close"],
            "source": "yfinance",
            "data_quality": 1.0,
        }

    async def fetch_batch(
        self,
        symbols: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: Optional[str] = None,
        interval: str = "1d",
        asset_types: Optional[Dict[str, str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols in batch.

        Args:
            symbols: List of symbols
            start_date: Start date (ignored if period is provided)
            end_date: End date (ignored if period is provided)
            period: Period string like 'max', '1y', etc. (takes precedence over start/end)
            interval: Data interval
            asset_types: Optional mapping of symbol -> asset_type

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        asset_types = asset_types or {}

        # Convert symbols to Yahoo Finance format
        yf_symbols = []
        symbol_mapping = {}

        for symbol in symbols:
            asset_type = asset_types.get(symbol)
            yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)
            yf_symbols.append(yf_symbol)
            symbol_mapping[yf_symbol] = symbol

        if period:
            date_desc = f"period={period}"
        else:
            date_desc = f"from {start_date.date()} to {end_date.date()}" if start_date and end_date else "no dates"

        logger.info(
            f"Sequential batch fetch for {len(yf_symbols)} symbols "
            f"({date_desc}, interval={interval})"
        )

        results: Dict[str, pd.DataFrame] = {}

        for idx, yf_symbol in enumerate(yf_symbols, start=1):
            original_symbol = symbol_mapping[yf_symbol]
            asset_type = asset_types.get(original_symbol)

            logger.info(
                f"[Batch {idx}/{len(yf_symbols)}] Fetching via singular pipeline: {original_symbol} -> {yf_symbol}"
            )

            # Use the singular fetch method to centralize rate limiting, conversion, and errors
            attempts = 0
            max_attempts = 2
            df = pd.DataFrame()
            last_error: Optional[str] = None
            while attempts < max_attempts:
                attempts += 1
                try:
                    if period:
                        # For period-based fetch, use a modified singular method
                        df = await self._fetch_with_period(
                            symbol=original_symbol,
                            period=period,
                            interval=interval,
                            asset_type=asset_type,
                        )
                    else:
                        assert start_date is not None and end_date is not None, "start_date and end_date required when period is None"
                        df = await self.fetch_historical_data(
                            symbol=original_symbol,
                            start_date=start_date,
                            end_date=end_date,
                            interval=interval,
                            asset_type=asset_type,
                        )
                    if df.empty:
                        logger.warning(
                            f"[Attempt {attempts}/{max_attempts}] Empty dataframe for {original_symbol} ({yf_symbol})"
                        )
                        await asyncio.sleep(1.0)
                    else:
                        break
                except Exception as e:
                    last_error = str(e)
                    logger.error(
                        f"[Attempt {attempts}/{max_attempts}] Exception for {original_symbol}: {e}"
                    )
                    await asyncio.sleep(1.0)

            if df.empty and last_error:
                logger.error(
                    f"Final failure for {original_symbol} after {max_attempts} attempts: {last_error}"
                )

            results[original_symbol] = df

        logger.info(
            f"Sequential batch fetch complete: {len(results)} symbols processed (singular fetch path)"
        )
        return results

    async def fetch_batch_multi(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        asset_types: Optional[Dict[str, str]] = None,
        group_size: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch multiple symbols using yfinance multi-ticker download in groups.

        - Uses a single Yahoo request per group of up to `group_size` symbols.
        - Respects the client's delay_between_requests between groups.
        """
        asset_types = asset_types or {}

        # Build mapping original -> yf symbol
        symbol_map: Dict[str, str] = {}
        for s in symbols:
            symbol_map[s] = self._convert_symbol_to_yfinance(s, asset_types.get(s))

        # Helper to split into chunks
        def chunk(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i : i + n]

        results: Dict[str, pd.DataFrame] = {}
        for group in chunk(symbols, group_size):
            yf_group = [symbol_map[s] for s in group]

            # Rate limiting per group request
            if self.config.respect_server:
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.config.delay_between_requests:
                    sleep_duration = self.config.delay_between_requests - time_since_last
                    logger.info(
                        f"Rate limiting: waiting {sleep_duration:.1f}s before next multi-ticker request"
                    )
                    await asyncio.sleep(sleep_duration)
                self.last_request_time = asyncio.get_event_loop().time()

            logger.info(
                f"Fetching Yahoo Finance data for group: {', '.join(yf_group)} "
                f"from {start_date.date()} to {end_date.date()} (interval: {interval})"
            )

            try:
                loop = asyncio.get_event_loop()
                yf_df = await loop.run_in_executor(
                    None,
                    lambda: yf.download(
                        tickers=yf_group,
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        auto_adjust=self.config.auto_adjust,
                        repair=self.config.repair,
                        keepna=self.config.keepna,
                        progress=False,
                        timeout=self.config.timeout,
                        group_by='ticker',
                        threads=False,
                    ),
                )

                # yfinance returns a single DataFrame for one ticker (no MultiIndex) or
                # a dict-like columns grouped by ticker when group_by='ticker'.
                if yf_df is None:
                    logger.error(f"yf.download returned None for group {yf_group}")
                    for orig in group:
                        results[orig] = pd.DataFrame()
                    continue
                if isinstance(yf_df, pd.DataFrame) and not isinstance(yf_df.columns, pd.MultiIndex):
                    # Single ticker case in group
                    only = group[0]
                    results[only] = self._yfinance_to_hedgevision_df(yf_df, only)
                else:
                    # Multi-ticker: iterate expected tickers in group
                    for orig in group:
                        yf_t = symbol_map[orig]
                        try:
                            # When group_by='ticker', columns are a regular Index of OHLC for each ticker
                            # accessible via yf_df[yf_t]
                            sub = yf_df[yf_t]
                            # Ensure DataFrame
                            if isinstance(sub, pd.Series):
                                sub = sub.to_frame()
                            results[orig] = self._yfinance_to_hedgevision_df(sub, orig)
                        except Exception:
                            results[orig] = pd.DataFrame()
                            logger.warning(f"No data segment for {yf_t} in group response")

            except Exception as e:
                logger.error(f"Failed multi-ticker download for group {yf_group}: {e}")
                for orig in group:
                    results[orig] = pd.DataFrame()

        # RETRY PHASE: For any empty results, try individual fetches (retry with backoff)
        failed_symbols = [s for s in symbols if results[s].empty]
        if failed_symbols:
            logger.info(f"\nRetrying {len(failed_symbols)} failed tickers with individual fetch + exponential backoff...")
            for symbol in failed_symbols:
                asset_type = asset_types.get(symbol)
                for attempt in range(1, 4):  # 3 total attempts
                    backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    try:
                        logger.info(
                            f"  [Retry {attempt}/3] Fetching {symbol} individually (backoff: {backoff}s)"
                        )
                        await asyncio.sleep(backoff)
                        df = await self.fetch_historical_data(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date,
                            interval=interval,
                            asset_type=asset_type,
                        )
                        if not df.empty:
                            results[symbol] = df
                            logger.info(f"  ✓ Retry successful for {symbol}: {len(df)} records")
                            break
                        else:
                            logger.warning(f"  ⚠ Retry {attempt}/3 returned empty for {symbol}")
                    except Exception as e:
                        logger.warning(f"  ⚠ Retry {attempt}/3 failed for {symbol}: {e}")
                        if attempt == 3:
                            logger.error(f"  ✗ All retries exhausted for {symbol}")

        return results

    async def get_ticker_info(
    self, symbol: str, asset_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get ticker information and metadata.

        Args:
            symbol: Stock/ETF/Crypto symbol
            asset_type: Asset type hint

        Returns:
            Dictionary with ticker info
        """
        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, lambda: yf.Ticker(yf_symbol))

            info = ticker.info
            logger.info(f"Retrieved info for {yf_symbol}")
            return info

        except Exception as e:
            logger.error(f"Failed to get info for {yf_symbol}: {e}")
            return {}

    async def fetch_corporate_actions(
        self, symbol: str, asset_type: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch dividends and stock splits data for a symbol.

        Args:
            symbol: Stock/ETF/Crypto symbol
            asset_type: Asset type hint

        Returns:
            Dictionary with 'dividends' and 'splits' DataFrames
        """
        yf_symbol = self._convert_symbol_to_yfinance(symbol, asset_type)

        try:
            loop = asyncio.get_event_loop()
            ticker = await loop.run_in_executor(None, lambda: yf.Ticker(yf_symbol))

            # Fetch dividends and splits
            dividends = await loop.run_in_executor(None, lambda: ticker.dividends)
            splits = await loop.run_in_executor(None, lambda: ticker.splits)

            # Convert to DataFrames and standardize
            dividends_df = dividends.reset_index() if not dividends.empty else pd.DataFrame()
            splits_df = splits.reset_index() if not splits.empty else pd.DataFrame()

            # Standardize column names
            if not dividends_df.empty:
                dividends_df.columns = [col.lower() for col in dividends_df.columns]
                dividends_df = dividends_df.rename(columns={'date': 'timestamp', 'dividends': 'amount'})
                dividends_df['action_type'] = 'dividend'
                dividends_df['source'] = 'yfinance'

            if not splits_df.empty:
                splits_df.columns = [col.lower() for col in splits_df.columns]
                splits_df = splits_df.rename(columns={'date': 'timestamp', 'stock splits': 'ratio'})
                splits_df['action_type'] = 'split'
                splits_df['source'] = 'yfinance'

            logger.info(f"Fetched corporate actions for {yf_symbol}: {len(dividends_df)} dividends, {len(splits_df)} splits")
            return {'dividends': dividends_df, 'splits': splits_df}

        except Exception as e:
            logger.error(f"Failed to fetch corporate actions for {yf_symbol}: {e}")
            return {'dividends': pd.DataFrame(), 'splits': pd.DataFrame()}

    async def close(self):
        """Close client (no-op for yfinance, included for consistency)."""
        logger.info("Yahoo Finance client closed (no cleanup needed)")
# Singleton instance
_client = None


def get_yfinance_client() -> YFinanceClient:
    """Get or create singleton YFinanceClient instance.

    Honors optional environment overrides for local runs:
      - YF_DELAY_BETWEEN_REQUESTS: float seconds (default 60.0)
      - YF_RESPECT_SERVER: true/false (default true)
    """
    global _client
    if _client is None:
        # Default to 20s between requests unless overridden via env
        try:
            delay = float(os.getenv("YF_DELAY_BETWEEN_REQUESTS", "20.0"))
        except Exception:
            delay = 20.0
        respect = str(os.getenv("YF_RESPECT_SERVER", "true")).lower() in ("true", "1", "yes")
        cfg = YFinanceConfig(delay_between_requests=delay, respect_server=respect)
        _client = YFinanceClient(config=cfg)
    return _client
