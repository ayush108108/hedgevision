"""
Pipeline Service - ETL (Extract, Transform, Load) for Price Data

This service manages the complete data ingestion pipeline:
1. EXTRACT: Fetch data from external providers (yfinance)
2. TRANSFORM: Standardize and validate data
3. LOAD: Store data in Supabase database

Replaces: data_ingestion_service.py and data_fetching_service.py
Uses: yfinance_client.py, data_standardization_service.py, supabase_client (via query_service)

Architecture:
- run_pipeline() is the single entry point for all data writing
- Supports daily and 4-hour granularities
- Handles both single-asset and batch operations
- Includes comprehensive error handling and logging
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any, List, Optional
from enum import Enum

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log,
    )
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False

# Support both package layouts: when running in Docker or with backend as top-level module,
# 'clients' is importable after api.main adds backend to sys.path. Avoid hard 'backend.' prefix.
from clients.yfinance_client import get_yfinance_client, YFinanceClient
from api.services.data_standardization_service import DataStandardizationService
from api.services.data_writer_service import get_data_writer, DataWriter

logger = logging.getLogger(__name__)


class Granularity(Enum):
    """Supported data granularities."""
    DAILY = "daily"
    FOUR_HOUR = "4h"
    HOURLY = "hourly"


class PipelineService:
    """
    ETL pipeline for ingesting price data from external sources.
    
    This service orchestrates the complete data flow:
    - Fetches data from yfinance
    - Standardizes/validates using DataStandardizationService
    - Stores in Supabase using DataWriter
    """

    def __init__(self):
        """Initialize pipeline components."""
        self.yfinance_client: YFinanceClient = get_yfinance_client()
        self.standardization_service = DataStandardizationService()
        self.data_writer: DataWriter = get_data_writer()
        logger.info("Pipeline service initialized with yfinance provider")

    async def run_pipeline(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "daily",
        asset_type: Optional[str] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline for a single asset.
        
        This is the main entry point for data ingestion.
        
        Pipeline Steps:
        1. EXTRACT: Fetch data from yfinance
        2. TRANSFORM: Standardize and validate data
        3. LOAD: Store in Supabase database
        
        Args:
            symbol: Asset symbol (e.g., 'AAPL', 'BTC-USD', 'RELIANCE.NS')
            start_date: Start date for data fetch
            end_date: End date for data fetch
            granularity: Data frequency ('daily', '4h', 'hourly')
            asset_type: Asset type hint ('stock', 'etf', 'crypto')
            validate: Whether to validate data quality
            
        Returns:
            Dictionary with pipeline results:
            {
                'status': 'success' | 'partial' | 'failed',
                'symbol': str,
                'records_fetched': int,
                'records_stored': int,
                'granularity': str,
                'duration_seconds': float,
                'error': Optional[str]
            }
        """
        start_time = datetime.now()
        pipeline_result = {
            'status': 'failed',
            'symbol': symbol,
            'records_fetched': 0,
            'records_stored': 0,
            'granularity': granularity,
            'duration_seconds': 0.0,
            'error': None
        }
        
        try:
            logger.info(
                f"Starting pipeline for {symbol} "
                f"({start_date.date()} to {end_date.date()}, {granularity})"
            )
            
            # ============================================================
            # STEP 1: EXTRACT - Fetch data from yfinance
            # ============================================================
            df_raw = await self._extract_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                asset_type=asset_type
            )
            
            if df_raw.empty:
                pipeline_result['status'] = 'failed'
                pipeline_result['error'] = 'No data returned from yfinance'
                logger.warning(f"No data fetched for {symbol}")
                return pipeline_result
            
            pipeline_result['records_fetched'] = len(df_raw)
            logger.info(f"Extracted {len(df_raw)} records for {symbol}")
            
            # ============================================================
            # STEP 2: TRANSFORM - Standardize and validate
            # ============================================================
            df_clean = self._transform_data(
                df=df_raw,
                symbol=symbol,
                validate=validate
            )
            
            if df_clean.empty:
                pipeline_result['status'] = 'partial'
                pipeline_result['error'] = 'Data failed validation'
                logger.warning(f"Data validation failed for {symbol}")
                return pipeline_result
            
            logger.info(f"Transformed {len(df_clean)} records for {symbol}")
            
            # ============================================================
            # STEP 3: LOAD - Store in database
            # ============================================================
            records_stored = self._load_data(
                df=df_clean,
                symbol=symbol,
                granularity=granularity
            )
            
            pipeline_result['records_stored'] = records_stored
            total_input = len(df_clean)
            duplicates_count = max(0, total_input - (records_stored or 0))
            pipeline_result['duplicates'] = duplicates_count
            
            if records_stored == 0:
                # Treat as duplicate/no-op instead of failure
                pipeline_result['status'] = 'skipped'
                pipeline_result['error'] = 'No new rows (duplicates)'
                logger.info(f"No new rows stored for {symbol} — skipped (duplicates: {duplicates_count})")
            elif records_stored < len(df_clean):
                pipeline_result['status'] = 'partial'
                pipeline_result['error'] = f'Only {records_stored}/{len(df_clean)} records stored'
                logger.warning(f"Partial storage for {symbol}: {records_stored} new, {duplicates_count} duplicates (of {len(df_clean)})")
            else:
                pipeline_result['status'] = 'success'
                logger.info(f"Stored {records_stored} new, {duplicates_count} duplicates for {symbol}")
            
        except Exception as e:
            pipeline_result['status'] = 'failed'
            pipeline_result['error'] = str(e)
            logger.error(f"Pipeline failed for {symbol}: {e}", exc_info=True)
        
        finally:
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            pipeline_result['duration_seconds'] = round(duration, 2)
            
            logger.info(
                f"Pipeline completed for {symbol}: {pipeline_result['status']} "
                f"in {duration:.2f}s"
            )
        
        return pipeline_result

    async def run_multi_fetch_store(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        granularity: str = "daily",
        asset_types: Optional[Dict[str, str]] = None,
        group_size: int = 5,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """Fetch multiple symbols in grouped Yahoo requests and store in bulk.

        Returns a summary with per-symbol status and inserted counts.
        """
        interval_map = {"daily": "1d", "4h": "1h", "hourly": "1h"}
        interval = interval_map.get(granularity, "1d")

        # Use multi-ticker fetch with retry/backoff if tenacity is available
        async def _fetch_with_retries() -> Dict[str, pd.DataFrame]:
            return await self.yfinance_client.fetch_batch_multi(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                asset_types=asset_types,
                group_size=group_size,
            )

        if _TENACITY_AVAILABLE:
            import tenacity  # noqa: PLC0415
            _fetch_with_retries_retried = tenacity.retry(
                stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_exponential(multiplier=2, min=2, max=30),
                retry=tenacity.retry_if_exception_type(Exception),
                before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )(_fetch_with_retries)
            fetched: Dict[str, pd.DataFrame] = await _fetch_with_retries_retried()
        else:
            fetched = await _fetch_with_retries()

        # Transform per-symbol
        cleaned: Dict[str, pd.DataFrame] = {}
        for sym, df in fetched.items():
            if df is None or df.empty:
                cleaned[sym] = pd.DataFrame()
                continue
            try:
                cleaned[sym] = self.standardization_service.standardize_price_data(
                    df=df,
                    symbol=sym,
                    data_type="ohlcv",
                    validate=validate,
                )
            except Exception:
                cleaned[sym] = pd.DataFrame()

        # Store all in bulk
        inserted_map = self.data_writer.store_multiple_symbols(cleaned, source="yfinance")

        # Build summary
        summary = {
            "symbols": symbols,
            "results": {},
            "total_inserted": 0,
        }
        for sym in symbols:
            inserted = int(inserted_map.get(sym, 0))
            status = "success" if inserted > 0 else "skipped"
            summary["results"][sym] = {"status": status, "records_stored": inserted}
            summary["total_inserted"] += inserted

        return summary

    async def _extract_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        granularity: str,
        asset_type: Optional[str] = None
    ):
        """
        EXTRACT: Fetch data from yfinance.
        
        Args:
            symbol: Asset symbol
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            asset_type: Asset type hint
            
        Returns:
            Raw DataFrame from yfinance
        """
        # Determine yfinance interval
        interval_map = {
            'daily': '1d',
            '4h': '1h',  # Fetch 1h and aggregate to 4h
            'hourly': '1h'
        }
        interval = interval_map.get(granularity, '1d')
        
        # Fetch data
        df = await self.yfinance_client.fetch_historical_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            asset_type=asset_type
        )
        
        # If 4h requested, aggregate from 1h
        if granularity == '4h' and not df.empty:
            df = self.yfinance_client._aggregate_to_4hour(df)
        
        return df

    def _transform_data(
        self,
        df,
        symbol: str,
        validate: bool = True
    ):
        """
        TRANSFORM: Standardize and validate data.
        
        Args:
            df: Raw DataFrame
            symbol: Asset symbol
            validate: Whether to validate
            
        Returns:
            Cleaned and standardized DataFrame
        """
        return self.standardization_service.standardize_price_data(
            df=df,
            symbol=symbol,
            data_type='ohlcv',
            validate=validate
        )

    def _load_data(
        self,
        df,
        symbol: str,
        granularity: str
    ) -> int:
        """
        LOAD: Store data in Supabase database.
        
        Args:
            df: Standardized DataFrame
            symbol: Asset symbol
            granularity: Data frequency
            
        Returns:
            Number of records stored
        """
        try:
            # Use DataWriter to store data
            # DataWriter handles Supabase client internally
            if granularity == 'daily':
                # Store in price_history table; return number of newly inserted rows
                return self.data_writer.store_data(symbol, df, source='yfinance')
            else:
                # Store in prices_hourly table (for 4h and hourly)
                if hasattr(self.data_writer, 'store_hourly_prices'):
                    return self.data_writer.store_hourly_prices(symbol, df)
                else:
                    # Fallback to generic store_data
                    return self.data_writer.store_data(symbol, df, source='yfinance')
            
        except Exception as e:
            logger.error(f"Failed to store data for {symbol}: {e}")
            return 0

    async def run_batch_pipeline(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        granularity: str = "daily",
        asset_types: Optional[Dict[str, str]] = None,
        max_concurrent: int = 3,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Run pipeline for multiple symbols in batch.
        
        Args:
            symbols: List of asset symbols
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            asset_types: Optional mapping of symbol -> asset_type
            max_concurrent: Maximum concurrent operations
            validate: Whether to validate data
            
        Returns:
            Batch results summary:
            {
                'total_symbols': int,
                'successful': int,
                'failed': int,
                'partial': int,
                'total_records_stored': int,
                'duration_seconds': float,
                'results': Dict[str, Dict[str, Any]]
            }
        """
        start_time = datetime.now()
        asset_types = asset_types or {}
        
        logger.info(
            f"Starting batch pipeline for {len(symbols)} symbols "
            f"(max_concurrent={max_concurrent})"
        )
        
        # Use semaphore to control concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def run_single_pipeline(symbol: str):
            """Run pipeline for single symbol with semaphore."""
            async with semaphore:
                asset_type = asset_types.get(symbol)
                result = await self.run_pipeline(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    granularity=granularity,
                    asset_type=asset_type,
                    validate=validate
                )
                results[symbol] = result
                
                # Log progress
                status = result['status']
                records = result['records_stored']
                logger.info(
                    f"[{len(results)}/{len(symbols)}] {symbol}: "
                    f"{status}, {records} records"
                )
        
        # Create tasks for all symbols
        tasks = [run_single_pipeline(symbol) for symbol in symbols]
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Summarize results
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        failed = sum(1 for r in results.values() if r['status'] == 'failed')
        partial = sum(1 for r in results.values() if r['status'] == 'partial')
        total_records = sum(r['records_stored'] for r in results.values())
        
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            'total_symbols': len(symbols),
            'successful': successful,
            'failed': failed,
            'partial': partial,
            'total_records_stored': total_records,
            'duration_seconds': round(duration, 2),
            'results': results
        }
        
        logger.info(
            f"Batch pipeline completed: "
            f"{successful} successful, {failed} failed, {partial} partial "
            f"({total_records} total records in {duration:.2f}s)"
        )
        
        return summary

    async def run_daily_backfill(
        self,
        symbol: str,
        days_back: int = 365,
        asset_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Backfill historical daily data for an asset.
        
        Args:
            symbol: Asset symbol
            days_back: Number of days to backfill
            asset_type: Asset type hint
            
        Returns:
            Pipeline result
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Running daily backfill for {symbol} ({days_back} days)")
        
        return await self.run_pipeline(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            granularity='daily',
            asset_type=asset_type
        )

    async def run_all_time_backfill(
        self,
        symbol: str,
        asset_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch ALL available historical data for an asset (maximum history).
        
        Uses yfinance period='max' to get all available data.
        
        Args:
            symbol: Asset symbol
            asset_type: Asset type hint
            
        Returns:
            Pipeline result
        """
        start_time = datetime.now()
        
        logger.info(f"Running ALL-TIME backfill for {symbol}")
        
        try:
            # Fetch all-time data from yfinance
            df_raw = await self.yfinance_client.fetch_all_time_daily(
                symbol=symbol,
                asset_type=asset_type
            )
            
            if df_raw.empty:
                return {
                    'status': 'failed',
                    'symbol': symbol,
                    'records_fetched': 0,
                    'records_stored': 0,
                    'error': 'No all-time data available'
                }
            
            # Transform
            df_clean = self._transform_data(df_raw, symbol, validate=True)
            
            # Load
            records_stored = self._load_data(df_clean, symbol, 'daily')
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'status': 'success' if records_stored > 0 else 'failed',
                'symbol': symbol,
                'records_fetched': len(df_raw),
                'records_stored': records_stored,
                'granularity': 'daily',
                'duration_seconds': round(duration, 2)
            }
            
            if not df_clean.empty:
                first_date = df_clean['date'].min().date() if 'date' in df_clean else None
                last_date = df_clean['date'].max().date() if 'date' in df_clean else None
                logger.info(
                    f"All-time backfill for {symbol}: {records_stored} records "
                    f"({first_date} to {last_date})"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"All-time backfill failed for {symbol}: {e}")
            return {
                'status': 'failed',
                'symbol': symbol,
                'records_fetched': 0,
                'records_stored': 0,
                'error': str(e)
            }

    async def close(self):
        """Clean up resources."""
        await self.yfinance_client.close()
        logger.info("Pipeline service closed")


# Singleton instance
_pipeline_service = None


def get_pipeline_service() -> PipelineService:
    """Get or create singleton PipelineService instance."""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service


# Convenience functions for common operations
async def ingest_daily_data(
    symbol: str,
    days_back: int = 365,
    asset_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function: Ingest daily data for a symbol.
    
    Args:
        symbol: Asset symbol
        days_back: Number of days to fetch
        asset_type: Asset type hint
        
    Returns:
        Pipeline result
    """
    service = get_pipeline_service()
    return await service.run_daily_backfill(symbol, days_back, asset_type)


async def ingest_batch_daily(
    symbols: List[str],
    days_back: int = 365,
    asset_types: Optional[Dict[str, str]] = None,
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """
    Convenience function: Ingest daily data for multiple symbols.
    
    Args:
        symbols: List of symbols
        days_back: Number of days to fetch
        asset_types: Optional symbol -> asset_type mapping
        max_concurrent: Maximum concurrent operations
        
    Returns:
        Batch results
    """
    service = get_pipeline_service()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    return await service.run_batch_pipeline(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        granularity='daily',
        asset_types=asset_types,
        max_concurrent=max_concurrent
    )
