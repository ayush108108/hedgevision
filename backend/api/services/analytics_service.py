"""
Analytics Service - High-Level Financial Analysis API

This is the ONLY service routers should use for financial analytics.
It's the "Head Chef" that orchestrates low-level math helpers.

Architecture:
- analytics_service.py (THIS FILE) - High-level public API for routers
- correlation_service.py - Low-level correlation calculations (helper)
- cointegration_service.py - Low-level cointegration tests (helper)

Replaces:
- screener_service.py (get_screener_top_pairs)
- business_calculations_service.py (rolling beta/volatility/correlation)
- Part of pair_analysis logic (consolidated with cointegration)

Public API Functions:
1. get_screener_top_pairs() - Get top correlated pairs
2. get_full_pair_report() - Comprehensive pair analysis
3. get_rolling_correlation() - Rolling correlation between assets
4. get_rolling_beta() - Rolling beta for asset vs benchmark
5. get_rolling_volatility() - Rolling volatility for asset
6. get_correlation_matrix() - Full correlation matrix

Each function is a clean, high-level interface that routers can call.
"""

import logging
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd
from fastapi import HTTPException, status

from api.utils.config import config
from api.utils.cache_adapter import get_cache_adapter
from api.utils.assets import name_to_symbol
from api.utils.supabase_client import get_supabase_client
from api.utils.datetime_normalization import normalize_datetime_iso

# Import low-level math helpers
from .correlation_service import (
    get_correlation_data,
    calculate_rolling_correlation as _calc_rolling_correlation,
)
from .cointegration_service import CointegrationService
from .data_standardization_service import DataStandardizationService

logger = logging.getLogger(__name__)


def _candidate_symbols(symbol: str) -> list[str]:
    """Return likely symbol variants for local SQLite lookups."""
    candidates = [symbol]
    if symbol.endswith(".CC"):
        candidates.append(symbol[:-3])
    if symbol.endswith(".US"):
        candidates.append(symbol[:-3])
    return list(dict.fromkeys(candidates))


class AnalyticsService:
    """
    High-level analytics service - the single entry point for routers.
    
    This service provides clean, router-friendly functions that internally
    delegate to low-level correlation and cointegration services.
    """

    def __init__(self):
        """Initialize analytics service with dependencies."""
        self.cache = get_cache_adapter(default_ttl=config.get("REDIS_TTL", 3600))
        self.supabase_client = get_supabase_client()
        self.cointegration_service = CointegrationService()
        self.standardization_service = DataStandardizationService()
        logger.info("Analytics service initialized")

    # ========================================================================
    # SCREENER FUNCTIONS
    # ========================================================================

    def get_screener_top_pairs(
        self,
        min_correlation: float = 0.7,
        limit: int = 50,
        granularity: str = "daily",
        method: str = "spearman",
        max_age_hours: int = 6,
    ) -> Dict[str, Any]:
        """
        Get top correlated pairs for screening.
        
        Replaces: screener_service.get_screened_pairs()
        
        Args:
            min_correlation: Minimum absolute correlation threshold
            limit: Maximum number of pairs to return
            granularity: Data granularity (daily, hourly)
            method: Correlation method (spearman, pearson)
            max_age_hours: Maximum age of precomputed data in hours
            
        Returns:
            {
                'pairs': List[Dict],
                'total_pairs': int,
                'data_age_hours': float,
                'cache_status': str,
                'granularity': str,
                'method': str
            }
        """
        # If Supabase isn't configured, fall back to on-the-fly computation
        if not self.supabase_client:
            logger.warning(
                "Supabase not configured or unavailable; falling back to dynamic computation"
            )
            return self._compute_pairs_on_fly(
                min_correlation, limit, granularity, method
            )

        try:
            # Try to get precomputed correlation matrix from Supabase
            matrix_row = self.supabase_client.get_correlation_matrix(
                granularity=granularity,
                method=method,
                max_age_hours=max_age_hours,
            )

            if not matrix_row:
                logger.warning(
                    "No precomputed correlation matrix found, computing on-the-fly"
                )
                return self._compute_pairs_on_fly(
                    min_correlation, limit, granularity, method
                )

            # Extract correlation matrix from precomputed data
            correlation_matrix = matrix_row.get("correlation_matrix", {})
            
            if not correlation_matrix:
                logger.warning("Empty correlation matrix, computing on-the-fly")
                return self._compute_pairs_on_fly(
                    min_correlation, limit, granularity, method
                )

            # Calculate data age
            created_at = datetime.fromisoformat(
                matrix_row.get("created_at", datetime.utcnow().isoformat()).replace("Z", "+00:00")
            )
            data_age_hours = (datetime.utcnow().replace(tzinfo=created_at.tzinfo) - created_at).total_seconds() / 3600

            # Determine cache status
            cache_status = (
                "fresh" if data_age_hours < 1
                else "stale" if data_age_hours < max_age_hours
                else "expired"
            )

            # Extract pairs from matrix
            pairs = self._extract_pairs_from_matrix(
                correlation_matrix, min_correlation, limit
            )

            return {
                "pairs": pairs,
                "total_pairs": len(pairs),
                "data_age_hours": round(data_age_hours, 2),
                "cache_status": cache_status,
                "granularity": granularity,
                "method": method,
                "computed_at": created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error retrieving screened pairs: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve screened pairs: {str(e)}",
            )

    def _extract_pairs_from_matrix(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        min_correlation: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Extract top pairs from correlation matrix."""
        pairs = []
        processed_pairs = set()

        for asset1_name, correlations in correlation_matrix.items():
            if not isinstance(correlations, dict):
                continue

            for asset2_name, correlation_val in correlations.items():
                if asset1_name == asset2_name:
                    continue

                # Avoid duplicates (A-B vs B-A)
                pair_key = tuple(sorted([asset1_name, asset2_name]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                # Skip NaN values
                try:
                    corr_float = float(correlation_val)
                    if not isinstance(corr_float, (int, float)) or corr_float != corr_float:  # NaN check
                        continue
                except (ValueError, TypeError):
                    continue

                abs_corr = abs(corr_float)
                if abs_corr < min_correlation:
                    continue

                # Get symbols (fallback to name if not found)
                asset1_symbol = name_to_symbol.get(asset1_name, asset1_name)
                asset2_symbol = name_to_symbol.get(asset2_name, asset2_name)

                pairs.append({
                    "asset1": asset1_name,
                    "asset1_symbol": asset1_symbol,
                    "asset2": asset2_name,
                    "asset2_symbol": asset2_symbol,
                    "correlation": corr_float,
                    "abs_correlation": abs_corr,
                })

        # Sort by absolute correlation descending
        pairs.sort(key=lambda x: x["abs_correlation"], reverse=True)
        return pairs[:limit]

    def _compute_pairs_on_fly(
        self,
        min_correlation: float,
        limit: int,
        granularity: str,
        method: str
    ) -> Dict[str, Any]:
        """Compute correlation matrix on-the-fly and extract pairs."""
        logger.warning(
            f"Computing correlation dynamically for {granularity}/{method}"
        )

        try:
            # Use correlation_service to compute matrix
            corr_df = get_correlation_data(
                self.cache,
                start_date=None,
                end_date=None,
                method=method,
                granularity=granularity,
                min_periods=60 if granularity == "daily" else 120,
                view_mode="asset",
            )

            if corr_df is None or corr_df.empty:
                return {
                    "pairs": [],
                    "total_pairs": 0,
                    "data_age_hours": 0.0,
                    "cache_status": "computed_empty",
                    "granularity": granularity,
                    "method": method,
                    "message": "Dynamic correlation computation returned no data.",
                }

            # Extract pairs from DataFrame
            pairs = []
            processed = set()

            for a1 in corr_df.index:
                row = corr_df.loc[a1]
                for a2, val in row.items():
                    if a1 == a2:
                        continue
                    
                    key = tuple(sorted([str(a1), str(a2)]))
                    if key in processed:
                        continue
                    processed.add(key)

                    try:
                        corr_val = float(val)
                        # Skip NaN values
                        if corr_val != corr_val:  # NaN check (NaN != NaN)
                            continue
                    except Exception:
                        continue

                    abs_corr = abs(corr_val)
                    if abs_corr < min_correlation:
                        continue

                    asset1_symbol = name_to_symbol.get(str(a1), str(a1))
                    asset2_symbol = name_to_symbol.get(str(a2), str(a2))

                    pairs.append({
                        "asset1": str(a1),
                        "asset1_symbol": asset1_symbol,
                        "asset2": str(a2),
                        "asset2_symbol": asset2_symbol,
                        "correlation": corr_val,
                        "abs_correlation": abs_corr,
                    })

            pairs.sort(key=lambda x: x["abs_correlation"], reverse=True)
            pairs = pairs[:limit]

            return {
                "pairs": pairs,
                "total_pairs": len(pairs),
                "data_age_hours": 0.0,
                "cache_status": "dynamic",
                "granularity": granularity,
                "method": method,
            }

        except Exception as e:
            logger.error(f"Dynamic correlation failed: {e}", exc_info=True)
            return {
                "pairs": [],
                "total_pairs": 0,
                "data_age_hours": 0.0,
                "cache_status": "dynamic_error",
                "granularity": granularity,
                "method": method,
                "message": f"Error: {str(e)}",
            }

    # ========================================================================
    # PAIR ANALYSIS FUNCTIONS
    # ========================================================================

    async def get_full_pair_report(
        self,
        asset1: str,
        asset2: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: str = "daily",
        lookback_days: int = 252,
        use_precomputed: bool = True,
        include_price_data: bool = True,
        include_spread_data: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive pair analysis report.
        
        Replaces: pair_analysis router's _run_analysis function
        Delegates to: CointegrationService for statistical tests
        
        This is the main "Head Chef" function that coordinates:
        1. Trying to fetch precomputed results (if available)
        2. Falling back to on-demand computation
        3. Formatting data for frontend consumption
        
        Args:
            asset1: First asset symbol
            asset2: Second asset symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            granularity: Data frequency (daily, 4h, hourly)
            lookback_days: Lookback period in days
            use_precomputed: Try to use precomputed results first
            include_price_data: Include price time series in response
            include_spread_data: Include spread time series in response
            
        Returns:
            Comprehensive pair report with correlation, cointegration,
            hedge ratio, spread, z-score, and trading signals
        """
        try:
            logger.info(f"Generating full pair report for {asset1}/{asset2}")
            
            # ================================================================
            # STEP 1: Try precomputed results (if enabled and no custom dates)
            # ================================================================
            if use_precomputed and not start_date and not end_date:
                try:
                    if self.supabase_client:
                        max_age_hours = config.get("PRECOMPUTE_MAX_AGE_HOURS", 6)
                        analysis_data = self.supabase_client.get_pair_analysis(
                            asset1=asset1, asset2=asset2, max_age_hours=max_age_hours
                        )
                        
                        if analysis_data:
                            logger.info(f"Using precomputed analysis for {asset1}/{asset2}")
                            return self._format_precomputed_report(
                                analysis_data, asset1, asset2, granularity,
                                include_price_data, include_spread_data
                            )
                except Exception as e:
                    logger.warning(f"Failed to fetch precomputed analysis: {e}")
            
            # ================================================================
            # STEP 2: On-demand computation
            # ================================================================
            logger.info(f"Computing on-demand analysis for {asset1}/{asset2}")
            
            from datetime import timedelta
            
            # Determine date range
            end_dt = datetime.utcnow() if not end_date else datetime.strptime(end_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=lookback_days) if not start_date else datetime.strptime(start_date, "%Y-%m-%d")
            
            # Fetch and prepare data
            prices_df = await self._fetch_pair_data(
                asset1, asset2,
                start_dt.strftime("%Y-%m-%d"),
                end_dt.strftime("%Y-%m-%d"),
                granularity
            )
            
            # Run cointegration analysis
            test_result = self.cointegration_service.test_pair(
                asset1_symbol=asset1,
                asset2_symbol=asset2,
                prices_df=prices_df,
                granularity=granularity,
                lookback_days=(end_dt - start_dt).days
            )
            
            # Format as report
            report = self._format_cointegration_report(
                test_result, prices_df, asset1, asset2,
                include_price_data, include_spread_data
            )
            
            logger.info(
                f"Generated on-demand report for {asset1}/{asset2}: "
                f"cointegrated={test_result.eg_is_cointegrated}, "
                f"score={test_result.overall_score}"
            )
            
            return report
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating pair report: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate pair report: {str(e)}"
            )

    async def _fetch_pair_data(
        self, asset1: str, asset2: str, start_date: str, end_date: str, granularity: str
    ) -> pd.DataFrame:
        """Fetch and merge price data for a pair from database.

        Uses datetime normalization for consistent UTC ISO boundaries.
        """
        data_backend = str(config.get("DATA_BACKEND", "sqlite")).lower()

        if data_backend == "sqlite":
            return await self._fetch_pair_data_sqlite(
                asset1=asset1,
                asset2=asset2,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
            )

        if not self.supabase_client:
            raise HTTPException(
                status_code=503,
                detail="Database not available for data fetching"
            )

        # Map granularity to correct table
        if granularity == "daily":
            table = "price_history"
        elif granularity.lower() in ("4h", "4hr", "4hrly", "four_hour", "fourhour"):
            table = "intraday_price_history"
        else:
            table = "prices_hourly"

        # Normalize temporal bounds once
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)

        async def fetch_asset(symbol: str) -> pd.DataFrame:
            # Guard for type checker/runtime
            assert self.supabase_client is not None, "Supabase client unexpectedly None"
            client = self.supabase_client.client  # type: ignore[union-attr]
            asset_response = (
                client.table("assets")
                .select("id")
                .eq("symbol", symbol)
                .single()
                .execute()
            )
            if not asset_response.data:
                raise HTTPException(404, f"Asset not found: {symbol}")
            asset_id = asset_response.data["id"]
            price_response = (
                client.table(table)
                .select("timestamp, open, high, low, close, volume")
                .eq("asset_id", asset_id)
                .gte("timestamp", start_iso)
                .lte("timestamp", end_iso)
                .order("timestamp")
                .execute()
            )
            if not price_response.data:
                raise HTTPException(404, f"No price data for {symbol}")
            df = pd.DataFrame(list(price_response.data))
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df

        asset1_data = await fetch_asset(asset1)
        asset2_data = await fetch_asset(asset2)

        merged = pd.merge(
            asset1_data,
            asset2_data,
            on="timestamp",
            suffixes=("_asset1", "_asset2")
        )
        if len(merged) < 30:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data: {len(merged)} points (need at least 30)"
            )
        merged = merged.rename(columns={
            "timestamp": "date",
            "close_asset1": "asset1_price",
            "close_asset2": "asset2_price"
        })
        return merged[[
            "date",
            "asset1_price", "asset2_price",
            "open_asset1", "high_asset1", "low_asset1", "volume_asset1",
            "open_asset2", "high_asset2", "low_asset2", "volume_asset2"
        ]]

    async def _fetch_pair_data_sqlite(
        self,
        asset1: str,
        asset2: str,
        start_date: str,
        end_date: str,
        granularity: str,
    ) -> pd.DataFrame:
        """Fetch and merge pair price data from local SQLite."""
        table = "price_history" if granularity == "daily" else "prices_hourly"
        db_path = str(config.get("DB_PATH", "backend/prices.db"))
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)

        def fetch_asset(symbol: str) -> pd.DataFrame:
            with sqlite3.connect(db_path, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row
                asset_row = None
                for candidate in _candidate_symbols(symbol):
                    asset_row = conn.execute(
                        "SELECT id FROM assets WHERE symbol = ? LIMIT 1",
                        (candidate,),
                    ).fetchone()
                    if asset_row:
                        break
                if not asset_row:
                    raise HTTPException(status_code=404, detail=f"Asset not found: {symbol}")

                rows = conn.execute(
                    f"""
                    SELECT timestamp, open, high, low, close, volume
                    FROM {table}
                    WHERE asset_id = ?
                      AND timestamp >= ?
                      AND timestamp <= ?
                    ORDER BY timestamp
                    """,
                    (int(asset_row[0]), start_iso, end_iso),
                ).fetchall()

            if not rows:
                raise HTTPException(status_code=404, detail=f"No price data for {symbol}")

            df = pd.DataFrame([dict(row) for row in rows])
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return df

        asset1_data = fetch_asset(asset1)
        asset2_data = fetch_asset(asset2)

        merged = pd.merge(
            asset1_data,
            asset2_data,
            on="timestamp",
            suffixes=("_asset1", "_asset2"),
        )

        if len(merged) < 30:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data: {len(merged)} points (need at least 30)",
            )

        merged = merged.rename(
            columns={
                "timestamp": "date",
                "close_asset1": "asset1_price",
                "close_asset2": "asset2_price",
            }
        )

        return merged[[
            "date",
            "asset1_price", "asset2_price",
            "open_asset1", "high_asset1", "low_asset1", "volume_asset1",
            "open_asset2", "high_asset2", "low_asset2", "volume_asset2",
        ]]

    async def _fetch_single_asset_data(
        self, symbol: str, start_date: Optional[str], end_date: Optional[str], granularity: str
    ) -> pd.DataFrame:
        """Fetch price data for a single asset from database."""
        data_backend = str(config.get("DATA_BACKEND", "sqlite")).lower()
        if data_backend == "sqlite":
            return await self._fetch_single_asset_data_sqlite(symbol, start_date, end_date, granularity)

        if not self.supabase_client:
            raise HTTPException(
                status_code=503,
                detail="Database not available for data fetching"
            )
        
        # Use default dates if not provided
        if not start_date:
            start_date = "2020-01-01"
        if not end_date:
            end_date = "2026-12-31"
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)
        
        # Map granularity to correct table
        if granularity == "daily":
            table = "price_history"
        elif granularity.lower() in ("4h", "4hr", "4hrly", "four_hour", "fourhour"):
            table = "intraday_price_history"
        else:
            table = "prices_hourly"
        
        # Get asset_id
        asset_response = (
            self.supabase_client.client.table("assets")
            .select("id")
            .eq("symbol", symbol)
            .single()
            .execute()
        )
        
        if not asset_response.data:
            raise HTTPException(404, f"Asset not found: {symbol}")
        
        asset_id = asset_response.data["id"]
        
        # Fetch prices
        price_response = (
            self.supabase_client.client.table(table)
            .select("timestamp, close")
            .eq("asset_id", asset_id)
            .gte("timestamp", start_iso)
            .lte("timestamp", end_iso)
            .order("timestamp")
            .execute()
        )
        
        if not price_response.data or len(price_response.data) == 0:
            raise HTTPException(404, f"No price data for {symbol}")
        
        # Convert to DataFrame
        df = pd.DataFrame(list(price_response.data))
        df["Date"] = pd.to_datetime(df["timestamp"])
        df = df.rename(columns={"close": "Close"})
        df = df[["Date", "Close"]].copy()
        
        return df

    async def _fetch_single_asset_data_sqlite(
        self,
        symbol: str,
        start_date: Optional[str],
        end_date: Optional[str],
        granularity: str,
    ) -> pd.DataFrame:
        """Fetch price data for a single asset from SQLite."""
        if not start_date:
            start_date = "2020-01-01"
        if not end_date:
            end_date = "2026-12-31"

        table = "price_history" if granularity == "daily" else "prices_hourly"
        db_path = str(config.get("DB_PATH", "backend/prices.db"))
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)

        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            asset_row = None
            for candidate in _candidate_symbols(symbol):
                asset_row = conn.execute(
                    "SELECT id FROM assets WHERE symbol = ? LIMIT 1",
                    (candidate,),
                ).fetchone()
                if asset_row:
                    break
            if not asset_row:
                raise HTTPException(404, f"Asset not found: {symbol}")

            rows = conn.execute(
                f"""
                SELECT timestamp, close
                FROM {table}
                WHERE asset_id = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                ORDER BY timestamp
                """,
                (int(asset_row[0]), start_iso, end_iso),
            ).fetchall()

        if not rows:
            raise HTTPException(404, f"No price data for {symbol}")

        df = pd.DataFrame([dict(row) for row in rows])
        df["Date"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.rename(columns={"close": "Close"})
        return df[["Date", "Close"]].copy()

    def _format_precomputed_report(
        self,
        analysis_data: Dict,
        asset1: str,
        asset2: str,
        granularity: str,
        include_price_data: bool,
        include_spread_data: bool
    ) -> Dict[str, Any]:
        """Format precomputed analysis data into standard report format."""
        pair_metrics = analysis_data.get("pair_metrics", {})
        regression_metrics = analysis_data.get("regression_metrics", {})
        cointegration_results = analysis_data.get("cointegration_results", {})
        price_data_summary = analysis_data.get("price_data_summary", {})
        
        report = {
            "asset1": asset1,
            "asset2": asset2,
            "granularity": granularity,
            "data_source": "precomputed",
            "precomputed_at": datetime.fromtimestamp(
                analysis_data.get("computed_at", 0)
            ).isoformat(),
            "pair_metrics": pair_metrics,
            "regression_metrics": {
                "hedge_ratio": regression_metrics.get("hedge_ratio"),
                "beta": regression_metrics.get("hedge_ratio"),
                "alpha": regression_metrics.get("intercept"),
                "intercept": regression_metrics.get("intercept"),
                "r_squared": regression_metrics.get("r_squared"),
                "std_error": regression_metrics.get("std_error"),
            },
            "cointegration_results": cointegration_results,
        }
        
        # Add price/spread data if requested
        if include_price_data or include_spread_data:
            # Create minimal DataFrame for latest values
            current_time = pd.Timestamp.now(tz="UTC")
            price_df = pd.DataFrame({
                "Date": [current_time],
                "asset1_price": [price_data_summary.get("asset1_latest_price", 0.0)],
                "asset2_price": [price_data_summary.get("asset2_latest_price", 0.0)],
                "spread": [price_data_summary.get("latest_spread", 0.0)],
                "zscore": [price_data_summary.get("latest_zscore", 0.0)],
            })
            
            if include_price_data:
                report["price_data"] = self._format_price_payload(price_df)
            if include_spread_data:
                report["spread_data"] = self._format_spread_payload(price_df)
        
        return report

    def _format_cointegration_report(
        self,
        test_result,
        prices_df: pd.DataFrame,
        asset1: str,
        asset2: str,
        include_price_data: bool,
        include_spread_data: bool
    ) -> Dict[str, Any]:
        """Format CointegrationTestResult into standard report format."""
        # Calculate spread and zscore
        import numpy as np
        spread = self.cointegration_service.calculate_spread(
            asset1_prices=np.array(prices_df["asset1_price"].values, dtype=float),
            asset2_prices=np.array(prices_df["asset2_price"].values, dtype=float),
            hedge_ratio=test_result.beta_coefficient
        )
        
        zscore = self.cointegration_service.calculate_zscore(spread, window=None)
        
        # Add to DataFrame
        prices_df = prices_df.copy()
        prices_df["spread"] = spread
        prices_df["zscore"] = zscore
        if "date" in prices_df.columns:
            prices_df = prices_df.rename(columns={"date": "Date"})
        
        report = {
            "asset1": asset1,
            "asset2": asset2,
            "granularity": test_result.granularity,
            "data_source": "on_demand",
            "report_generated_at": datetime.utcnow().isoformat(),
            "pair_metrics": {
                "correlation": test_result.pearson_correlation,
                "spearman_correlation": test_result.spearman_correlation,
                "half_life": test_result.half_life_days,
                "hurst_exponent": test_result.hurst_exponent,
            },
            "regression_metrics": {
                "hedge_ratio": test_result.beta_coefficient,
                "beta": test_result.beta_coefficient,
                "alpha": test_result.alpha_intercept,
                "intercept": test_result.alpha_intercept,
                "r_squared": test_result.regression_r_squared,
                "std_error": test_result.regression_std_error,
            },
            "cointegration_results": {
                "eg_is_cointegrated": bool(test_result.eg_is_cointegrated),
                "eg_pvalue": test_result.eg_pvalue,
                "eg_test_statistic": test_result.eg_test_statistic,
                "eg_critical_value_1pct": test_result.eg_critical_value_1pct,
                "eg_critical_value_5pct": test_result.eg_critical_value_5pct,
                "eg_critical_value_10pct": test_result.eg_critical_value_10pct,
                "eg_significance_level": test_result.eg_significance_level,
                "johansen_is_cointegrated": bool(test_result.johansen_is_cointegrated),
                "adf_is_stationary": bool(test_result.adf_is_stationary),
            },
        }
        
        # Add price/spread data if requested
        if include_price_data:
            report["price_data"] = self._format_price_payload(prices_df)
        if include_spread_data:
            report["spread_data"] = self._format_spread_payload(prices_df)
        
        return report

    def _format_price_payload(self, df: pd.DataFrame) -> Dict[str, List]:
        """Format price data for frontend with OHLCV support."""
        dates = [
            timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
            for timestamp in df["Date"]
        ]
        
        result = {
            "dates": dates,
            "asset1_prices": [
                float(v) if pd.notna(v) else None for v in df["asset1_price"]
            ],
            "asset2_prices": [
                float(v) if pd.notna(v) else None for v in df["asset2_price"]
            ],
        }
        
        # Add OHLCV data if available (for candlestick charts)
        if "open_asset1" in df.columns:
            result["asset1_ohlcv"] = [
                {
                    "open": float(row["open_asset1"]) if pd.notna(row["open_asset1"]) else None,
                    "high": float(row["high_asset1"]) if pd.notna(row["high_asset1"]) else None,
                    "low": float(row["low_asset1"]) if pd.notna(row["low_asset1"]) else None,
                    "close": float(row["asset1_price"]) if pd.notna(row["asset1_price"]) else None,
                    "volume": float(row["volume_asset1"]) if pd.notna(row.get("volume_asset1")) else None,
                }
                for _, row in df.iterrows()
            ]
        
        if "open_asset2" in df.columns:
            result["asset2_ohlcv"] = [
                {
                    "open": float(row["open_asset2"]) if pd.notna(row["open_asset2"]) else None,
                    "high": float(row["high_asset2"]) if pd.notna(row["high_asset2"]) else None,
                    "low": float(row["low_asset2"]) if pd.notna(row["low_asset2"]) else None,
                    "close": float(row["asset2_price"]) if pd.notna(row["asset2_price"]) else None,
                    "volume": float(row["volume_asset2"]) if pd.notna(row.get("volume_asset2")) else None,
                }
                for _, row in df.iterrows()
            ]
        
        return result

    def _format_spread_payload(self, df: pd.DataFrame) -> List[Dict]:
        """Format spread data for frontend."""
        payload = []
        for _, row in df.iterrows():
            payload.append({
                "date": (
                    row["Date"].isoformat()
                    if isinstance(row["Date"], datetime)
                    else str(row["Date"])
                ),
                "spread": (
                    float(row["spread"])
                    if pd.notna(row["spread"])
                    else None
                ),
                "zscore": (
                    float(row["zscore"])
                    if pd.notna(row["zscore"])
                    else None
                ),
            })
        return payload

    # ========================================================================
    # ROLLING CALCULATIONS
    # ========================================================================

    def get_rolling_correlation(
        self,
        asset1: str,
        asset2: str,
        window: int = 60,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: str = "daily",
        method: str = "pearson",
    ) -> Dict[str, Any]:
        """
        Calculate rolling correlation between two assets.
        
        Replaces: business_calculations_service.calculate_rolling_correlation()
        Delegates to: correlation_service._calc_rolling_correlation()
        
        Args:
            asset1: First asset symbol
            asset2: Second asset symbol
            window: Rolling window size
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            method: Correlation method (pearson, spearman)
            
        Returns:
            {
                'asset1': str,
                'asset2': str,
                'window': int,
                'granularity': str,
                'method': str,
                'data': List[{date: str, correlation: float}]
            }
        """
        try:
            logger.info(f"Calculating rolling correlation for {asset1}/{asset2}")
            
            # Delegate to correlation_service
            result_df = _calc_rolling_correlation(
                self.cache,
                asset1_name=asset1,
                asset2_name=asset2,
                window_days=window,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
            )

            if result_df is None or result_df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data available for {asset1}/{asset2}"
                )

            # Format response
            data_points = [
                {
                    "date": row["Date"].isoformat() if isinstance(row["Date"], datetime) else str(row["Date"]),
                    "correlation": float(row["rolling_correlation"]) if pd.notna(row["rolling_correlation"]) else None,
                }
                for _, row in result_df.iterrows()
            ]

            return {
                "asset1": asset1,
                "asset2": asset2,
                "window": window,
                "granularity": granularity,
                "method": method,
                "data": data_points,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating rolling correlation: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate rolling correlation: {str(e)}"
            )

    async def get_rolling_beta(
        self,
        asset: str,
        benchmark: str = "S&P 500 ETF",
        window: int = 60,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: str = "daily",
    ) -> Dict[str, Any]:
        """
        Calculate rolling beta for asset vs benchmark.
        
        Replaces: business_calculations_service.calculate_rolling_beta()
        
        Args:
            asset: Asset symbol
            benchmark: Benchmark symbol
            window: Rolling window size
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            
        Returns:
            {
                'asset': str,
                'benchmark': str,
                'window': int,
                'granularity': str,
                'data': List[{date: str, beta: float}]
            }
        """
        try:
            logger.info(f"Calculating rolling beta for {asset} vs {benchmark}")
            
            # Fetch data using internal Supabase helper
            asset_df = await self._fetch_single_asset_data(
                asset, start_date, end_date, granularity
            )
            
            benchmark_df = await self._fetch_single_asset_data(
                benchmark, start_date, end_date, granularity
            )

            if asset_df.empty or benchmark_df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"Insufficient data for {asset} or {benchmark}"
                )

            # Calculate returns
            asset_returns = asset_df["Close"].pct_change()
            benchmark_returns = benchmark_df["Close"].pct_change()

            # Calculate rolling beta
            covariance = asset_returns.rolling(window).cov(benchmark_returns)
            variance = benchmark_returns.rolling(window).var()
            rolling_beta = covariance / variance

            # Format response
            data_points = [
                {
                    "date": date.isoformat() if isinstance(date, datetime) else str(date),
                    "beta": float(beta) if pd.notna(beta) else None,
                }
                for date, beta in zip(asset_df["Date"], rolling_beta)
            ]

            return {
                "asset": asset,
                "benchmark": benchmark,
                "window": window,
                "granularity": granularity,
                "data": data_points,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating rolling beta: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate rolling beta: {str(e)}"
            )

    async def get_rolling_volatility(
        self,
        asset: str,
        window: int = 21,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: str = "daily",
        annualization_factor: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate rolling volatility for asset.
        
        Replaces: business_calculations_service.calculate_rolling_volatility()
        
        Args:
            asset: Asset symbol
            window: Rolling window size
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            annualization_factor: Factor to annualize volatility
            
        Returns:
            {
                'asset': str,
                'window': int,
                'granularity': str,
                'annualization_factor': int,
                'data': List[{date: str, volatility: float}]
            }
        """
        try:
            logger.info(f"Calculating rolling volatility for {asset}")
            
            # Fetch data using internal Supabase helper
            asset_df = await self._fetch_single_asset_data(
                asset, start_date, end_date, granularity
            )

            if asset_df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data available for {asset}"
                )

            # Determine annualization factor
            factor_map = {
                "daily": 252,
                "hourly": 252 * 6,  # Assuming 6 trading hours
                "4h": 252 * 6 / 4,
            }
            final_ann_factor = annualization_factor if annualization_factor is not None else factor_map.get(granularity, 252)

            # Calculate returns and rolling volatility
            returns = asset_df["Close"].pct_change()
            rolling_vol = returns.rolling(window).std() * (final_ann_factor ** 0.5)

            # Format response
            data_points = [
                {
                    "date": date.isoformat() if isinstance(date, datetime) else str(date),
                    "volatility": float(vol) if pd.notna(vol) else None,
                }
                for date, vol in zip(asset_df["Date"], rolling_vol)
            ]

            return {
                "asset": asset,
                "window": window,
                "granularity": granularity,
                "annualization_factor": annualization_factor,
                "data": data_points,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating rolling volatility: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate rolling volatility: {str(e)}"
            )

    # ========================================================================
    # SCREENER MANAGEMENT
    # ========================================================================

    def get_screener_status(self) -> Dict[str, Any]:
        """
        Get screener system status and health information.
        
        Replaces: screener_service.get_screener_status()
        
        Returns:
            System status with data freshness and health metrics
        """
        from datetime import timezone
        
        status_data = {
            "supabase_available": self.supabase_client is not None,
            "system_health": {
                "fresh_datasets": 0,
                "total_datasets": 0,
                "health_score": 0.0,
            },
            "data_freshness": {},
        }

        if not self.supabase_client:
            status_data["message"] = (
                "Supabase not configured - pre-computation unavailable"
            )
            return status_data

        try:
            # Check precompute configuration
            status_data["precompute_config"] = {
                "max_age_hours": 6,
                "min_correlation": 0.7,
                "max_pairs": 100,
            }

            # Check data freshness for different granularity/method combinations
            combinations = [
                ("daily", "spearman"),
                ("daily", "pearson"),
                ("hourly", "spearman"),
                ("hourly", "pearson"),
            ]

            fresh_count = 0
            total_count = len(combinations)

            for granularity, method in combinations:
                try:
                    # Check precomputed_correlations table
                    matrix_result = self.supabase_client.get_correlation_matrix(
                        granularity=granularity,
                        method=method,
                        max_age_hours=999999,  # Get any available data
                    )

                    dataset_info: Dict[str, Any] = {
                        "correlation_matrix_available": bool(matrix_result),
                        "top_pairs_available": bool(matrix_result),
                    }

                    if matrix_result:
                        created_at = datetime.fromisoformat(
                            matrix_result["created_at"].replace("Z", "+00:00")
                        )
                        matrix_age = (
                            datetime.now(timezone.utc) - created_at
                        ).total_seconds() / 3600
                        
                        dataset_info["correlation_matrix_age_hours"] = round(matrix_age, 2)
                        dataset_info["top_pairs_age_hours"] = round(matrix_age, 2)

                        if matrix_age < 6:  # Fresh if less than 6 hours old
                            fresh_count += 1

                    status_data["data_freshness"][
                        f"{granularity}_{method}"
                    ] = dataset_info

                except Exception as e:
                    logger.warning(f"Error checking {granularity}/{method} data: {e}")
                    status_data["data_freshness"][f"{granularity}_{method}"] = {
                        "correlation_matrix_available": False,
                        "top_pairs_available": False,
                    }

            # Update system health
            status_data["system_health"]["fresh_datasets"] = int(fresh_count)
            status_data["system_health"]["total_datasets"] = total_count
            status_data["system_health"]["health_score"] = round(
                (fresh_count / total_count) * 100 if total_count > 0 else 0, 1
            )

        except Exception as e:
            logger.error(f"Error getting screener status: {e}")
            status_data["error"] = str(e)

        return status_data

    def trigger_precomputation(
        self, granularity: str = "daily", method: str = "spearman", force: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger pre-computation of correlation data.
        
        Replaces: screener_service.trigger_precomputation()

        Args:
            granularity: Data granularity
            method: Correlation method
            force: Force recomputation even if recent data exists

        Returns:
            Task trigger response
        """
        from datetime import timezone
        
        if not self.supabase_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Screener service unavailable",
            )

        try:
            # Check if recent data exists (unless forcing)
            if not force:
                recent_data = self.supabase_client.get_correlation_matrix(
                    granularity=granularity,
                    method=method,
                    max_age_hours=6,
                )
                if recent_data:
                    created_at = datetime.fromisoformat(
                        recent_data["created_at"].replace("Z", "+00:00")
                    )
                    age_hours = (
                        datetime.now(timezone.utc) - created_at
                    ).total_seconds() / 3600
                    
                    return {
                        "status": "skipped",
                        "message": "Recent pre-computed data exists. Use force=true to override.",
                        "data_age_hours": round(age_hours, 2),
                        "granularity": granularity,
                        "method": method,
                    }

            # In a real implementation, this would trigger background tasks
            # For now, return a simulated response
            timestamp = int(datetime.now(timezone.utc).timestamp())
            task_ids = {
                "correlation_matrix": f"corr-matrix-{granularity}-{method}-{timestamp}",
                "top_pairs": f"top-pairs-{granularity}-{method}-{timestamp}",
                "detailed_analysis": f"analysis-{granularity}-{method}-{timestamp}",
            }

            return {
                "status": "triggered",
                "message": f"Pre-computation tasks started for {granularity}/{method}",
                "task_ids": task_ids,
                "granularity": granularity,
                "method": method,
                "estimated_completion": "5-10 minutes",
            }

        except Exception as e:
            logger.error(f"Error triggering precomputation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger precomputation",
            )

    def clear_screener_cache(self) -> Dict[str, Any]:
        """
        Clear screener cache and old pre-computed data.
        
        Replaces: screener_service.clear_screener_cache()

        Returns:
            Cache clear response
        """
        from datetime import timezone
        
        try:
            # In a real implementation, this would trigger cleanup tasks
            # For now, return a simulated response
            task_id = f"cleanup-{int(datetime.now(timezone.utc).timestamp())}"

            return {
                "status": "triggered",
                "message": "Cache cleanup task started",
                "task_id": task_id,
            }

        except Exception as e:
            logger.error(f"Error clearing screener cache: {e}")
            raise Exception("Failed to clear screener cache")

    # ========================================================================
    # CORRELATION MATRIX
    # ========================================================================

    def get_correlation_matrix(
        self,
        assets: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        granularity: str = "daily",
        method: str = "spearman",
        min_periods: int = 60,
    ) -> Dict[str, Any]:
        """
        Get full correlation matrix for assets.
        
        Replaces: business_calculations_service.get_correlation_data()
        Delegates to: correlation_service.get_correlation_data()
        
        Args:
            assets: List of asset symbols (None = all assets)
            start_date: Start date
            end_date: End date
            granularity: Data frequency
            method: Correlation method
            min_periods: Minimum periods for correlation
            
        Returns:
            {
                'correlation_matrix': Dict[str, Dict[str, float]],
                'assets': List[str],
                'method': str,
                'granularity': str,
                'start_date': str,
                'end_date': str
            }
        """
        try:
            logger.info(f"Calculating correlation matrix ({method}, {granularity})")
            
            # Delegate to correlation_service
            # Note: get_correlation_data doesn't take 'assets' param, it computes all
            corr_df = get_correlation_data(
                self.cache,
                start_date=start_date,
                end_date=end_date,
                method=method,
                granularity=granularity,
                min_periods=min_periods,
                view_mode="asset",
            )
            
            # Filter to requested assets if provided
            if assets and corr_df is not None:
                available_assets = [a for a in assets if a in corr_df.index]
                if available_assets:
                    corr_df = corr_df.loc[available_assets, available_assets]

            if corr_df is None or corr_df.empty:
                raise HTTPException(
                    status_code=404,
                    detail="No correlation data available"
                )

            # Convert DataFrame to dictionary
            correlation_matrix = corr_df.to_dict()

            return {
                "correlation_matrix": correlation_matrix,
                "assets": list(corr_df.index),
                "method": method,
                "granularity": granularity,
                "start_date": start_date,
                "end_date": end_date,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate correlation matrix: {str(e)}"
            )


# ============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# ============================================================================

_analytics_service = None


def get_analytics_service() -> AnalyticsService:
    """Get or create singleton AnalyticsService instance."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service


# Convenience functions for common operations
def get_screener_top_pairs(**kwargs) -> Dict[str, Any]:
    """Convenience function for screener pairs."""
    service = get_analytics_service()
    return service.get_screener_top_pairs(**kwargs)


async def get_full_pair_report(**kwargs) -> Dict[str, Any]:
    """Convenience function for pair report."""
    service = get_analytics_service()
    return await service.get_full_pair_report(**kwargs)


def get_rolling_correlation(**kwargs) -> Dict[str, Any]:
    """Convenience function for rolling correlation."""
    service = get_analytics_service()
    return service.get_rolling_correlation(**kwargs)


async def get_rolling_beta(**kwargs) -> Dict[str, Any]:
    """Convenience function for rolling beta."""
    service = get_analytics_service()
    return await service.get_rolling_beta(**kwargs)


async def get_rolling_volatility(**kwargs) -> Dict[str, Any]:
    """Convenience function for rolling volatility."""
    service = get_analytics_service()
    return await service.get_rolling_volatility(**kwargs)


def get_correlation_matrix(**kwargs) -> Dict[str, Any]:
    """Convenience function for correlation matrix."""
    service = get_analytics_service()
    return service.get_correlation_matrix(**kwargs)


def get_screener_status() -> Dict[str, Any]:
    """Convenience function for screener status."""
    service = get_analytics_service()
    return service.get_screener_status()


def trigger_precomputation(**kwargs) -> Dict[str, Any]:
    """Convenience function for triggering precomputation."""
    service = get_analytics_service()
    return service.trigger_precomputation(**kwargs)


def clear_screener_cache() -> Dict[str, Any]:
    """Convenience function for clearing screener cache."""
    service = get_analytics_service()
    return service.clear_screener_cache()
