"""
Standalone Rolling Metrics Computation Script
Computes rolling financial metrics (beta, volatility, sharpe, etc.) for all assets.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))

import pandas as pd
import numpy as np

from utils.supabase_client import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Configuration
LOOKBACK_DAYS = 365  # 1 year of data
ROLLING_WINDOWS = [30, 60, 90, 180, 252]  # All windows
MAX_ASSETS = None  # Limit for testing (set to None for all assets)
SKIP_EXISTING = True  # Skip assets that already have metrics

# Benchmarks for beta calculation
BENCHMARKS = {
    "SPY.US": "S&P 500",
    "GLD.US": "Gold",
}


def compute_rolling_metrics_for_asset(
    supabase, 
    asset: Dict, 
    benchmark_data: Dict[str, pd.DataFrame],
    start_date: datetime,
    end_date: datetime,
    skip_existing: bool = True
) -> int:
    """Compute rolling metrics for a single asset."""
    asset_id = asset["id"]
    symbol = asset["symbol"]
    metrics_computed = 0
    
    try:
        logger.info(f"  Processing {symbol}...")
        
        # Check if metrics already exist for this asset (optional skip)
        if skip_existing:
            existing_check = (
                supabase.client.table("rolling_metrics")
                .select("id", count="exact")
                .eq("asset_id", asset_id)
                .limit(1)
                .execute()
            )
            
            if existing_check.count and existing_check.count > 0:
                logger.info(f"    ⊙ Skipping {symbol} - already has {existing_check.count} metrics")
                return 0
        
        # Fetch price history for asset
        price_response = (
            supabase.client.table("price_history")
            .select("timestamp, close")
            .eq("asset_id", asset_id)
            .gte("timestamp", start_date.isoformat())
            .lte("timestamp", end_date.isoformat())
            .order("timestamp")
            .execute()
        )
        
        if not price_response.data or len(price_response.data) < 30:
            logger.warning(f"    ✗ Insufficient data for {symbol} ({len(price_response.data) if price_response.data else 0} points)")
            return 0
        
        # Convert to DataFrame
        asset_df = pd.DataFrame(price_response.data)
        asset_df["timestamp"] = pd.to_datetime(asset_df["timestamp"])
        asset_df = asset_df.set_index("timestamp").sort_index()
        asset_df["returns"] = asset_df["close"].pct_change()
        
        logger.info(f"    ✓ Loaded {len(asset_df)} price points")
        
        # Compute metrics for each window and benchmark
        for window in ROLLING_WINDOWS:
            if len(asset_df) < window:
                continue
            
            for benchmark_symbol, benchmark_name in BENCHMARKS.items():
                if benchmark_symbol not in benchmark_data:
                    continue
                
                bench_df = benchmark_data[benchmark_symbol]
                
                # Align asset and benchmark data
                common_dates = asset_df.index.intersection(bench_df.index)
                if len(common_dates) < window:
                    continue
                
                asset_aligned = asset_df.loc[common_dates]
                bench_aligned = bench_df.loc[common_dates]
                
                # Get benchmark ID
                bench_response = (
                    supabase.client.table("assets")
                    .select("id")
                    .eq("symbol", benchmark_symbol)
                    .single()
                    .execute()
                )
                benchmark_id = bench_response.data["id"] if bench_response.data else None
                
                # Compute rolling metrics
                rolling_beta = []
                rolling_volatility = []
                rolling_sharpe = []
                
                for i in range(window, len(common_dates) + 1):
                    window_asset = asset_aligned.iloc[i - window : i]
                    window_bench = bench_aligned.iloc[i - window : i]
                    
                    # Beta (covariance / variance)
                    cov = window_asset["returns"].cov(window_bench["returns"])
                    var = window_bench["returns"].var()
                    beta = cov / var if var != 0 else None
                    
                    # Volatility (annualized std dev)
                    volatility = window_asset["returns"].std() * np.sqrt(252)
                    
                    # Sharpe Ratio (assuming 0% risk-free rate)
                    mean_return = window_asset["returns"].mean() * 252
                    sharpe = mean_return / volatility if volatility != 0 else None
                    
                    rolling_beta.append(beta)
                    rolling_volatility.append(volatility)
                    rolling_sharpe.append(sharpe)
                
                # Batch insert all metrics for this window/benchmark combination
                batch_records = []
                for idx, date in enumerate(common_dates[window:]):
                    metric_record = {
                        "asset_id": asset_id,
                        "benchmark_id": benchmark_id,
                        "window_days": window,
                        "start_date": common_dates[idx].isoformat(),
                        "end_date": date.isoformat(),
                        "rolling_beta": float(rolling_beta[idx]) if rolling_beta[idx] is not None else None,
                        "rolling_volatility": float(rolling_volatility[idx]) if rolling_volatility[idx] is not None else None,
                        "rolling_sharpe": float(rolling_sharpe[idx]) if rolling_sharpe[idx] is not None else None,
                    }
                    batch_records.append(metric_record)
                
                # Insert batch (PostgREST/Supabase supports batch inserts)
                if batch_records:
                    try:
                        # Preferred: upsert to avoid duplicates across reruns
                        supabase.client.table("rolling_metrics").upsert(
                            batch_records,
                            on_conflict="asset_id,benchmark_id,window_days,end_date"
                        ).execute()
                        metrics_computed += len(batch_records)
                        logger.info(f"    ✓ Inserted {len(batch_records)} metrics for window={window}, benchmark={benchmark_symbol}")
                    except Exception as insert_error:
                        # If unique constraint for ON CONFLICT is missing, fall back to insert
                        if "42P10" in str(insert_error) or "ON CONFLICT" in str(insert_error):
                            try:
                                supabase.client.table("rolling_metrics").insert(batch_records).execute()
                                metrics_computed += len(batch_records)
                                logger.info(f"    ✓ Inserted {len(batch_records)} metrics for window={window}, benchmark={benchmark_symbol}")
                            except Exception as e2:
                                logger.error(f"    ✗ Batch insert fallback failed: {e2}")
                        else:
                            logger.error(f"    ✗ Failed to insert batch: {insert_error}")
        
        logger.info(f"    ✓ Computed {metrics_computed} rolling metrics for {symbol}")
        return metrics_computed
        
    except Exception as e:
        logger.error(f"    ✗ Error processing {symbol}: {e}")
        return 0


def main():
    """Main execution."""
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 80)
    logger.info("STANDALONE ROLLING METRICS COMPUTATION")
    logger.info("=" * 80)
    logger.info(f"Lookback: {LOOKBACK_DAYS} days")
    logger.info(f"Windows: {ROLLING_WINDOWS}")
    logger.info(f"Max assets: {MAX_ASSETS or 'All'}")
    
    # Initialize Supabase
    supabase = get_supabase_client()
    logger.info("✓ Supabase client initialized")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    
    # Fetch benchmark data
    logger.info("\nLoading benchmark data...")
    benchmark_data = {}
    
    for benchmark_symbol in BENCHMARKS.keys():
        try:
            bench_response = (
                supabase.client.table("assets")
                .select("id")
                .eq("symbol", benchmark_symbol)
                .single()
                .execute()
            )
            
            if not bench_response.data:
                logger.warning(f"  ✗ Benchmark {benchmark_symbol} not found")
                continue
            
            benchmark_id = bench_response.data["id"]
            
            price_response = (
                supabase.client.table("price_history")
                .select("timestamp, close")
                .eq("asset_id", benchmark_id)
                .gte("timestamp", start_date.isoformat())
                .lte("timestamp", end_date.isoformat())
                .order("timestamp")
                .execute()
            )
            
            if price_response.data:
                df = pd.DataFrame(price_response.data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp").sort_index()
                df["returns"] = df["close"].pct_change()
                benchmark_data[benchmark_symbol] = df
                logger.info(f"  ✓ Loaded {benchmark_symbol}: {len(df)} points")
            else:
                logger.warning(f"  ✗ No price data for {benchmark_symbol}")
                
        except Exception as e:
            logger.error(f"  ✗ Error loading {benchmark_symbol}: {e}")
    
    if not benchmark_data:
        logger.error("✗ No benchmark data available. Aborting.")
        return 1
    
    # Fetch assets
    logger.info("\nFetching assets...")
    assets_response = (
        supabase.client.table("assets")
        .select("id, symbol, name")
        .execute()
    )
    
    assets = assets_response.data
    if MAX_ASSETS:
        assets = assets[:MAX_ASSETS]
    
    logger.info(f"✓ Processing {len(assets)} assets")
    
    # Process each asset
    logger.info("\nComputing rolling metrics...")
    total_metrics = 0
    successful_assets = 0
    
    for asset in assets:
        metrics_count = compute_rolling_metrics_for_asset(
            supabase, asset, benchmark_data, start_date, end_date, SKIP_EXISTING
        )
        if metrics_count > 0:
            successful_assets += 1
            total_metrics += metrics_count
    
    # Summary
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds() / 60
    
    logger.info("\n" + "=" * 80)
    logger.info("COMPUTATION COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Duration: {duration:.2f} minutes")
    logger.info(f"Assets processed: {successful_assets}/{len(assets)}")
    logger.info(f"Total metrics computed: {total_metrics}")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
