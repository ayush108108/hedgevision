#!/usr/bin/env python3
"""
Minimal smoke test: insert a couple of daily OHLC rows into price_history for given symbols.

Usage (PowerShell):
  python backend/scripts/smoke_insert_price_row.py --symbols AAPL,SPY

Requires SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) to be set.
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

# Ensure backend package root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.data_writer_service import get_data_writer


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Smoke insert daily OHLC rows")
    ap.add_argument("--symbols", type=str, default="AAPL,SPY")
    return ap.parse_args()


def make_df() -> pd.DataFrame:
    # Two deterministic days
    rows = [
        {"Date": "2024-01-02", "Open": 100.0, "High": 105.0, "Low": 99.5, "Close": 104.0, "Volume": 1234567},
        {"Date": "2024-01-03", "Open": 104.0, "High": 106.0, "Low": 103.5, "Close": 105.5, "Volume": 2345678},
    ]
    return pd.DataFrame(rows)


def main() -> int:
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    df = make_df()
    writer = get_data_writer()
    total = 0
    for s in symbols:
        inserted = writer.store_data(s, df, source="smoke")
        print(f"{s}: inserted {inserted} rows")
        total += inserted
    print(f"Total inserted: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
