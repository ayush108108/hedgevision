"""
Populate Cointegration Data in Database (Full-scale, batched)

This script runs cointegration tests on existing price data and populates the
`cointegration_scores` table with detailed results. Optimized to:
- Select a configurable universe (default: 200+ symbols)
- Cache price history per asset once to minimize Supabase load
- Iterate all pair combinations (C(n,2)) with batching and throttling
- Store either only cointegrated pairs (default) or ALL pairs (via --store-all-pairs)

Examples (PowerShell):
  # Quick test on first 10 assets (only cointegrated stored)
  python scripts/populate_cointegration.py --limit-assets 10

  # Full 200+ symbol universe, store top 5,000+ screened pairs, 252-day lookback
  python scripts/populate_cointegration.py --limit-assets 200 --store-all-pairs --lookback-days 252 --sleep 0.2 --batch-insert 100

  # Backward-compatibility: treats --all as full-mode presets
  python scripts/populate_cointegration.py --all
"""

from __future__ import annotations

import sys
import os
import asyncio
import argparse
import time
from datetime import datetime, timedelta, timezone
from itertools import combinations
from typing import Dict, List

import pandas as pd
import numpy as np

# Add backend/api to sys.path so package `api` is importable
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_path = os.path.join(repo_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from api.utils.supabase_client import get_supabase_client
from api.services.cointegration_service import CointegrationService


def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, bool):  # Handle regular Python bool
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _fetch_assets(supabase, limit_assets: int | None, symbol_suffix: str | None) -> List[Dict]:
    # Attempt 1: try to fetch `symbol` if present (legacy schema)
    try:
        resp = supabase.client.table("assets").select("id,symbol,name").order("symbol").execute()
        assets = resp.data or []
        if symbol_suffix:
            assets = [a for a in assets if isinstance(a.get("symbol"), str) and a["symbol"].endswith(symbol_suffix)]
        # Stable order
        assets.sort(key=lambda a: a.get("symbol", ""))
        if assets:
            if limit_assets:
                assets = assets[:limit_assets]
            return assets
    except Exception:
        # Fall through to try yfinance_ticker below
        pass

    # Attempt 2: use yfinance_ticker mapping (preferred schema)
    try:
        resp = (
            supabase.client.table("assets")
            .select("id,yfinance_ticker,name")
            .order("yfinance_ticker")
            .execute()
        )
        assets = resp.data or []
        if symbol_suffix:
            assets = [a for a in assets if isinstance(a.get("yfinance_ticker"), str) and a["yfinance_ticker"].endswith(symbol_suffix)]
        # Map fallback symbol to yfinance_ticker for compatibility
        for a in assets:
            if a.get("yfinance_ticker"):
                a["symbol"] = a.get("yfinance_ticker")
        assets.sort(key=lambda a: a.get("symbol", ""))
        if limit_assets:
            assets = assets[:limit_assets]
        return assets
    except Exception:
        # Last resort: return empty list
        return []


def _fetch_price_history(supabase, asset_id: str, start_iso: str, end_iso: str) -> pd.DataFrame:
    q = (
        supabase.client.table("price_history")
        .select("timestamp,close")
        .eq("asset_id", asset_id)
        .gte("timestamp", start_iso)
        .lte("timestamp", end_iso)
        .order("timestamp")
    )
    res = q.execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        df["date"] = pd.to_datetime(df["timestamp"])  # preserve original too
        df = df.drop_duplicates(subset=["date"], keep="last").sort_values("date")
        df = df[["date", "close"]]
        # ensure numeric and positive
        df["close"] = pd.to_numeric(df["close"], errors="coerce").astype(float)
        df = df[df["close"] > 0].dropna()
    return df


def _build_test_record(result_dict: Dict, asset1: str, asset2: str, granularity: str, lookback_days: int) -> Dict:
    # Defensive getters
    def g(key, default=None):
        v = result_dict.get(key, default)
        try:
            # convert numpy scalars
            if isinstance(v, (np.generic,)):
                return v.item()
        except Exception:
            pass
        return v

    return {
        "asset1_symbol": asset1,
        "asset2_symbol": asset2,
        "test_date": datetime.now(timezone.utc).isoformat(),
        "granularity": granularity,
        "lookback_days": int(lookback_days),
        "overall_score": float(g("overall_score", 0.0)),
        # Engle-Granger
        "eg_is_cointegrated": bool(g("eg_is_cointegrated", False)),
        "eg_pvalue": float(g("eg_pvalue", 1.0)) if g("eg_pvalue") is not None else None,
        "eg_test_statistic": float(g("eg_test_statistic", 0.0)) if g("eg_test_statistic") is not None else None,
        "eg_critical_value_1pct": float(g("eg_critical_value_1pct")) if g("eg_critical_value_1pct") is not None else None,
        "eg_critical_value_5pct": float(g("eg_critical_value_5pct")) if g("eg_critical_value_5pct") is not None else None,
        "eg_critical_value_10pct": float(g("eg_critical_value_10pct")) if g("eg_critical_value_10pct") is not None else None,
        "eg_significance_level": g("eg_significance_level"),
        # Johansen (map trace stat to single columns)
        "johansen_is_cointegrated": bool(g("johansen_is_cointegrated", False)),
        "johansen_test_statistic": float(g("johansen_trace_stat", 0.0)) if g("johansen_trace_stat") is not None else None,
        "johansen_critical_value": float(g("johansen_trace_crit_95", 0.0)) if g("johansen_trace_crit_95") is not None else None,
        # ADF
        "adf_is_stationary": bool(g("adf_is_stationary", False)),
        "adf_pvalue": float(g("adf_pvalue", 1.0)) if g("adf_pvalue") is not None else None,
        "adf_test_statistic": float(g("adf_test_statistic", 0.0)) if g("adf_test_statistic") is not None else None,
        # Mean reversion
        "half_life_days": float(g("half_life_days")) if g("half_life_days") is not None else None,
        "hurst_exponent": float(g("hurst_exponent")) if g("hurst_exponent") is not None else None,
        # Regression
        "hedge_ratio": float(g("beta_coefficient")) if g("beta_coefficient") is not None else None,
        "beta_coefficient": float(g("beta_coefficient")) if g("beta_coefficient") is not None else None,
        "alpha_intercept": float(g("alpha_intercept")) if g("alpha_intercept") is not None else None,
        "r_squared": float(g("regression_r_squared")) if g("regression_r_squared") is not None else None,
        "regression_std_error": float(g("regression_std_error")) if g("regression_std_error") is not None else None,
        # Full JSONB
        "test_results": convert_numpy_types(result_dict),
    }


async def populate_cointegration_data():
    """Main function to populate cointegration data for many pairs efficiently."""

    ap = argparse.ArgumentParser(description="Populate cointegration_scores with batched pair tests")
    ap.add_argument("--limit-assets", type=int, default=10, help="Max number of assets to include (default 10; use --all for 50)")
    ap.add_argument("--symbol-suffix", type=str, default=None, help="Filter assets by symbol suffix (default none; use '.US' to filter by .US)")
    ap.add_argument("--lookback-days", type=int, default=252, help="Lookback window in days (default 252)")
    ap.add_argument("--granularity", type=str, default="daily", choices=["daily"], help="Data granularity (default daily)")
    ap.add_argument("--store-all-pairs", action="store_true", help="Store results for all tested pairs, not only cointegrated ones")
    ap.add_argument("--batch-insert", type=int, default=100, help="Number of rows per insert batch (default 100)")
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between insert batches (default 0.0)")
    ap.add_argument("--all", action="store_true", help="Compatibility: same as --limit-assets 50 --store-all-pairs")
    ap.add_argument("--from-pairs-file", type=str, default=None, help="Read specific pairs from CSV file (asset1,asset2 per line)")
    args = ap.parse_args()

    # Backward-compatibility preset
    if args.all:
        if args.limit_assets < 50:
            args.limit_assets = 50
        args.store_all_pairs = True

    print("=" * 80)
    print("POPULATING COINTEGRATION DATA (BATCHED)")
    print("=" * 80)
    print(f"Universe limit: {args.limit_assets} | Suffix filter: '{args.symbol_suffix}' | Lookback: {args.lookback_days}d | Granularity: {args.granularity}")
    print(f"Store all pairs: {args.store_all_pairs} | Batch size: {args.batch_insert} | Sleep: {args.sleep}s")

    # Initialize services
    print("\n[1/6] Initializing services...")
    supabase = get_supabase_client()
    cointegration_service = CointegrationService()

    if not supabase:
        print("[ERROR] Failed to connect to Supabase")
        return 1

    print("   [SUCCESS] Supabase connected")
    print("   [SUCCESS] Cointegration service initialized")

    # Time window
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=args.lookback_days)
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    # Get assets
    print("\n[2/6] Fetching assets from database...")
    try:
        assets = _fetch_assets(supabase, args.limit_assets, args.symbol_suffix or None)
        if not assets:
            print("   [ERROR] No assets found after filtering")
            return 1
        print(f"   [SUCCESS] Selected {len(assets)} assets:")
        for a in assets[:min(10, len(assets))]:
            print(f"      - {a['symbol']:<12} {a.get('name','')}")
    except Exception as e:
        print(f"   [ERROR] Error fetching assets: {e}")
        return 1

    # Prefetch price history per asset (cache)
    print("\n[3/6] Fetching price history for selected assets (cached)...")
    price_map: Dict[str, pd.DataFrame] = {}
    missing_prices = 0
    for a in assets:
        try:
            df = _fetch_price_history(supabase, a["id"], start_iso, end_iso)
            if df is None or df.empty:
                missing_prices += 1
                continue
            price_map[a["symbol"]] = df
        except Exception as e:
            print(f"      [WARN] Failed prices for {a['symbol']}: {e}")
            missing_prices += 1
    print(f"   [INFO] Price cache ready for {len(price_map)}/{len(assets)} assets (missing: {missing_prices})")
    if len(price_map) < 2:
        print("   [ERROR] Not enough assets with price data to test pairs")
        return 1

    # Generate pairs (either from file or all combinations)
    print("\n[4/6] Generating pair list and running tests...")
    if args.from_pairs_file:
        print(f"   [INFO] Reading pairs from file: {args.from_pairs_file}")
        pair_list = []
        try:
            with open(args.from_pairs_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split(',')
                    if len(parts) >= 2:
                        s1, s2 = parts[0].strip(), parts[1].strip()
                        # Only include if we have price data
                        if s1 in price_map and s2 in price_map:
                            pair_list.append((s1, s2))
            print(f"   [INFO] Loaded {len(pair_list)} pairs from file")
        except Exception as e:
            print(f"   [ERROR] Failed to read pairs file: {e}")
            return 1
    else:
        symbols = list(price_map.keys())
        symbols.sort()
        pair_list = [(s1, s2) for s1, s2 in combinations(symbols, 2)]
    
    print(f"   [INFO] Total pairs to test: {len(pair_list)}")

    tested_pairs = 0
    stored_pairs = 0
    cointegrated_pairs = 0
    batch_buffer: List[Dict] = []

    for idx, (s1, s2) in enumerate(pair_list, start=1):
        try:
            df1 = price_map.get(s1)
            df2 = price_map.get(s2)
            if df1 is None or df2 is None or df1.empty or df2.empty:
                continue

            # Merge prices on date
            merged = pd.merge(df1.rename(columns={"close": "asset1_price"}),
                              df2.rename(columns={"close": "asset2_price"}),
                              on="date", how="inner")
            if merged.empty or len(merged) < 3:
                # Create minimal DF to trigger error path in service (or skip)
                if not args.store_all_pairs:
                    continue

            # Build result using service
            result = cointegration_service.test_pair(
                asset1_symbol=s1,
                asset2_symbol=s2,
                prices_df=merged[["date", "asset1_price", "asset2_price"]],
                granularity=args.granularity,
                lookback_days=args.lookback_days,
            )
            tested_pairs += 1

            result_dict = vars(result)
            record = _build_test_record(result_dict, s1, s2, args.granularity, args.lookback_days)

            if result_dict.get("eg_is_cointegrated", False):
                cointegrated_pairs += 1
                print(f"   [{idx}/{len(pair_list)}] {s1} vs {s2}: COINTEGRATED (p={result_dict.get('eg_pvalue', 1.0):.4f}, score={result_dict.get('overall_score', 0.0):.1f})")
                batch_buffer.append(record)
                stored_pairs += 1
            else:
                # Store only if requested
                if args.store_all_pairs:
                    print(f"   [{idx}/{len(pair_list)}] {s1} vs {s2}: not cointegrated (p={result_dict.get('eg_pvalue', 1.0):.4f})")
                    batch_buffer.append(record)
                    stored_pairs += 1
                else:
                    # Skip storing non-cointegrated by default
                    pass

            # Flush batch
            if len(batch_buffer) >= args.batch_insert:
                try:
                    supabase.client.table("cointegration_scores").insert(batch_buffer).execute()
                    batch_buffer.clear()
                    if args.sleep > 0:
                        time.sleep(args.sleep)
                except Exception as e:
                    print(f"      [WARN] Batch insert failed: {e}")
                    # Try smaller batches individual fallback
                    for rec in list(batch_buffer):
                        try:
                            supabase.client.table("cointegration_scores").insert(rec).execute()
                            batch_buffer.remove(rec)
                            if args.sleep > 0:
                                time.sleep(args.sleep)
                        except Exception as e2:
                            print(f"        [WARN] Single insert failed for {rec.get('asset1_symbol')}/{rec.get('asset2_symbol')}: {e2}")
                    batch_buffer.clear()

        except Exception as e:
            print(f"   [{idx}/{len(pair_list)}] {s1} vs {s2}: ERROR {str(e)[:120]}")
            continue

    # Flush remaining
    if batch_buffer:
        try:
            supabase.client.table("cointegration_scores").insert(batch_buffer).execute()
            batch_buffer.clear()
        except Exception as e:
            print(f"      [WARN] Final batch insert failed: {e}")

    # Summary
    print("\n[5/6] Summary of run")
    print(f"   Tested pairs:        {tested_pairs}")
    print(f"   Stored pair records: {stored_pairs}")
    print(f"   Cointegrated pairs:  {cointegrated_pairs}")

    # Refresh materialized view (best-effort)
    print("\n[6/6] Refreshing materialized view cointegration_scores_latest (best-effort)")
    try:
        supabase.client.rpc("refresh_cointegration_scores_latest").execute()
        print("   [SUCCESS] Materialized view refreshed")
    except Exception as e:
        print(f"   [WARN] Could not refresh materialized view: {e}")

    print("\nDONE")
    return 0


if __name__ == "__main__":
    # Run async function (synchronously used)
    exit_code = asyncio.run(populate_cointegration_data())
    sys.exit(exit_code)
