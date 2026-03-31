"""
Correlation analysis service for HedgeVision API.

Contains functions for correlation calculations, rolling correlations, and related metrics.
"""

import logging
import os
import sys

import numpy as np
import pandas as pd
from api.utils.assets import asset_sectors, name_to_symbol

# Add parent directory to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Constants (moved from deprecated query_service)
TIMEOUT = 3600  # Cache timeout in seconds
DEFAULT_START_DATE_STR = "2020-01-01"
DEFAULT_END_DATE_STR = "2026-12-31"


def _fetch_price_data(symbol: str, start_date: str, end_date: str, granularity: str) -> pd.DataFrame:
    """
    Fetch price data directly from Supabase.
    
    Replaces deprecated query_service.get_cached_data().
    Uses direct Supabase queries for cleaner architecture.
    """
    from api.utils.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    if not supabase:
        logger.warning(f"Supabase not available for {symbol}")
        return pd.DataFrame()
    
    try:
        # Get asset_id
        asset_response = (
            supabase.client.table("assets")
            .select("id")
            .eq("symbol", symbol)
            .single()
            .execute()
        )
        
        if not asset_response.data:
            logger.warning(f"Asset not found: {symbol}")
            return pd.DataFrame()
        
        asset_id = asset_response.data["id"]
        
        # Determine table based on granularity
        if granularity == "daily":
            table = "price_history"
        elif str(granularity).lower() in ("4h", "4hr", "4hrly", "four_hour", "fourhour"):
            table = "intraday_price_history"
        else:
            table = "prices_hourly"
        
        # Normalize temporal bounds (accept date/datetime strings)
        from api.utils.datetime_normalization import normalize_datetime_iso
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)

        # Fetch prices with normalized ISO8601 bounds
        price_response = (
            supabase.client.table(table)
            .select("timestamp, open, high, low, close, volume")
            .eq("asset_id", asset_id)
            .gte("timestamp", start_iso)
            .lte("timestamp", end_iso)
            .order("timestamp")
            .execute()
        )
        
        if not price_response.data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(list(price_response.data))
        df["Date"] = pd.to_datetime(df["timestamp"])
        df = df.rename(columns={"close": "Close"})
        df = df[["Date", "Close"]].copy()
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


# Simple replacement for get_sorted_correlation_matrix
def get_sorted_correlation_matrix(corr_df):
    """Sort correlation matrix by average correlation values."""
    if corr_df is None or corr_df.empty:
        return corr_df

    # Calculate average correlation for each asset (excluding self-correlation)
    avg_corr = corr_df.apply(lambda x: x[x != 1.0].mean(), axis=1)
    # Sort by average correlation (descending)
    sorted_indices = avg_corr.sort_values(ascending=False).index

    # Return sorted matrix
    return corr_df.loc[sorted_indices, sorted_indices]


# Set up logging
logger = logging.getLogger(__name__)




def get_correlation_data(
    cache,
    start_date=None,
    end_date=None,
    method: str = "spearman",
    granularity: str = "daily",
    min_periods: int = 10,
    view_mode: str = "asset",
):
    """
    Compute a pair-wise correlation matrix (log returns) for all assets.

    Always uses a union time-grid + per-pair NaN masking.
    Caches the result for `TIMEOUT` seconds.

    Returns:
        pd.DataFrame | None: Sorted correlation matrix when at least two assets have
        overlapping observations; otherwise ``None``.
    """

    # ------------------------------------------------------------------ #
    # 1) Standardise dates
    # ------------------------------------------------------------------ #
    effective_start = pd.to_datetime(start_date or DEFAULT_START_DATE_STR, utc=True)
    effective_end = pd.to_datetime(end_date or DEFAULT_END_DATE_STR, utc=True)

    @cache.memoize(timeout=TIMEOUT)
    def _get_corr(start_arg, end_arg, method_arg, granularity_arg, min_periods_arg, view_mode_arg):

        logger.info(
            "Computing %s pair-wise correlation (%s) from %s to %s (view_mode=%s)",
            granularity_arg,
            method_arg,
            start_arg,
            end_arg,
            view_mode_arg,
        )

        # -------------------------------------------------------------- #
        # 2) Pull & clean price series
        # -------------------------------------------------------------- #
        price_series = {}
        for asset, symbol_name_in_db in sorted(
            name_to_symbol.items()
        ):  # Ensure using the correct symbol for DB lookup
            if granularity_arg == "hourly":
                # Fetch hourly data directly from Supabase
                df_asset_hourly = _fetch_price_data(
                    symbol_name_in_db, start_arg, end_arg, granularity="hourly"
                )

                if (
                    df_asset_hourly is None
                    or df_asset_hourly.empty
                    or "Close" not in df_asset_hourly.columns
                    or df_asset_hourly["Close"].isnull().all()
                ):
                    logger.warning(
                        f"Skipping {asset} for hourly correlation – no valid 'Close' data after fetch and resample."
                    )
                    continue

                s = df_asset_hourly.set_index("Date")["Close"].rename(asset)
                # Basic check for positive prices, though much cleaning is now in DataManager
                s = s.where(s > 0)
                if s.dropna().empty:
                    logger.warning(
                        f"Skipping {asset} for hourly correlation – no positive 'Close' prices."
                    )
                    continue

            elif granularity_arg == "daily":
                df_asset_daily = _fetch_price_data(
                    symbol_name_in_db, start_arg, end_arg, granularity="daily"
                )
                if (
                    df_asset_daily is None
                    or df_asset_daily.empty
                    or "Close" not in df_asset_daily.columns
                    or df_asset_daily["Close"].isnull().all()
                ):
                    logger.warning(
                        f"Skipping {asset} for daily correlation – no valid 'Close' data."
                    )
                    continue

                s = df_asset_daily.set_index("Date")["Close"].rename(asset)
                # Daily data specific cleaning (like normalization) is handled by DataManager.get_daily_data
                # Basic check for positive prices
                s = s.where(s > 0)
                if s.dropna().empty:
                    logger.warning(
                        f"Skipping {asset} for daily correlation – no positive 'Close' prices."
                    )
                    continue
            else:
                logger.error(
                    f"Unsupported granularity: {granularity_arg} for asset {asset}"
                )
                continue

            # Ensure the series 's' is not empty and contains at least two non-NaN values for variance/correlation calculation
            if s.dropna().size < 2:
                logger.warning(
                    f"Skipping {asset} – fewer than 2 non-NaN data points for {granularity_arg} series."
                )
                continue

            price_series[asset] = s

        if len(price_series) < 2:
            logger.warning(
                "Need at least 2 assets with valid data – correlation aborted"
            )
            return None

        # -------------------------------------------------------------- #
        # 3) Build union price matrix
        # -------------------------------------------------------------- #
        price_df = pd.concat(price_series, axis=1).sort_index()
        # (asset names are already the columns)

        # -------------------------------------------------------------- #
        # 4) Convert to log-returns (preserve DataFrame type explicitly)
        # -------------------------------------------------------------- #
        returns_df = pd.DataFrame(
            np.log(price_df / price_df.shift(1)),
            index=price_df.index,
            columns=price_df.columns,
        )

        if view_mode_arg == "sector":
            logger.info(f"Aggregating {len(returns_df.columns)} assets into sectors")
            sector_returns = {}
            for sector, assets in asset_sectors.items():
                sector_assets = [
                    asset for asset in assets if asset in returns_df.columns
                ]
                if sector_assets:
                    sector_returns[sector] = returns_df[sector_assets].mean(axis=1)
                    logger.info(f"Sector '{sector}': {len(sector_assets)} assets")
            returns_df = pd.DataFrame(sector_returns)
            logger.info(f"After sector aggregation, DataFrame has {len(returns_df.columns)} columns: {list(returns_df.columns)}")

        # -------------------------------------------------------------- #
        # 5) Compute overlap counts & correlations in one pass
        # -------------------------------------------------------------- #
        valid_obs = (~returns_df.isna()).astype("int")
        overlap_matrix = valid_obs.T @ valid_obs  # common sample count

        corr_raw = returns_df.corr(
            method=method_arg, min_periods=min_periods_arg
        )  # Renamed 'corr' to 'corr_raw'

        # Mask pairs that don't meet the overlap threshold
        # THIS IS THE CRITICAL STEP TO EXAMINE FOR HOURLY
        corr_masked = corr_raw.where(
            overlap_matrix >= min_periods_arg
        )  # Renamed 'corr' to 'corr_masked'

        if corr_masked.isna().all().all():
            logger.warning("No valid correlations – result is empty")
            return None

        # Guarantee diagonal == 1
        np.fill_diagonal(corr_masked.values, 1.0)

        # -------------------------------------------------------------- #
        # 6) Pretty-sort for heat-map and return
        # -------------------------------------------------------------- #
        return get_sorted_correlation_matrix(corr_masked)

    # Call the cached worker
    return _get_corr(effective_start, effective_end, method, granularity, min_periods, view_mode)


def calculate_rolling_correlation(
    cache,
    asset1_name,
    asset2_name,
    window_days=30,
    start_date=None,
    end_date=None,
    granularity="daily",
):
    """Calculate rolling correlation between two assets using log returns.

    The first data point in the returned series corresponds to the 'start_date',
    achieved by fetching data with a buffer period.

    Args:
        cache: The Flask-Cache instance
        asset1_name (str): First asset name
        asset2_name (str): Second asset name
        window_days (int): Number of days for the rolling window (default: 30). For hourly, this is # of hours.
        start_date (str or datetime, optional): Start date/datetime for filtering data. Defaults will be handled by get_cached_data.
        end_date (str or datetime, optional): End date/datetime for filtering data. Defaults will be handled by get_cached_data.
        granularity (str): Data granularity ('daily' or 'hourly'). Defaults to 'daily'.

    Returns:
        pandas.DataFrame: DataFrame with Date and rolling correlation values
    """
    # Standardize input parameters
    effective_start_date = (
        start_date if start_date is not None else DEFAULT_START_DATE_STR
    )
    effective_end_date = end_date if end_date is not None else DEFAULT_END_DATE_STR

    @cache.memoize(timeout=TIMEOUT)
    def _get_rolling_correlation(
        asset1_name_arg,
        asset2_name_arg,
        window_arg,
        start_date_arg,
        end_date_arg,
        granularity_arg,
    ):
        # Define early so it's always bound for the except block
        empty_df = pd.DataFrame(
            {
                "Date": pd.Series(dtype="datetime64[ns, UTC]"),
                "Correlation": pd.Series(dtype="float64"),
            }
        )
        try:
            log_prefix = f"{window_arg}-{'hour' if granularity_arg == 'hourly' else 'day'} rolling correlation ({granularity_arg})"
            logger.info(
                f"Calculating {log_prefix} between {asset1_name_arg} and {asset2_name_arg} for period {start_date_arg} to {end_date_arg}"
            )

            # 1) Convert dates to datetime with UTC timezone
            orig_start_dt = pd.to_datetime(start_date_arg)
            orig_end_dt = pd.to_datetime(end_date_arg)

            orig_start_dt = (
                orig_start_dt.tz_localize("UTC")
                if orig_start_dt.tzinfo is None
                else orig_start_dt.tz_convert("UTC")
            )
            orig_end_dt = (
                orig_end_dt.tz_localize("UTC")
                if orig_end_dt.tzinfo is None
                else orig_end_dt.tz_convert("UTC")
            )

            # 2) Add buffer period to ensure we have enough data for the first window
            # Need window_arg + 1 days to calculate returns for window_arg days
            buffer_periods = 2 * window_arg + 1

            if granularity_arg == "daily":
                buf_delta = pd.Timedelta(days=buffer_periods)
            else:  # hourly
                buf_delta = pd.Timedelta(hours=buffer_periods)

            fetch_start_dt = orig_start_dt - buf_delta
            fetch_end_dt = orig_end_dt

            logger.info(
                f"Effective fetch window: {fetch_start_dt} to {fetch_end_dt} (Window: {window_arg})"
            )

            # 3) Fetch data for both assets
            try:
                symbol1 = name_to_symbol[asset1_name_arg]
                symbol2 = name_to_symbol[asset2_name_arg]
            except KeyError as e:
                logger.error(f"Asset name not found in name_to_symbol map: {e}")
                return empty_df

            df1 = _fetch_price_data(
                symbol1,
                start_date=fetch_start_dt,
                end_date=fetch_end_dt,
                granularity=granularity_arg,
            )
            df2 = _fetch_price_data(
                symbol2,
                start_date=fetch_start_dt,
                end_date=fetch_end_dt,
                granularity=granularity_arg,
            )

            # 4) Validate data availability
            if (
                df1.empty
                or df2.empty
                or "Date" not in df1.columns
                or "Close" not in df1.columns
                or "Date" not in df2.columns
                or "Close" not in df2.columns
            ):
                logger.warning(
                    f"Missing data for {asset1_name_arg} or {asset2_name_arg}"
                )
                return empty_df

            # 5) Prepare data for correlation calculation
            # Set index and create combined DataFrame
            df1 = df1.set_index("Date")
            df2 = df2.set_index("Date")

            combined_df = pd.DataFrame(
                {asset1_name_arg: df1["Close"], asset2_name_arg: df2["Close"]}
            )

            combined_df = combined_df.sort_index()

            # 6) Calculate log returns - CRITICAL IMPROVEMENT
            returns_df = pd.DataFrame(
                np.log(combined_df / combined_df.shift(1)),
                index=combined_df.index,
            ).dropna()

            if returns_df.empty or len(returns_df) < window_arg:
                logger.warning(
                    f"Insufficient data points after calculating returns ({len(returns_df)} points, need {window_arg})"
                )
                return empty_df

            # 7) Calculate rolling correlation on log returns
            # Allow min_periods to be slightly less than window for sparse data
            min_periods = max(
                int(window_arg * 0.8), 2
            )  # At least 80% of window or 2 points

            rolling_corr = (
                returns_df[asset1_name_arg]
                .rolling(window=window_arg, min_periods=min_periods)
                .corr(returns_df[asset2_name_arg])
            )

            # 8) Package into a DataFrame and clean up
            result_df = pd.DataFrame(
                {"Date": rolling_corr.index, "Correlation": rolling_corr.values}
            )

            result_df = result_df.dropna()

            # 9) Trim to requested date range
            if not result_df.empty:
                result_df = result_df[
                    (result_df["Date"] >= orig_start_dt)
                    & (result_df["Date"] <= orig_end_dt)
                ].reset_index(drop=True)

            if result_df.empty:
                logger.warning(
                    f"No correlation data available after trimming to requested date range {orig_start_dt} to {orig_end_dt}"
                )
                return empty_df  # Good

            # --- Save to CSV before returning ---
            try:
                data_folder = "data"
                if not os.path.exists(data_folder):
                    os.makedirs(data_folder)

                # Format the end_date_arg for the filename (e.g., YYYYMMDD)
                # orig_end_dt is already a timezone-aware datetime object here
                date_str_for_filename = orig_end_dt.strftime("%Y%m%d")

                # Sanitize asset names for filename (optional, but good practice)
                sane_asset1 = "".join(
                    c if c.isalnum() else "_" for c in asset1_name_arg
                )
                sane_asset2 = "".join(
                    c if c.isalnum() else "_" for c in asset2_name_arg
                )

                csv_filename = (
                    f"{sane_asset1}_vs_{sane_asset2}_{date_str_for_filename}.csv"
                )
                csv_filepath = os.path.join(data_folder, csv_filename)

                result_df.to_csv(csv_filepath, index=False)
                logger.info(
                    f"Successfully saved rolling correlation data to {csv_filepath}"
                )

            except Exception as csv_e:
                logger.error(
                    f"Failed to save rolling correlation data to CSV for {asset1_name_arg} vs {asset2_name_arg}: {str(csv_e)}",
                    exc_info=True,
                )
            # --- End of CSV saving ---

            logger.info(
                f"Successfully calculated {log_prefix} with {len(result_df)} data points for range {orig_start_dt} to {orig_end_dt}"
            )
            return result_df

        except Exception as e:
            logger.error(
                f"Error calculating rolling correlation: {str(e)}", exc_info=True
            )
            return empty_df

    return _get_rolling_correlation(
        asset1_name,
        asset2_name,
        window_days,
        effective_start_date,
        effective_end_date,
        granularity,
    )


# ============================================================================
# CorrelationService Class - Wrapper for periodic tasks
# ============================================================================


class CorrelationService:
    """
    Service class for correlation calculations with Supabase storage.
    Used by GitHub Actions scheduled workflows.
    """

    def __init__(self, supabase_client):
        """Initialize with Supabase client for fetching prices."""
        self.supabase_client = supabase_client
        self.logger = logging.getLogger(__name__)
        # DataManager no longer needed - using _fetch_price_data directly

    def compute_correlation_matrix(
        self,
        asset_symbols: list[str],
        granularity: str = "daily",
        method: str = "pearson",
        lookback_days: int = 252,
    ) -> dict:
        """
        Compute correlation matrix for given assets and store in database.

        Args:
            asset_symbols: List of asset symbols to analyze
            granularity: 'daily' or 'hourly'
            method: 'pearson' or 'spearman'
            lookback_days: Number of days to look back

        Returns:
            Dictionary of correlation values keyed by asset pairs
        """
        self.logger.info(
            f"Computing {method} correlation matrix for {len(asset_symbols)} assets "
            f"(granularity={granularity}, lookback={lookback_days} days)"
        )

        try:
            if not asset_symbols:
                self.logger.warning("No asset symbols provided for correlation")
                return {}

            if granularity not in ("daily", "hourly"):
                self.logger.error(
                    f"Unsupported granularity: {granularity}. Use 'daily' or 'hourly'."
                )
                return {}

            if method not in ("pearson", "spearman"):
                self.logger.error(
                    f"Unsupported method: {method}. Use 'pearson' or 'spearman'."
                )
                return {}

            # Determine date range
            end_dt = pd.Timestamp.utcnow()
            # Ensure UTC timezone
            if getattr(end_dt, "tz", None) is None:
                end_dt = end_dt.tz_localize("UTC")
            else:
                end_dt = end_dt.tz_convert("UTC")
            # Normalize to midnight for daily for consistency
            if granularity == "daily":
                end_dt = end_dt.normalize()
            start_dt = end_dt - pd.Timedelta(days=lookback_days)

            # Fetch close series for each symbol using _fetch_price_data
            price_series: dict[str, pd.Series] = {}
            for symbol in sorted(set(asset_symbols)):
                try:
                    # Use _fetch_price_data for both daily and hourly
                    df = _fetch_price_data(
                        symbol=symbol,
                        start_date=start_dt.strftime("%Y-%m-%d"),
                        end_date=end_dt.strftime("%Y-%m-%d"),
                        granularity=granularity
                    )

                    if (
                        df is None
                        or df.empty
                        or "Date" not in df.columns
                        or "Close" not in df.columns
                    ):
                        self.logger.info(
                            f"Skipping {symbol}: no valid {granularity} data in window"
                        )
                        continue

                    s = df.set_index("Date")["Close"].astype(float)
                    s = s.where(s > 0).dropna()
                    if s.size < 2:
                        self.logger.info(
                            f"Skipping {symbol}: <2 data points after cleaning"
                        )
                        continue
                    price_series[symbol] = s

                except Exception as fe:
                    self.logger.warning(
                        f"Failed fetching data for {symbol}: {fe}", exc_info=False
                    )
                    continue

            if len(price_series) < 2:
                self.logger.warning(
                    "Insufficient assets with valid data to compute correlations"
                )
                return {}

            # Align on union index and compute log returns
            price_df = pd.concat(price_series, axis=1).sort_index()
            returns_df = pd.DataFrame(
                np.log(price_df / price_df.shift(1)),
                index=price_df.index,
                columns=price_df.columns,
            )

            # Compute correlation matrix
            min_periods = max(10, int(lookback_days * 0.2))
            corr_df = returns_df.corr(method=method, min_periods=min_periods)

            # Guard: if empty or all NaN
            if corr_df is None or corr_df.empty or corr_df.isna().all().all():
                self.logger.warning("Computed correlation matrix is empty/NaN")
                return {}

            # Ensure diagonal = 1.0
            for i, col in enumerate(corr_df.columns):
                corr_df.iat[i, i] = 1.0

            # Build plain dict for storage
            corr_dict: dict[str, dict[str, float]] = {}
            for r in corr_df.index:
                row: dict[str, float] = {}
                for c in corr_df.columns:
                    try:
                        val = corr_df.at[r, c]
                        # Skip NaNs explicitly
                        if pd.isna(val):
                            continue
                        row[str(c)] = float(val)  # type: ignore[arg-type]
                    except Exception:
                        # Skip problematic cell but continue building matrix
                        continue
                corr_dict[str(r)] = row

            # Prepare payload for Supabase
            matrix_payload = {
                "granularity": granularity,
                "method": method,
                "start_date": start_dt.to_pydatetime().isoformat(),
                "end_date": end_dt.to_pydatetime().isoformat(),
                "correlation_matrix": corr_dict,
                "assets": list(corr_df.columns.astype(str)),
            }

            stored = False
            try:
                if self.supabase_client is not None:
                    stored = self.supabase_client.store_correlation_matrix(
                        matrix_payload
                    )
                else:
                    self.logger.error("Supabase client is None; skipping storage")
            except Exception as se:
                self.logger.error(
                    f"Failed to store correlation matrix in Supabase: {se}",
                    exc_info=True,
                )

            self.logger.info(
                f"Computed {method} correlation for {len(corr_df.columns)} assets; stored={stored}"
            )
            return corr_dict

        except Exception as e:
            self.logger.error(
                f"Error computing correlation matrix: {e}", exc_info=True
            )
            return {}
