"""
Unified Data Ingestion Service.

Routes assets to appropriate data sources based on asset universe configuration:
- CCXT/Binance for crypto assets (Section A)
- yfinance for macro monitoring and gap assets (Sections B & C)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import time

import pandas as pd

try:
    from clients.ccxt_client import get_ccxt_client
    from clients.yfinance_client import get_yfinance_client
except Exception:  # pragma: no cover - fallback for alternate package roots
    from backend.clients.ccxt_client import get_ccxt_client  # type: ignore
    from backend.clients.yfinance_client import get_yfinance_client  # type: ignore
from api.utils.asset_universe_loader import (
    get_crypto_core_tickers,
    get_macro_monitor_tickers,
    get_gap_assets_tickers
)

logger = logging.getLogger(__name__)


class UnifiedDataIngestionService:
    """
    Unified service for ingesting price data from multiple sources.

    Routes assets to appropriate clients based on asset universe configuration:
    - Crypto assets (Section A) -> CCXT/Binance
    - Other assets (Sections B & C) -> yfinance
    """

    def __init__(self):
        self.ccxt_client = get_ccxt_client()
        self.yfinance_client = get_yfinance_client()

        # Cache asset classifications
        self.crypto_tickers = set(get_crypto_core_tickers())
        self.macro_tickers = set(get_macro_monitor_tickers())
        self.gap_tickers = set(get_gap_assets_tickers())

    def get_data_source_for_asset(self, ticker: str) -> str:
        """
        Determine which data source to use for a given asset ticker.

        Args:
            ticker: Asset ticker symbol

        Returns:
            'ccxt' for crypto assets, 'yfinance' for others
        """
        if ticker in self.crypto_tickers:
            return 'ccxt'
        else:
            return 'yfinance'

    def is_crypto_asset(self, ticker: str) -> bool:
        """Check if ticker is a crypto asset."""
        return ticker in self.crypto_tickers

    async def fetch_symbol_data(
        self,
        ticker: str,
        period: str = 'max',
        interval: str = '1d',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch price data for a single symbol using the appropriate data source.

        Args:
            ticker: Asset ticker
            period: Period for yfinance ('max', '1y', etc.)
            interval: Interval for yfinance ('1d', '1h', etc.) or timeframe for CCXT
            start_date: Start date (for yfinance)
            end_date: End date (for yfinance)

        Returns:
            DataFrame with OHLCV data
        """
        data_source = self.get_data_source_for_asset(ticker)

        try:
            if data_source == 'ccxt':
                # Use CCXT for crypto assets
                logger.info(f"Fetching {ticker} from CCXT/Binance")

                # Convert yfinance-style interval to CCXT timeframe
                timeframe = self._convert_interval_to_timeframe(interval)

                # Fetch data
                ohlcv_data = self.ccxt_client.fetch_ohlcv_sync(
                    symbol=ticker,
                    timeframe=timeframe,
                    limit=1000  # Adjust as needed
                )

                # Convert to DataFrame
                df = self.ccxt_client.convert_to_dataframe(ohlcv_data)

            else:
                # Use yfinance for other assets
                logger.info(f"Fetching {ticker} from yfinance")
                df = self.yfinance_client.fetch_price_history(
                    ticker=ticker,
                    period=period,
                    interval=interval,
                    start=start_date,
                    end=end_date
                )

            if df.empty:
                logger.warning(f"No data fetched for {ticker}")
            else:
                logger.info(f"Fetched {len(df)} rows for {ticker}")

            return df

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    async def fetch_batch_data(
        self,
        tickers: List[str],
        period: str = 'max',
        interval: str = '1d',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        batch_size: int = 10,
        delay_between_batches: float = 1.0
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch price data for multiple symbols in batches.

        Args:
            tickers: List of asset tickers
            period: Period for yfinance
            interval: Interval/timeframe
            start_date: Start date
            end_date: End date
            batch_size: Number of symbols per batch
            delay_between_batches: Delay between batches in seconds

        Returns:
            Dictionary mapping tickers to DataFrames
        """
        results = {}

        # Group tickers by data source for efficiency
        ccxt_tickers = [t for t in tickers if self.is_crypto_asset(t)]
        yfinance_tickers = [t for t in tickers if not self.is_crypto_asset(t)]

        logger.info(f"Processing {len(ccxt_tickers)} crypto assets via CCXT")
        logger.info(f"Processing {len(yfinance_tickers)} other assets via yfinance")

        # Process CCXT assets (typically smaller batch due to rate limits)
        for i in range(0, len(ccxt_tickers), batch_size):
            batch = ccxt_tickers[i:i + batch_size]
            logger.info(f"Processing CCXT batch {i//batch_size + 1}: {batch}")

            for ticker in batch:
                df = await self.fetch_symbol_data(
                    ticker=ticker,
                    period=period,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date
                )
                if not df.empty:
                    results[ticker] = df

            # Delay between batches
            if i + batch_size < len(ccxt_tickers):
                await asyncio.sleep(delay_between_batches)

        # Process yfinance assets
        for i in range(0, len(yfinance_tickers), batch_size):
            batch = yfinance_tickers[i:i + batch_size]
            logger.info(f"Processing yfinance batch {i//batch_size + 1}: {batch}")

            # yfinance client can handle batch requests more efficiently
            batch_results = await self.yfinance_client.fetch_batch(
                symbols=batch,
                period=period,
                interval=interval,
                start=start_date,
                end=end_date
            )

            results.update(batch_results)

            # Delay between batches
            if i + batch_size < len(yfinance_tickers):
                await asyncio.sleep(delay_between_batches)

        return results

    def _convert_interval_to_timeframe(self, interval: str) -> str:
        """
        Convert yfinance interval to CCXT timeframe.

        Args:
            interval: yfinance interval ('1d', '4h', '1h', etc.)

        Returns:
            CCXT timeframe string
        """
        # Map common intervals to CCXT timeframes
        mapping = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
            '1wk': '1w',
            '1mo': '1M'
        }

        return mapping.get(interval, '1d')


# Global service instance
_unified_ingestion_service = None

def get_unified_ingestion_service() -> UnifiedDataIngestionService:
    """Get or create unified ingestion service instance."""
    global _unified_ingestion_service
    if _unified_ingestion_service is None:
        _unified_ingestion_service = UnifiedDataIngestionService()
    return _unified_ingestion_service
