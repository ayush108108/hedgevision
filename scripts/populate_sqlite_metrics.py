#!/usr/bin/env python3
"""
Populate rolling metrics for SQLite database.
Computes rolling financial metrics for assets with sufficient price data.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))
from utils.config import config

ROLLING_WINDOWS = [30, 60, 90]  # Start with smaller windows for quick results
BENCHMARK_SYMBOL = "ETH-USD"  # Use ETH as benchmark (more reliable in crypto-focused DB)
MIN_DATA_POINTS = 200  # Minimum price points needed

def compute_metrics_for_asset(conn, asset_id, symbol, benchmark_id, window):
    """Compute rolling metrics for a single asset and window."""
    cursor = conn.cursor()
    
    # Fetch asset prices
    cursor.execute("""
        SELECT timestamp, close 
        FROM price_history 
        WHERE asset_id = ? 
        ORDER BY timestamp ASC
    """, (asset_id,))
    asset_prices = cursor.fetchall()
    
    # Fetch benchmark prices
    cursor.execute("""
        SELECT timestamp, close 
        FROM price_history 
        WHERE asset_id = ? 
        ORDER BY timestamp ASC
    """, (benchmark_id,))
    bench_prices = cursor.fetchall()
    
    if len(asset_prices) < window or len(bench_prices) < window:
        return 0
    
    # Convert to dict for alignment
    asset_dict = {ts: close for ts, close in asset_prices}
    bench_dict = {ts: close for ts, close in bench_prices}
    
    # Find common dates
    common_dates = sorted(set(asset_dict.keys()) & set(bench_dict.keys()))
    
    if len(common_dates) < window:
        return 0
    
    # Compute returns
    asset_returns = []
    bench_returns = []
    for i in range(1, len(common_dates)):
        prev_date = common_dates[i-1]
        curr_date = common_dates[i]
        
        asset_ret = (asset_dict[curr_date] - asset_dict[prev_date]) / asset_dict[prev_date]
        bench_ret = (bench_dict[curr_date] - bench_dict[prev_date]) / bench_dict[prev_date]
        
        asset_returns.append(asset_ret)
        bench_returns.append(bench_ret)
    
    # Compute rolling metrics
    metrics_inserted = 0
    for i in range(window - 1, len(asset_returns)):
        window_asset = asset_returns[i - window + 1 : i + 1]
        window_bench = bench_returns[i - window + 1 : i + 1]
        
        # Beta
        cov = np.cov(window_asset, window_bench)[0, 1]
        var = np.var(window_bench, ddof=1)
        beta = float(cov / var) if var > 0 else None
        
        # Volatility (annualized)
        volatility = float(np.std(window_asset, ddof=1) * np.sqrt(365))
        
        # Sharpe Ratio (0% risk-free rate)
        mean_return = np.mean(window_asset) * 365
        sharpe = float(mean_return / volatility) if volatility > 0 else None
        
        # Max Drawdown
        cumulative = np.cumprod([1 + r for r in window_asset])
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_dd = float(np.min(drawdown))
        
        # Insert metric
        start_date = common_dates[i - window + 1]
        end_date = common_dates[i + 1]  # +1 because returns are shifted
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO rolling_metrics 
                (asset_id, benchmark_id, window_days, start_date, end_date,
                 rolling_beta, rolling_volatility, rolling_sharpe, max_drawdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (asset_id, benchmark_id, window, start_date, end_date,
                  beta, volatility, sharpe, max_dd))
            metrics_inserted += 1
        except Exception as e:
            print(f"  Error inserting metric: {e}")
    
    return metrics_inserted


def main():
    db_path = config.get("DB_PATH", "backend/prices.db")
    print(f"Using database: {db_path}")
    
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    
    try:
        # Get benchmark asset
        cursor.execute("SELECT id FROM assets WHERE symbol = ?", (BENCHMARK_SYMBOL,))
        bench_row = cursor.fetchone()
        if not bench_row:
            print(f"❌ Benchmark {BENCHMARK_SYMBOL} not found")
            return
        
        benchmark_id = bench_row[0]
        print(f"✓ Using benchmark: {BENCHMARK_SYMBOL} (ID: {benchmark_id})")
        
        # Get assets with sufficient data
        cursor.execute("""
            SELECT a.id, a.symbol, COUNT(ph.id) as price_count
            FROM assets a
            JOIN price_history ph ON a.id = ph.asset_id
            GROUP BY a.id, a.symbol
            HAVING price_count >= ?
            ORDER BY price_count DESC
            LIMIT 20
        """, (MIN_DATA_POINTS,))
        
        assets = cursor.fetchall()
        print(f"✓ Found {len(assets)} assets with sufficient data\n")
        
        total_metrics = 0
        for asset_id, symbol, price_count in assets:
            if symbol == BENCHMARK_SYMBOL:
                continue
                
            print(f"Processing {symbol} ({price_count} prices)...")
            
            for window in ROLLING_WINDOWS:
                metrics_count = compute_metrics_for_asset(
                    conn, asset_id, symbol, benchmark_id, window
                )
                total_metrics += metrics_count
                if metrics_count > 0:
                    print(f"  ✓ Window {window}: {metrics_count} metrics")
        
        conn.commit()
        print(f"\n✅ Total metrics inserted: {total_metrics}")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM rolling_metrics")
        total_count = cursor.fetchone()[0]
        print(f"✅ Total metrics in database: {total_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
