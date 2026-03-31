"""
Shared data access utilities for services.

This module provides common data fetching functions used across multiple services
to avoid duplication and ensure consistency.
"""

import logging
from typing import Dict, List, Optional
from api.services.data_standardization_service import data_standardization_service

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


async def get_price_data_from_db(
    supabase_client, symbol: str, days: int, granularity: str = "daily"
) -> Optional[List[Dict]]:
    """
    Fetch price data from Supabase for a given symbol.

    Shared utility used by multiple services to avoid code duplication.
    Used by: analytics_computer.py, data_quality_service.py

    Args:
        supabase_client: Supabase client instance (can be direct client or wrapped)
        symbol: Asset symbol
        days: Number of days of historical data
        granularity: "daily" or "intraday"

    Returns:
        List of price records or None if error
    """
    try:
        from datetime import datetime, timedelta
        from api.utils.datetime_normalization import normalize_datetime_iso

        # Handle both direct Supabase client and wrapped client
        client = (
            supabase_client
            if hasattr(supabase_client, "table")
            else supabase_client.client
        )

        # Get asset ID
        asset_response = (
            client.table("assets").select("id").eq("symbol", symbol).single().execute()
        )

        if not asset_response.data:
            logger.warning(f"Asset not found: {symbol}")
            return None

        asset_id = asset_response.data["id"]
        cutoff_date = datetime.now() - timedelta(days=days)
        start_iso = normalize_datetime_iso(cutoff_date, assume="start") or cutoff_date.isoformat()

        # Determine table
        table = (
            "intraday_price_history" if granularity == "intraday" else "price_history"
        )

        # Fetch price data with date filter
        price_response = (
            client.table(table)
            .select("timestamp, close")
            .eq("asset_id", asset_id)
            .gte("timestamp", start_iso)
            .order("timestamp")
            .execute()
        )

        # Convert to DataFrame and standardize for downstream consumers
        import pandas as pd

        rows = price_response.data or []
        if not rows:
            return []

        df = pd.DataFrame(rows)
        # Standardize to ensure consistent schema before returning
        df_std = data_standardization_service.standardize_price_data(
            df=df, symbol=symbol, data_type="price_history", validate=False
        )

        return df_std.to_dict("records") if not df_std.empty else []

    except Exception as e:
        logger.error(f"Failed to get price data for {symbol}: {e}")
        return None


def validate_price_dataframe(
    df: pd.DataFrame, required_columns: Optional[List[str]] = None
) -> bool:
    """
    Validate that a price DataFrame has required structure.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names (default: ['Date', 'Close'])

    Returns:
        True if valid, False otherwise
    """
    if df is None or df.empty:
        return False

    if required_columns is None:
        required_columns = ["Date", "Close"]

    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        logger.warning(f"DataFrame missing required columns: {missing_cols}")
        return False

    return True


def align_price_series(
    series1: pd.Series, series2: pd.Series, method: str = "inner"
) -> tuple[pd.Series, pd.Series]:
    """
    Align two price series on their index (timestamps).

    Args:
        series1: First price series
        series2: Second price series
        method: Alignment method ("inner", "outer", "left", "right")

    Returns:
        Tuple of aligned series
    """
    aligned_df = pd.DataFrame({"series1": series1, "series2": series2})

    if method == "inner":
        aligned_df = aligned_df.dropna()

    return aligned_df["series1"], aligned_df["series2"]


def calculate_returns(prices: pd.Series, method: str = "log") -> pd.Series:
    """
    Calculate returns from price series.

    Args:
        prices: Price series
        method: "log" for log returns, "simple" for simple returns

    Returns:
        Returns series
    """
    if method == "log":
        # ensure pandas Series is returned
        return pd.Series(np.log(prices / prices.shift(1)), index=prices.index)
    else:  # simple
        return prices.pct_change()
