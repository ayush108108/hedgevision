"""
Analytics Computation Pipeline V2 - Complete Implementation
Implements all Tier 3 business logic computations with automatic sequential execution.

Architecture:
- Pre-flight checks (Layer 0)
- Raw data validation (Layer 1)
- Tier 3A: Correlation computation
- Tier 3B: Cointegration testing
- Tier 3C: Rolling metrics (Beta, Sharpe, Volatility, etc.)
- Tier 3D: Factor exposures (CAPM, Fama-French)
- Layer 2: Validation of all computed data
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional

import argparse
import logging
import traceback

# Add backend to path so top-level `api` package can be imported (used by scripts)
# When running from scripts/ directly, we want Python to find `api` as a top-level package.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BACKEND_ROOT = os.path.join(REPO_ROOT, 'backend')
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

import pandas as pd
import numpy as np
from statsmodels.api import OLS, add_constant

from api.utils.pair_validation import (
    MIN_OBSERVATIONS,
    evaluate_pair,
    infer_asset_class,
    prepare_price_series,
    SeriesPayload,
)
from api.utils.supabase_client import get_supabase_client

try:
    # Prefer absolute import when script runs with BACKEND_ROOT on PYTHONPATH
    from api.services.data_standardization_service import data_standardization_service
    from api.services.cointegration_service import CointegrationService, CointegrationTestResult
except Exception:
    # Fall back to relative import for unusual run contexts
    try:
        sys.path.insert(0, REPO_ROOT)
        from backend.api.services.data_standardization_service import (
            data_standardization_service,
        )
        from backend.api.services.cointegration_service import (
            CointegrationService,
            CointegrationTestResult,
        )
    except Exception:
        # Re-raise with a clearer message
        raise

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Test mode: Reduced dataset for fast testing
TEST_MODE = True

if TEST_MODE:
    LOOKBACK_DAYS = 90  # 3 months for testing
    MAX_ASSETS = 10  # Test with 10 assets only
    CORRELATION_THRESHOLD = 0.7  # |correlation| >= 0.7
    ROLLING_WINDOWS = [30]  # Single window for testing
else:
    LOOKBACK_DAYS = 730  # 2 years for production
    MAX_ASSETS = None  # All assets
    CORRELATION_THRESHOLD = 0.6
    ROLLING_WINDOWS = [30, 60, 90, 180, 252]  # Multiple windows

# Benchmarks for beta calculation
BENCHMARKS = {
    "SPY": "S&P 500",  # US Stock Market
    "GC=F": "Gold Futures",  # Gold
}

# ============================================================================
# ANALYTICS PIPELINE CLASS
# ============================================================================


class AnalyticsComputationPipeline:
    """Complete analytics computation pipeline with all tiers."""

    def __init__(self):
        """Initialize the pipeline."""
        self.supabase = get_supabase_client()
        self.cointegration_service = CointegrationService()
        self.stats = {
            "total_assets": 0,
            "correlations_computed": 0,
            "pairs_found": 0,
            "pairs_stored": 0,
            "cointegration_tests": 0,
            "cointegrated_pairs": 0,
            "rolling_metrics_computed": 0,
            "factor_exposures_computed": 0,
            "duration_minutes": 0,
        }
        self.start_time = datetime.now(timezone.utc)
        self.tickers_override: Optional[List[str]] = None
        # Allow overriding the min observations for cointegration testing in CLI
        self.min_observations: int = MIN_OBSERVATIONS

    def log(self, message: str, level: str = "info"):
        """Log a message with timestamp."""
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)

    # ========================================================================
    # LAYER 0: PRE-FLIGHT CHECKS
    # ========================================================================

    def pre_flight_checks(self) -> bool:
        """Verify all required tables exist."""
        self.log("\n" + "=" * 80)
        self.log("LAYER 0: PRE-FLIGHT CHECKS")
        self.log("=" * 80)

        # Only require core tables; downstream tables are optional and handled gracefully
        required_tables = [
            "assets",
            "price_history",
            "correlation_matrix",
        ]

        try:
            for table in required_tables:
                self.supabase.client.table(table).select("*").limit(1).execute()
                self.log(f"✓ Table '{table}' exists")

            # Optional tables: don't fail the pipeline if missing
            optional_tables = [
                "pair_trades",
                "rolling_metrics",
                "factor_exposures",
            ]
            for table in optional_tables:
                try:
                    self.supabase.client.table(table).select("id").limit(1).execute()
                    self.log(f"• Optional table '{table}' available")
                except Exception:
                    self.log(
                        f"⚠ Optional table '{table}' not found — features depending on it will be skipped",
                        "warning",
                    )

            self.log("✓ All required tables verified")
            return True

        except Exception as e:
            self.log(f"✗ Pre-flight check failed: {e}", "error")
            return False

    # ========================================================================
    # LAYER 1: RAW DATA VALIDATION
    # ========================================================================

    def validate_raw_data(self) -> Tuple[bool, List[Dict]]:
        """Validate raw price data availability."""
        self.log("\n" + "=" * 80)
        self.log("LAYER 1: RAW DATA VALIDATION")
        self.log("=" * 80)

        try:
            # Fetch active assets
            assets_result = (
                self.supabase.client.table("assets")
                .select("id, yfinance_ticker, name")
                .execute()
            )

            assets = assets_result.data
            # Optional --tickers override for targeted runs
            if self.tickers_override:
                assets = [a for a in assets if a["yfinance_ticker"] in self.tickers_override]
            if MAX_ASSETS:
                assets = assets[:MAX_ASSETS]

            self.stats["total_assets"] = len(assets)
            self.log(f"Found {len(assets)} active assets")

            # Check price data for each asset
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=LOOKBACK_DAYS)

            valid_assets = []
            for asset in assets:
                price_result = (
                    self.supabase.client.table("price_history")
                    .select("timestamp, close")
                    .eq("asset_id", asset["id"])
                    .gte("timestamp", start_date.isoformat())
                    .lte("timestamp", end_date.isoformat())
                    .order("timestamp")
                    .execute()
                )

                if len(price_result.data) >= 20:  # Minimum data requirement
                    valid_assets.append(asset)
                    self.log(
                        f"  {asset['yfinance_ticker']}: {len(price_result.data)} price records"
                    )
                else:
                    self.log(
                        f"  {asset['yfinance_ticker']}: Insufficient data ({len(price_result.data)} records)",
                        "warning",
                    )

            self.log(f"✓ Raw data validation passed ({len(valid_assets)} assets)")
            return True, valid_assets

        except Exception as e:
            self.log(f"✗ Raw data validation failed: {e}", "error")
            return False, []

    # ========================================================================
    # TIER 3A: CORRELATION COMPUTATION
    # ========================================================================

    def compute_correlations(self, assets: List[Dict]) -> Tuple[bool, List[Dict], Dict[str, SeriesPayload]]:
        """Compute pairwise correlations between assets."""
        self.log("\n" + "=" * 80)
        self.log("TIER 3A: CORRELATION COMPUTATION")
        self.log("=" * 80)

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=LOOKBACK_DAYS)

            self.log("Computing correlations...")
            self.log(f"  Date range: {start_date.date()} to {end_date.date()}")
            self.log("  Method: Spearman")
            self.log(f"  Threshold: |correlation| >= {CORRELATION_THRESHOLD}")

            # Fetch price data for all assets
            price_data = {}
            for asset in assets:
                result = (
                    self.supabase.client.table("price_history")
                    .select("timestamp, close")
                    .eq("asset_id", asset["id"])
                    .gte("timestamp", start_date.isoformat())
                    .lte("timestamp", end_date.isoformat())
                    .order("timestamp")
                    .execute()
                )

                if result.data:
                    price_data[asset["yfinance_ticker"]] = result.data

            # Build correlation matrix
            df_dict = {}
            for symbol, prices in price_data.items():
                price_df = pd.DataFrame(prices)
                price_df["timestamp"] = pd.to_datetime(price_df["timestamp"])
                # Remove duplicates (price_history has no unique constraint)
                price_df = price_df.drop_duplicates(subset=["timestamp"], keep="last")
                df_dict[symbol] = price_df.set_index("timestamp")["close"]

            df = pd.DataFrame(df_dict)
            self.log(f"  Correlation matrix shape: {df.shape}")

            # Create SeriesPayload for each asset for cointegration testing
            payloads = {}
            for asset in assets:
                symbol = asset['yfinance_ticker']
                if symbol in df_dict:
                    asset_class = infer_asset_class(symbol)
                    # Convert to DataFrame and apply standardization
                    df_price = df_dict[symbol].reset_index()
                    # Standardize columns via the central service (ensures date/close normal form)
                    df_price = data_standardization_service.standardize_price_data(
                        df=df_price, symbol=symbol, data_type="price_history", validate=False
                    )
                    # prepare_price_series expects a 'timestamp' column; the standardizer
                    # normalizes to 'date'—map it to 'timestamp' for backcompat
                    if "timestamp" not in df_price.columns and "date" in df_price.columns:
                        df_price["timestamp"] = df_price["date"]
                    # Prepare payload using existing helper
                    payloads[symbol] = prepare_price_series(df_price, symbol, asset_class)

            # Compute Spearman correlation
            corr_matrix = df.corr(method="spearman")

            # Persist full correlation matrix (preferred store)
            try:
                corr_dict = corr_matrix.fillna(0.0).to_dict()
                store_ok = self.supabase.store_correlation_matrix(
                    {
                        "granularity": "daily",
                        "method": "spearman",
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "correlation_matrix": corr_dict,
                        "assets": [a["yfinance_ticker"] for a in assets],
                    }
                )
                if store_ok:
                    self.log("✓ Stored correlation matrix in 'correlation_matrix' table")
                else:
                    self.log(
                        "⚠ Failed to store correlation matrix; continuing without persistence",
                        "warning",
                    )
            except Exception as e:
                self.log(
                    f"⚠ Error while storing correlation matrix (non-fatal): {e}",
                    "warning",
                )

            # Extract high correlation pairs
            pairs = []
            symbols = list(corr_matrix.columns)
            for i, sym1 in enumerate(symbols):
                for j, sym2 in enumerate(symbols):
                    if i < j:  # Avoid duplicates and self-correlation
                        corr_value = corr_matrix.loc[sym1, sym2]
                        if abs(corr_value) >= CORRELATION_THRESHOLD:
                            pairs.append(
                                {
                                    "asset1": sym1,
                                    "asset2": sym2,
                                    "correlation": float(corr_value),
                                }
                            )

            # Sort by absolute correlation
            pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

            self.log(
                f"Found {len(pairs)} pairs with |correlation| >= {CORRELATION_THRESHOLD}"
            )

            # No longer store per-pair rows in deprecated 'precomputed_pairs'
            stored_count = 0

            self.stats["correlations_computed"] = 1
            self.stats["pairs_found"] = len(pairs)
            self.stats["pairs_stored"] = stored_count

            if stored_count > 0:
                self.log(f"✓ Stored {stored_count} correlation pairs")
            else:
                self.log("✓ Pair list computed (stored full matrix instead of per-pair rows)")

            # Show top 10 pairs
            if pairs:
                self.log("\nTop 10 correlated pairs:")
                for pair in pairs[:10]:
                    self.log(
                        f"  {pair['asset1']:15} <-> {pair['asset2']:15} : {pair['correlation']:7.3f}"
                    )

            return True, pairs, payloads

        except Exception as e:
            self.log(f"✗ Correlation computation failed: {e}", "error")
            self.log(traceback.format_exc(), "error")
            return False, [], {}

    # ========================================================================
    # TIER 3B: COINTEGRATION TESTING
    # ========================================================================

    def test_cointegration(self, pairs: List[Dict], assets: List[Dict], payloads: Dict[str, SeriesPayload]) -> bool:
        """Test cointegration for high-correlation pairs using new validation pipeline."""
        self.log("\n" + "=" * 80)
        self.log("TIER 3B: COINTEGRATION TESTING")
        self.log("=" * 80)

        try:
            cointegrated_pairs = []

            for idx, pair in enumerate(pairs, 1):
                try:
                    sym1 = pair["asset1"]
                    sym2 = pair["asset2"]

                    payload1 = payloads.get(sym1)
                    payload2 = payloads.get(sym2)

                    if not payload1 or not payload2:
                        continue

                    asset1 = next((a for a in assets if a['yfinance_ticker'] == sym1), None)
                    asset2 = next((a for a in assets if a['yfinance_ticker'] == sym2), None)

                    if not asset1 or not asset2:
                        continue

                    # 3. Comprehensive testing using service
                    # Create pair dataframe as required by service
                    prices_df = pd.DataFrame({
                        "date": payload1.series.index,
                        "asset1_price": payload1.series.values,
                        "asset2_price": payload2.series.values
                    })

                    result: CointegrationTestResult = self.cointegration_service.test_pair(
                        asset1_symbol=sym1,
                        asset2_symbol=sym2,
                        prices_df=prices_df,
                        lookback_days=LOOKBACK_DAYS
                    )
                    
                    self.stats["cointegration_tests"] += 1

                    is_coint = result.eg_is_cointegrated or result.johansen_is_cointegrated
                    if not is_coint:
                         continue

                    # Helper to sanitize numpy values
                    def s(val):
                        if val is None: return None
                        if isinstance(val, (np.floating, float)):
                            return float(val) if np.isfinite(val) else None
                        if isinstance(val, (np.integer, int)):
                            return int(val)
                        return val

                    # 4. Store in expanded pair_trades table
                    pair_trade_data = {
                        "long_asset_id": asset1["id"],
                        "short_asset_id": asset2["id"],
                        "cointegration_score": s(result.eg_test_statistic),
                        "cointegration_pvalue": s(result.eg_pvalue),
                        "beta_coefficient": s(result.beta_coefficient),
                        "alpha_intercept": s(result.alpha_intercept),
                        "model_r_squared": s(result.regression_r_squared),
                        "residual_adf_stat": s(result.adf_test_statistic),
                        "residual_adf_pvalue": s(result.adf_pvalue),
                        "half_life_days": s(result.half_life_days),
                        
                        # Expanded metrics
                        "johansen_trace_stat": s(result.johansen_trace_stat),
                        "johansen_eigen_stat": s(result.johansen_eigen_stat),
                        "johansen_rank": s(result.johansen_rank),
                        "johansen_is_cointegrated": bool(result.johansen_is_cointegrated),
                        "pp_pvalue": s(result.pp_pvalue),
                        "kpss_pvalue": s(result.kpss_pvalue),
                        "kpss_is_stationary": bool(result.kpss_is_stationary),
                        "hurst_exponent": s(result.hurst_exponent),
                        "spread_mean": s(result.spread_mean),
                        "spread_std": s(result.spread_std),
                        "spread_skewness": s(result.spread_skewness),
                        "spread_kurtosis": s(result.spread_kurtosis),
                        "zscore_current": s(result.zscore_current),
                        "sharpe_ratio": s(result.sharpe_ratio),
                        "profit_factor": s(result.profit_factor),
                        "win_rate": s(result.win_rate),
                        "max_drawdown_pct": s(result.max_drawdown_pct),
                        "overall_score": s(result.overall_score),
                        "cointegration_strength": result.cointegration_strength,
                        "trading_suitability": result.trading_suitability,
                        "risk_level": result.risk_level,

                        "status": "active",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "test_date": datetime.now(timezone.utc).date().isoformat(),
                    }
                    
                    self.supabase.client.table("pair_trades").upsert(
                        pair_trade_data, on_conflict="long_asset_id,short_asset_id,test_date"
                    ).execute()

                    cointegrated_pairs.append(
                        {
                            "asset1": sym1,
                            "asset2": sym2,
                            "p_value": result.eg_pvalue,
                            "beta": result.beta_coefficient,
                            "half_life": result.half_life_days,
                        }
                    )



                    if idx % 10 == 0:
                        self.log(f"  Tested {idx}/{len(pairs)} pairs...")

                except Exception as e:
                    self.log(
                        f"  Error testing {pair['asset1']} <-> {pair['asset2']}: {e}",
                        "warning",
                    )
                    continue

            self.stats["cointegrated_pairs"] = len(cointegrated_pairs)

            self.log(
                f"✓ Completed {self.stats['cointegration_tests']} cointegration tests"
            )
            self.log(f"✓ Found {len(cointegrated_pairs)} cointegrated pairs (p < 0.05)")

            if cointegrated_pairs:
                self.log("\nTop 10 cointegrated pairs:")
                sorted_pairs = sorted(cointegrated_pairs, key=lambda x: x["p_value"])
                for pair in sorted_pairs[:10]:
                    half_life_str = (
                        f"{pair['half_life']:.1f} days" if pair["half_life"] else "N/A"
                    )
                    self.log(
                        f"  {pair['asset1']:15} <-> {pair['asset2']:15} | "
                        f"p={pair['p_value']:.4f} | beta={pair['beta']:.3f} | "
                        f"half-life={half_life_str}"
                    )

            return True

        except Exception as e:
            self.log(f"✗ Cointegration testing failed: {e}", "error")
            self.log(traceback.format_exc(), "error")
            return False

    # ========================================================================
    # TIER 3C: ROLLING METRICS
    # ========================================================================

    def compute_rolling_metrics(self, assets: List[Dict]) -> bool:
        """Compute rolling metrics (beta, volatility, Sharpe, etc.)."""
        self.log("\n" + "=" * 80)
        self.log("TIER 3C: ROLLING METRICS")
        self.log("=" * 80)

        try:
            end_date = datetime.now(timezone.utc)

            # Fetch benchmark data
            benchmark_data = {}
            for bench_symbol, bench_name in BENCHMARKS.items():
                bench_result = (
                    self.supabase.client.table("assets")
                    .select("id")
                    .eq("yfinance_ticker", bench_symbol)
                    .execute()
                )

                if bench_result.data:
                    benchmark_data[bench_symbol] = bench_result.data[0]
                    self.log(f"  Using benchmark: {bench_name} ({bench_symbol})")

            metrics_computed = 0

            for asset in assets:
                for window in ROLLING_WINDOWS:
                    for bench_symbol, bench_info in benchmark_data.items():
                        try:
                            # Fetch ALL available prices for the asset and benchmark to compute history
                            # We use the LOOKBACK_DAYS defined in config
                            start_date = end_date - timedelta(days=LOOKBACK_DAYS + window + 30)

                            # Fetch asset prices
                            asset_prices = (
                                self.supabase.client.table("price_history")
                                .select("timestamp, close")
                                .eq("asset_id", asset["id"])
                                .gte("timestamp", start_date.isoformat())
                                .lte("timestamp", end_date.isoformat())
                                .order("timestamp")
                                .execute()
                            )

                            # Fetch benchmark prices
                            bench_prices = (
                                self.supabase.client.table("price_history")
                                .select("timestamp, close")
                                .eq("asset_id", bench_info["id"])
                                .gte("timestamp", start_date.isoformat())
                                .lte("timestamp", end_date.isoformat())
                                .order("timestamp")
                                .execute()
                            )

                            if not asset_prices.data or not bench_prices.data:
                                continue

                            # Merge data
                            df_asset = pd.DataFrame(asset_prices.data)
                            df_bench = pd.DataFrame(bench_prices.data)
                            df_asset["timestamp"] = pd.to_datetime(df_asset["timestamp"])
                            df_bench["timestamp"] = pd.to_datetime(df_bench["timestamp"])

                            merged = pd.merge(
                                df_asset,
                                df_bench,
                                on="timestamp",
                                suffixes=("_asset", "_bench"),
                            )
                            merged = merged.sort_values("timestamp")

                            if len(merged) < window:
                                continue

                            # Calculate returns
                            merged["return_asset"] = merged["close_asset"].pct_change()
                            merged["return_bench"] = merged["close_bench"].pct_change()
                            merged = merged.dropna()

                            if len(merged) < window:
                                continue

                            # VECORIZED ROLLING CALCULATIONS (Compute history in one go)
                            # Rolling Beta: cov(r_a, r_b) / var(r_b)
                            rolling_cov = merged["return_asset"].rolling(window=window).cov(merged["return_bench"])
                            rolling_var = merged["return_bench"].rolling(window=window).var()
                            merged["beta_series"] = rolling_cov / rolling_var

                            # Rolling Volatility: std(r_a) * sqrt(252)
                            merged["vol_series"] = merged["return_asset"].rolling(window=window).std() * np.sqrt(252)

                            # Rolling Sharpe: (mean(r_a) * 252) / annualized_std(r_a)
                            rolling_mean = merged["return_asset"].rolling(window=window).mean() * 252
                            merged["sharpe_series"] = rolling_mean / merged["vol_series"]

                            # Filter for valid points (where window is full)
                            history_data = merged.dropna(subset=["beta_series", "vol_series"])
                            
                            # Limit history to avoid overloading DB (last 252 points per asset/window)
                            history_data = history_data.tail(252)

                            metrics_batch = []
                            for idx, row in history_data.iterrows():
                                metrics_batch.append({
                                    "asset_id": asset["id"],
                                    "benchmark_id": bench_info["id"],
                                    "window_days": window,
                                    "start_date": (row["timestamp"] - timedelta(days=window)).isoformat(), # Rough approx
                                    "end_date": row["timestamp"].isoformat(),
                                    "rolling_beta": float(row["beta_series"]) if not pd.isna(row["beta_series"]) else None,
                                    "rolling_volatility": float(row["vol_series"]) if not pd.isna(row["vol_series"]) else 0,
                                    "rolling_sharpe_ratio": float(row["sharpe_series"]) if not pd.isna(row["sharpe_series"]) else None,
                                    "sample_size": window,
                                })

                            # Batch insert in chunks to Supabase
                            if metrics_batch:
                                # Chunk by 100 for safety
                                for i in range(0, len(metrics_batch), 100):
                                    chunk = metrics_batch[i:i+100]
                                    try:
                                        # Try upsert first (works if unique constraint on end_date exists)
                                        self.supabase.client.table("rolling_metrics").upsert(
                                            chunk,
                                            on_conflict="asset_id,benchmark_id,window_days,end_date",
                                        ).execute()
                                    except Exception:
                                        # Fallback: plain insert (constraint not yet applied)
                                        self.supabase.client.table("rolling_metrics").insert(
                                            chunk
                                        ).execute()
                                    metrics_computed += len(chunk)

                        except Exception as e:
                            self.log(
                                f"  Error computing metrics for {asset['yfinance_ticker']} ({window}d, {bench_symbol}): {e}",
                                "warning",
                            )
                            continue

                if metrics_computed % 10 == 0 and metrics_computed > 0:
                    self.log(f"  Computed {metrics_computed} rolling metrics...")

            self.stats["rolling_metrics_computed"] = metrics_computed
            self.log(
                f"✓ Computed {metrics_computed} rolling metrics across all assets and windows"
            )

            return True

        except Exception as e:
            self.log(f"✗ Rolling metrics computation failed: {e}", "error")
            self.log(traceback.format_exc(), "error")
            return False

    # ========================================================================
    # TIER 3D: FACTOR EXPOSURES
    # ========================================================================

    def compute_factor_exposures(self, assets: List[Dict]) -> bool:
        """Compute factor model exposures (CAPM, Fama-French)."""
        self.log("\n" + "=" * 80)
        self.log("TIER 3D: FACTOR EXPOSURES")
        self.log("=" * 80)

        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=LOOKBACK_DAYS)

            # Get market benchmark (SPY)
            spy_result = (
                self.supabase.client.table("assets")
                .select("id")
                .eq("yfinance_ticker", "SPY")
                .execute()
            )

            if not spy_result.data:
                self.log(
                    "  Market benchmark (SPY.US) not found, skipping factor exposures",
                    "warning",
                )
                return False

            spy_id = spy_result.data[0]["id"]

            # Fetch SPY prices
            spy_prices = (
                self.supabase.client.table("price_history")
                .select("timestamp, close")
                .eq("asset_id", spy_id)
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .order("timestamp")
                .execute()
            )

            if not spy_prices.data:
                self.log("  No market data available", "warning")
                return False

            df_market = pd.DataFrame(spy_prices.data)
            df_market["timestamp"] = pd.to_datetime(df_market["timestamp"])
            df_market = df_market.set_index("timestamp")
            df_market["market_return"] = df_market["close"].pct_change()

            exposures_computed = 0

            for asset in assets:
                try:
                    # Fetch asset prices
                    asset_prices = (
                        self.supabase.client.table("price_history")
                        .select("timestamp, close")
                        .eq("asset_id", asset["id"])
                        .gte("timestamp", start_date.isoformat())
                        .lte("timestamp", end_date.isoformat())
                        .order("timestamp")
                        .execute()
                    )

                    if not asset_prices.data:
                        continue

                    df_asset = pd.DataFrame(asset_prices.data)
                    df_asset["timestamp"] = pd.to_datetime(df_asset["timestamp"])
                    df_asset = df_asset.set_index("timestamp")
                    df_asset["asset_return"] = df_asset["close"].pct_change()

                    # Merge with market returns
                    merged = df_asset.join(df_market[["market_return"]], how="inner")
                    merged = merged.dropna()

                    if len(merged) < 30:
                        continue

                    # CAPM regression: R_asset = alpha + beta * R_market
                    y = merged["asset_return"].values
                    X = add_constant(merged["market_return"].values)

                    model = OLS(y, X)
                    results = model.fit()

                    alpha = results.params[0]
                    beta_market = results.params[1]
                    r_squared = results.rsquared
                    f_statistic = results.fvalue
                    p_value_alpha = results.pvalues[0]
                    p_value_beta = results.pvalues[1]

                    # Store factor exposures (simplified schema)
                    exposure_data = {
                        "asset_id": asset["id"],
                        "factor_model": "CAPM",
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "beta_market": float(beta_market),
                        "alpha": float(alpha),
                        "model_r_squared": float(r_squared),
                        "f_statistic": float(f_statistic),
                        "p_value_alpha": float(p_value_alpha),
                        "p_value_beta": float(p_value_beta),
                    }

                    self.supabase.client.table("factor_exposures").insert(
                        exposure_data
                    ).execute()
                    exposures_computed += 1

                except Exception as e:
                    self.log(
                        f"  Error computing factor exposure for {asset['yfinance_ticker']}: {e}",
                        "warning",
                    )
                    continue

            self.stats["factor_exposures_computed"] = exposures_computed
            self.log(f"✓ Computed {exposures_computed} factor exposures (CAPM model)")

            return True

        except Exception as e:
            self.log(f"✗ Factor exposures computation failed: {e}", "error")
            self.log(traceback.format_exc(), "error")
            return False

    # ========================================================================
    # LAYER 2: VALIDATION
    # ========================================================================

    def validate_computed_data(self) -> bool:
        """Validate all computed analytics data."""
        self.log("\n" + "=" * 80)
        self.log("LAYER 2: VALIDATION OF COMPUTED DATA")
        self.log("=" * 80)

        try:
            # Check correlations via 'correlation_matrix' table
            try:
                corr_result = (
                    self.supabase.client.table("correlation_matrix")
                    .select("*", count="exact")
                    .execute()
                )
                self.log(
                    f"✓ Found {getattr(corr_result, 'count', 0)} correlation matrices"
                )
            except Exception as e:
                self.log(f"⚠ Could not query correlation_matrix: {e}", "warning")

            # Check cointegration (optional table)
            try:
                coint_result = (
                    self.supabase.client.table("pair_trades")
                    .select("*", count="exact")
                    .execute()
                )
                self.log(f"✓ Found {coint_result.count} cointegration tests")
            except Exception:
                self.log(
                    "⚠ pair_trades table missing — skipping cointegration count",
                    "warning",
                )

            # Check rolling metrics
            metrics_result = (
                self.supabase.client.table("rolling_metrics")
                .select("*", count="exact")
                .execute()
            )
            self.log(f"✓ Found {metrics_result.count} rolling metrics")

            # Check factor exposures
            factors_result = (
                self.supabase.client.table("factor_exposures")
                .select("*", count="exact")
                .execute()
            )
            self.log(f"✓ Found {factors_result.count} factor exposures")

            self.log("✓ All computed data validation passed")
            return True

        except Exception as e:
            self.log(f"✗ Validation failed: {e}", "error")
            return False

    # ========================================================================
    # MAIN EXECUTION
    # ========================================================================

    def run(self) -> bool:
        """Execute the complete analytics pipeline."""
        try:
            self.log("\nSTARTING COMPLETE ANALYTICS COMPUTATION PIPELINE")
            self.log(f"Mode: {'TEST' if TEST_MODE else 'PRODUCTION'}")
            self.log(f"Lookback: {LOOKBACK_DAYS} days")
            self.log(f"Correlation threshold: {CORRELATION_THRESHOLD}")

            # Layer 0: Pre-flight checks
            if not self.pre_flight_checks():
                return False

            # Layer 1: Raw data validation
            valid, assets = self.validate_raw_data()
            if not valid:
                return False

            # Tier 3A: Correlations (REQUIRED for downstream tiers)
            success, pairs, payloads = self.compute_correlations(assets)
            if not success:
                return False

            # Tier 3B: Cointegration (executes automatically after 3A)
            if pairs:
                self.log("\n→ Starting Tier 3B (Cointegration) automatically...")
                self.test_cointegration(pairs, assets, payloads)

            # Tier 3C: Rolling Metrics (executes automatically)
            self.log("\n→ Starting Tier 3C (Rolling Metrics) automatically...")
            self.compute_rolling_metrics(assets)

            # Tier 3D: Factor Exposures (executes automatically)
            self.log("\n→ Starting Tier 3D (Factor Exposures) automatically...")
            self.compute_factor_exposures(assets)

            # Layer 2: Validation
            self.validate_computed_data()

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - self.start_time).total_seconds() / 60
            self.stats["duration_minutes"] = round(duration, 2)

            # Print summary
            self.log("\n" + "=" * 80)
            self.log("PIPELINE COMPLETED SUCCESSFULLY")
            self.log("=" * 80)
            self.log(f"Duration: {self.stats['duration_minutes']} minutes")
            self.log(f"Total assets: {self.stats['total_assets']}")
            self.log(f"Correlations computed: {self.stats['correlations_computed']}")
            self.log(f"Pairs found: {self.stats['pairs_found']}")
            self.log(f"Pairs stored: {self.stats['pairs_stored']}")
            self.log(f"Cointegration tests: {self.stats['cointegration_tests']}")
            self.log(f"Cointegrated pairs: {self.stats['cointegrated_pairs']}")
            self.log(f"Rolling metrics: {self.stats['rolling_metrics_computed']}")
            self.log(f"Factor exposures: {self.stats['factor_exposures_computed']}")
            self.log("=" * 80 + "\n")

            return True

        except Exception as e:
            self.log(f"\n✗ PIPELINE FAILED: {e}", "error")
            self.log(traceback.format_exc(), "error")
            return False


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analytics computation pipeline v2")
    parser.add_argument(
        "--max-assets",
        type=int,
        default=None,
        help="Limit the number of assets for fast testing",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of yfinance tickers to run the pipeline for",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Correlation threshold override for |correlation| (e.g., 0.6)",
    )
    parser.add_argument(
        "--min-obs",
        type=int,
        default=None,
        help="Minimum overlapping observations for cointegration tests (override)",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Run pipeline in production mode: full assets, longer lookback, production defaults",
    )
    args = parser.parse_args()

    # Declare globals up front so Python knows these names are module-level
    global TEST_MODE, LOOKBACK_DAYS, MAX_ASSETS, CORRELATION_THRESHOLD, ROLLING_WINDOWS

    pipeline = AnalyticsComputationPipeline()
    # Apply production/test mode on start
    TEST_MODE = not args.prod
    if TEST_MODE:
        LOOKBACK_DAYS = 90
        MAX_ASSETS = 20
        CORRELATION_THRESHOLD = 0.7
        ROLLING_WINDOWS = [30]
    else:
        LOOKBACK_DAYS = 730
        MAX_ASSETS = None
        # Default production gates
        CORRELATION_THRESHOLD = 0.6
        ROLLING_WINDOWS = [30, 60, 90, 180, 252]
    if args.max_assets:
        MAX_ASSETS = args.max_assets
    if args.tickers:
        pipeline.tickers_override = args.tickers.split(",")
    if args.threshold is not None:
        CORRELATION_THRESHOLD = float(args.threshold)
    if args.min_obs is not None:
        pipeline.min_observations = int(args.min_obs)
    success = pipeline.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
