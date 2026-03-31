#!/usr/bin/env python3
"""
Populate daily price_history in Supabase up to the current date.

Focus: data/ETL/services rigor first. Uses yfinance and existing DataWriter service.

Usage (PowerShell):
  # Ensure env has SUPABASE_URL and SUPABASE_KEY or SUPABASE_SERVICE_KEY
  # Optional: specify symbols and start date
  # python backend/scripts/populate_price_history.py --symbols SPY,AAPL,MSFT --start 2015-01-01

If symbols are omitted, attempts to read from Supabase 'assets' table (active assets) up to a limit.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List
import asyncio

import pandas as pd

# Ensure backend package root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local imports
try:
    from api.services.data_writer_service import get_data_writer
    from clients.yfinance_client import get_yfinance_client
    from api.utils.config import get_config
    from supabase import create_client
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Populate Supabase price_history (daily)")
    ap.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated symbols (omit to fetch active assets from Supabase)",
    )
    ap.add_argument(
        "--start",
        type=str,
        default="2015-01-01",
        help="Start date YYYY-MM-DD (default: 2015-01-01)",
    )
    ap.add_argument(
        "--limit-assets",
        type=int,
        default=50,
        help="Max assets to ingest when symbols omitted (default: 50)",
    )
    return ap.parse_args()


def _get_yfinance_tickers_from_supabase(limit: int) -> Dict[str, str]:
    """
    Fetch assets with their yfinance tickers from Supabase.
    
    Returns:
        Dict mapping yfinance_ticker -> asset_name for lookup
    """
    cfg = get_config()
    client = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_KEY"])
    # Fetch active assets with yfinance_ticker
    cols = "id,name,yfinance_ticker"
    try:
        resp = (
            client.table("assets")
            .select(cols)
            .eq("is_active", 1)
            .not_.is_("yfinance_ticker", "null")
            .order("id")
            .limit(limit)
            .execute()
        )
        if not resp.data:
            # Fallback: all assets with yfinance_ticker
            resp = (
                client.table("assets")
                .select(cols)
                .not_.is_("yfinance_ticker", "null")
                .order("id")
                .limit(limit)
                .execute()
            )
        
        # Return dict of yfinance_ticker -> name
        return {str(r["yfinance_ticker"]): str(r["name"]) for r in (resp.data or []) if r.get("yfinance_ticker")}
    except Exception as e:
        print(f"Warning: Failed to fetch from assets table: {e}")
        # Fall back to popular US mega-caps as a bootstrap
        return {
            "SPY": "spy",
            "AAPL": "apple",
            "MSFT": "microsoft",
            "GOOGL": "alphabet",
            "AMZN": "amazon",
            "META": "meta platforms",
            "NVDA": "nvidia",
            "TSLA": "tesla",
        }


async def _download_prices(symbols: List[str]) -> Dict[str, pd.DataFrame]:
    yf = get_yfinance_client()
    # Use batch singular pipeline to respect rate limits consistently
    data = await yf.fetch_batch(symbols=symbols, period="max", interval="1d")
    # Ensure dict[str, DataFrame]
    return {k: v for k, v in data.items() if isinstance(v, pd.DataFrame) and not v.empty}


def main() -> int:
    args = _parse_args()
    # Get yfinance tickers from Supabase or command line
    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        ticker_map = {s: s.lower() for s in symbols}  # Simple mapping for CLI usage
    else:
        ticker_map = _get_yfinance_tickers_from_supabase(args.limit_assets)
        symbols = list(ticker_map.keys())

    if not symbols:
        print("No symbols to ingest. Exiting.")
        return 1

    print(f"Ingesting {len(symbols)} symbols with max historical data")
    print(f"  Sample tickers: {symbols[:10]}{'...' if len(symbols)>10 else ''}")
    
    data = asyncio.run(_download_prices(symbols))
    if not data:
        print("No data downloaded. Exiting.")
        return 1

    writer = get_data_writer()
    results = writer.store_multiple_symbols(data, source="yfinance")

    inserted_total = sum(results.values())
    now_iso = datetime.now(timezone.utc).isoformat()
    print(f"[{now_iso}] Inserted {inserted_total} new rows across {len(results)} symbols.")
    # Print a compact summary
    top = sorted(results.items(), key=lambda kv: kv[1], reverse=True)[:10]
    for sym, cnt in top:
        asset_name = ticker_map.get(sym, sym)
        print(f"  {sym} ({asset_name}): +{cnt} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
