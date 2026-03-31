"""
Data Standardization Service
Ensures all price data is consistently formatted and validated system-wide.

NOTE: With yfinance as the sole provider, this service is greatly simplified.
YFinance already provides clean, standardized data. This service now primarily:
1. Validates data quality (missing values, outliers, gaps)
2. Ensures DB schema compatibility
3. Provides pair analysis utilities

Legacy multi-provider normalization logic is preserved for reference but rarely needed.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataStandardizationService:
    """
    Handles data validation, standardization, and quality checks
    for price data across the HedgeVision platform.
    """

    # Standard column names
    STANDARD_COLUMNS = {
        "date": "date",
        "timestamp": "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "adjusted_close": "adjusted_close",
        "symbol": "symbol",
    }

    # Required columns for different data types
    REQUIRED_COLUMNS = {
        "price_history": ["date", "close"],
        "ohlcv": ["date", "open", "high", "low", "close", "volume"],
        "adjusted": ["date", "close", "adjusted_close"],
    }

    def __init__(self):
        self.logger = logger

    def standardize_price_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        data_type: str = "price_history",
        validate: bool = True,
    ) -> pd.DataFrame:
        """
        Standardize price data DataFrame to consistent format.

        Args:
            df: Input DataFrame with price data
            symbol: Asset symbol
            data_type: Type of data ('price_history', 'ohlcv', 'adjusted')
            validate: Whether to validate data quality

        Returns:
            Standardized DataFrame
        """
        if df is None or df.empty:
            self.logger.warning(f"Empty DataFrame provided for {symbol}")
            return pd.DataFrame()

        try:
            # 1. Normalize column names
            df = self._normalize_column_names(df)

            # 2. Ensure required columns exist
            df = self._ensure_required_columns(df, data_type)

            # 3. Add symbol if not present
            if "symbol" not in df.columns:
                df["symbol"] = symbol

            # 4. Standardize date/timestamp
            df = self._standardize_datetime(df)

            # 5. Standardize numeric columns
            df = self._standardize_numeric_columns(df)

            # 6. Remove duplicates
            df = self._remove_duplicates(df)

            # 7. Sort by date
            df = df.sort_values("date").reset_index(drop=True)

            # 8. Validate data quality
            if validate:
                df = self._validate_and_clean(df, symbol)

            # 9. Add metadata columns
            df = self._add_metadata(df)

            self.logger.info(f"Standardized {len(df)} records for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error standardizing data for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to standard format"""
        # Common column name variations
        column_mappings = {
            "Date": "date",
            "DATE": "date",
            "Timestamp": "timestamp",
            "DateTime": "date",
            "Open": "open",
            "OPEN": "open",
            "High": "high",
            "HIGH": "high",
            "Low": "low",
            "LOW": "low",
            "Close": "close",
            "CLOSE": "close",
            "Price": "close",
            "PRICE": "close",
            "Volume": "volume",
            "VOLUME": "volume",
            "Adj Close": "adjusted_close",
            "Adj_Close": "adjusted_close",
            "AdjClose": "adjusted_close",
            "adjusted": "adjusted_close",
            "Symbol": "symbol",
            "SYMBOL": "symbol",
            "Ticker": "symbol",
            "ticker": "symbol",
        }

        # Apply mappings
        df = df.rename(columns=column_mappings)

        # Convert all column names to lowercase
        df.columns = df.columns.str.lower().str.strip()

        return df

    def _ensure_required_columns(
        self, df: pd.DataFrame, data_type: str
    ) -> pd.DataFrame:
        """Ensure all required columns are present"""
        required = self.REQUIRED_COLUMNS.get(data_type, ["date", "close"])

        for col in required:
            if col not in df.columns:
                # Allow timestamp/datetime to be standardized later into 'date'
                if col == "date" and any(x in df.columns for x in ["timestamp", "datetime"]):
                    continue
                if col == "adjusted_close" and "close" in df.columns:
                    # If adjusted_close missing, use close as fallback
                    df["adjusted_close"] = df["close"]
                elif col in ["open", "high", "low"] and "close" in df.columns:
                    # If OHLC missing, use close as approximation
                    df[col] = df["close"]
                elif col == "volume":
                    # If volume missing, set to 0
                    df["volume"] = 0
                else:
                    raise ValueError(f"Required column '{col}' missing from DataFrame")

        return df

    def _standardize_datetime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize date/timestamp column"""
        # Find date column
        date_col = None
        for col in ["date", "timestamp", "datetime"]:
            if col in df.columns:
                date_col = col
                break

        if date_col is None:
            # Try to find any column that looks like a date
            for col in df.columns:
                if "date" in col.lower() or "time" in col.lower():
                    date_col = col
                    break

        if date_col is None:
            raise ValueError("No date/timestamp column found in DataFrame")

        # Convert to datetime
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        # Rename to standard 'date' column
        if date_col != "date":
            df = df.rename(columns={date_col: "date"})

        # Remove timezone for consistency
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)

        # Remove any rows with invalid dates
        df = df.dropna(subset=["date"])

        return df

    def _standardize_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize numeric columns (prices, volume)"""
        numeric_cols = ["open", "high", "low", "close", "volume", "adjusted_close"]

        for col in numeric_cols:
            if col in df.columns:
                # Convert to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors="coerce")

                # For price columns, remove negative values
                if col != "volume":
                    df.loc[df[col] < 0, col] = np.nan

                # For volume, set negatives to 0
                if col == "volume":
                    df.loc[df[col] < 0, col] = 0

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate timestamps, keeping the last entry"""
        if "date" in df.columns:
            # Check for duplicates
            duplicates = df.duplicated(subset=["date"], keep="last")
            num_duplicates = duplicates.sum()

            if num_duplicates > 0:
                self.logger.warning(f"Removing {num_duplicates} duplicate timestamps")
                df = df[~duplicates].copy()

        return df

    def _validate_and_clean(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Validate data quality and clean outliers"""
        if df.empty:
            return df

        original_len = len(df)

        # 1. Remove rows with missing close prices
        df = df.dropna(subset=["close"])

        # 2. Remove zero prices (likely data errors)
        df = df[df["close"] > 0]

        # 3. Detect and handle outliers (price spikes > 50% in one day)
        if len(df) > 1:
            price_changes = df["close"].pct_change().abs()
            outliers = price_changes > 0.5  # 50% change threshold

            if outliers.sum() > 0:
                self.logger.warning(
                    f"{symbol}: Found {outliers.sum()} potential outliers "
                    f"(>50% price change)"
                )
                # Don't remove, just flag for review
                df["potential_outlier"] = outliers

        # 4. Validate OHLC relationships
        if all(col in df.columns for col in ["open", "high", "low", "close"]):
            # High should be >= all others
            df.loc[df["high"] < df["close"], "high"] = df["close"]
            df.loc[df["high"] < df["open"], "high"] = df["open"]

            # Low should be <= all others
            df.loc[df["low"] > df["close"], "low"] = df["close"]
            df.loc[df["low"] > df["open"], "low"] = df["open"]

        # 5. Log data quality
        if len(df) < original_len:
            removed = original_len - len(df)
            self.logger.info(
                f"{symbol}: Removed {removed} invalid records "
                f"({removed/original_len*100:.1f}%)"
            )

        return df

    def _add_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add metadata columns"""
        # Data quality score (0-100)
        if not df.empty:
            df["data_quality"] = 100.0  # Can be adjusted based on validation results

            # Add processing timestamp
            df["processed_at"] = datetime.now()

        return df

    def check_data_completeness(
        self, df: pd.DataFrame, expected_days: int = 252, granularity: str = "daily"
    ) -> Dict:
        """
        Check data completeness and identify gaps.

        Returns:
            Dict with completeness metrics
        """
        if df.empty:
            return {
                "is_complete": False,
                "completeness_pct": 0.0,
                "missing_days": expected_days,
                "gaps": [],
                "date_range": None,
            }

        # Ensure date column exists and is sorted
        if "date" not in df.columns:
            return {"is_complete": False, "error": "No date column found"}

        df = df.sort_values("date")
        date_range = (df["date"].min(), df["date"].max())

        # Calculate expected trading days
        if granularity == "daily":
            # Assume 252 trading days per year
            days_diff = (date_range[1] - date_range[0]).days
            expected_records = int(days_diff * 252 / 365)
        else:
            expected_records = expected_days

        actual_records = len(df)
        completeness_pct = (
            (actual_records / expected_records * 100) if expected_records > 0 else 0
        )

        # Find gaps (periods > 5 days between consecutive records)
        gaps = []
        if len(df) > 1:
            date_diffs = df["date"].diff()
            large_gaps = date_diffs > timedelta(days=5)

            if large_gaps.any():
                gap_indices = df[large_gaps].index
                for idx in gap_indices:
                    prev_date = df.loc[idx - 1, "date"]
                    curr_date = df.loc[idx, "date"]
                    gap_days = (curr_date - prev_date).days
                    gaps.append(
                        {
                            "start": prev_date.strftime("%Y-%m-%d"),
                            "end": curr_date.strftime("%Y-%m-%d"),
                            "days": gap_days,
                        }
                    )

        return {
            "is_complete": completeness_pct >= 95,
            "completeness_pct": round(completeness_pct, 2),
            "expected_records": expected_records,
            "actual_records": actual_records,
            "missing_records": max(0, expected_records - actual_records),
            "gaps": gaps,
            "date_range": {
                "start": date_range[0].strftime("%Y-%m-%d"),
                "end": date_range[1].strftime("%Y-%m-%d"),
                "days": (date_range[1] - date_range[0]).days,
            },
        }

    def merge_price_data(
        self, dfs: List[pd.DataFrame], priority_order: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Merge price data from multiple sources, handling conflicts.

        Args:
            dfs: List of DataFrames to merge (must have 'date' and 'close' columns)
            priority_order: Optional list of source names for conflict resolution

        Returns:
            Merged DataFrame
        """
        if not dfs:
            return pd.DataFrame()

        # Filter out empty DataFrames
        dfs = [df for df in dfs if not df.empty]

        if not dfs:
            return pd.DataFrame()

        if len(dfs) == 1:
            return dfs[0].copy()

        # Merge all DataFrames on date
        result = dfs[0].copy()

        for df in dfs[1:]:
            # Merge on date, using suffix to distinguish sources
            result = pd.merge(result, df, on="date", how="outer", suffixes=("", "_new"))

            # For overlapping dates, keep existing value (or apply priority)
            for col in ["close", "open", "high", "low", "volume"]:
                if f"{col}_new" in result.columns:
                    # Fill NaN values in original column with new values
                    result[col] = result[col].fillna(result[f"{col}_new"])
                    result = result.drop(columns=[f"{col}_new"])

        # Sort and clean
        result = result.sort_values("date").reset_index(drop=True)
        result = self._remove_duplicates(result)

        return result

    def create_pair_dataframe(
        self,
        asset1_df: pd.DataFrame,
        asset2_df: pd.DataFrame,
        asset1_symbol: str,
        asset2_symbol: str,
    ) -> pd.DataFrame:
        """
        Create a standardized DataFrame for pair analysis.

        Returns DataFrame with columns: [date, asset1_price, asset2_price]
        """
        # Standardize both DataFrames
        df1 = self.standardize_price_data(asset1_df, asset1_symbol)
        df2 = self.standardize_price_data(asset2_df, asset2_symbol)

        if df1.empty or df2.empty:
            self.logger.error(f"Empty data for pair {asset1_symbol}/{asset2_symbol}")
            return pd.DataFrame()

        # Merge on date (inner join to get common dates)
        merged = pd.merge(
            df1[["date", "close"]],
            df2[["date", "close"]],
            on="date",
            how="inner",
            suffixes=("_1", "_2"),
        )

        # Rename columns to standard format
        merged = merged.rename(
            columns={"close_1": "asset1_price", "close_2": "asset2_price"}
        )

        # Sort by date
        merged = merged.sort_values("date").reset_index(drop=True)

        self.logger.info(
            f"Created pair DataFrame for {asset1_symbol}/{asset2_symbol}: "
            f"{len(merged)} common dates"
        )

        return merged

    def validate_pair_data_quality(
        self, pair_df: pd.DataFrame, min_records: int = 252
    ) -> Dict:
        """
        Validate data quality for pair analysis.

        Returns:
            Dict with validation results
        """
        issues = []
        warnings = []

        # Check minimum records
        if len(pair_df) < min_records:
            issues.append(
                f"Insufficient data: {len(pair_df)} records "
                f"(minimum {min_records} required)"
            )

        # Check for missing values
        missing = pair_df[["asset1_price", "asset2_price"]].isnull().sum()
        if missing.any():
            issues.append(f"Missing values: {missing.to_dict()}")

        # Check for zero or negative prices
        if (pair_df["asset1_price"] <= 0).any():
            issues.append("Asset1 has zero or negative prices")
        if (pair_df["asset2_price"] <= 0).any():
            issues.append("Asset2 has zero or negative prices")

        # Check for data gaps
        if len(pair_df) > 1:
            date_diffs = pair_df["date"].diff().dt.days
            max_gap = date_diffs.max()
            if max_gap > 10:
                warnings.append(f"Large gap detected: {max_gap} days")

        # Calculate overall quality score
        quality_score = 100.0
        quality_score -= len(issues) * 20  # -20 for each issue
        quality_score -= len(warnings) * 10  # -10 for each warning
        quality_score = max(0, min(100, quality_score))

        return {
            "is_valid": len(issues) == 0,
            "quality_score": quality_score,
            "num_records": len(pair_df),
            "issues": issues,
            "warnings": warnings,
        }


# Global instance
data_standardization_service = DataStandardizationService()
