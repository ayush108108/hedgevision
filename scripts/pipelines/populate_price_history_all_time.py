#!/usr/bin/env python3
"""
Populate all available historical price history for assets using unified data sources.

This script automatically routes assets to appropriate data sources:
- Crypto assets (Section A) -> CCXT/Binance
- Other assets (Sections B & C) -> yfinance

It batches symbol processing, respects rate limiting, and prints detailed
terminal logs so you can follow progress.

Usage:
    python scripts/pipelines/populate_price_history_all_time.py --limit-assets 50 --batch-size 5 --delay 20

Notes:
- This uses the UnifiedDataIngestionService to route assets to correct sources
- The service uses DataWriter/store_multiple_symbols to standardize and store data
- Respects rate limiting for both CCXT and yfinance APIs
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import List
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

# Ensure backend package root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add backend package to path so we can import backend clients/services
sys.path.insert(0, os.path.join(ROOT, "backend"))

try:
    from clients.yfinance_client import get_yfinance_client
    from api.services.data_writer_service import get_data_writer
    from api.services.unified_ingestion_service import get_unified_ingestion_service
    from api.utils.config import get_config
    from supabase import create_client
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Populate ALL-TIME price_history using yfinance period='max'")
    ap.add_argument("--symbols", type=str, default="", help="Comma-separated symbols (omit to fetch active assets from Supabase)")
    ap.add_argument(
        "--limit-assets",
        type=int,
        default=0,
        help="Limit number of assets to fetch; 0 means no limit (fetch all active assets)",
    )
    ap.add_argument(
        "--skip-assets",
        type=int,
        default=0,
        help="Number of assets to skip (offset) when fetching from Supabase",
    )
    ap.add_argument("--batch-size", type=int, default=5, help="Number of assets to process between extra waits")
    ap.add_argument("--delay", type=int, default=20, help="Additional delay (seconds) between logical batches")
    ap.add_argument("--dry-run", action="store_true", help="Don't write to DB; only fetch and show counts")
    # No group_size for `fetch_batch` — multi-ticker groups are controlled by --batch-size
    return ap.parse_args()


def _get_tickers_from_supabase(limit: int, skip: int = 0) -> List[str]:
    cfg = get_config()
    client = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_KEY"])
    # Fetch active assets with yfinance_ticker
    cols = "id,yfinance_ticker"
    try:
        # Use offset (skip) and optional limit
        base = (
            client.table("assets")
            .select(cols)
            .eq("is_active", 1)
            .not_.is_("yfinance_ticker", "null")
            .order("id")
        )
        if skip and skip > 0:
            base = base.offset(skip)

        if limit and limit > 0:
            resp = base.limit(limit).execute()
        else:
            resp = base.execute()

        # Fallback: if no data (maybe permissions), try without active filter but apply offset/limit
        if not getattr(resp, "data", None):
            fallback = client.table("assets").select(cols).not_.is_("yfinance_ticker", "null").order("id")
            if skip and skip > 0:
                fallback = fallback.offset(skip)
            if limit and limit > 0:
                fallback = fallback.limit(limit)
            resp = fallback.execute()

        return [r["yfinance_ticker"] for r in (resp.data or []) if r.get("yfinance_ticker")]
    except Exception as e:
        print(f"Warning: Failed to fetch from assets table: {e}")
        return []


async def main_async(args: argparse.Namespace) -> int:
    if args.symbols.strip():
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = _get_tickers_from_supabase(args.limit_assets, args.skip_assets)

    if not symbols:
        print("No symbols found. Exiting.")
        return 1

    total_symbols = len(symbols)
    if args.limit_assets == 0:
        print(f"Starting ALL-TIME backfill for {total_symbols} symbols (period='max', fetching ALL active assets)")
    else:
        print(f"Starting ALL-TIME backfill for {total_symbols} symbols (period='max')")
    print(f"Processing in batch-size={args.batch_size} groups, extra delay={args.delay}s between groups")

    yf = get_yfinance_client()
    unified_ingestion = get_unified_ingestion_service()
    writer = get_data_writer()

    # Use fetch_batch with period='max'. The client will rate-limit between each symbol.
    # To avoid too many immediate requests, process in logical groups
    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    total_inserted = 0
    processed = 0
    success_count = 0

    group_idx = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} symbols"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        overall_task = progress.add_task("Total progress", total=total_symbols)

        for group_idx, group in enumerate(chunk(symbols, args.batch_size), start=1):
            print(f"\n=== Group {group_idx} | {len(group)} tickers: {', '.join(group)} ===")

            # Fetch all-time data using unified ingestion service
            # Routes crypto assets to CCXT/Binance, others to yfinance
            fetched = await unified_ingestion.fetch_batch_data(
                tickers=group,
                period="max",
                interval="1d",
                batch_size=len(group),  # Process all in this group together
                delay_between_batches=args.delay
            )

            # Show group summary and advance progress
            for sym, df in fetched.items():
                if df is None or df.empty:
                    print(f"  ✗ {sym}: No data returned")
                else:
                    first = df['timestamp'].min().date() if 'timestamp' in df.columns else 'N/A'
                    last = df['timestamp'].max().date() if 'timestamp' in df.columns else 'N/A'
                    print(f"  ✓ {sym}: {len(df)} rows ({first}..{last})")
                progress.advance(overall_task)

            if args.dry_run:
                print("Dry-run: skipping DB write for this group.")
            else:
                # store_multiple_symbols expects dict of symbol->DataFrame
                results = writer.store_multiple_symbols(fetched, source="yfinance")
                g_inserted = sum(results.values())
                total_inserted += g_inserted
                print(f"  → Inserted {g_inserted} new rows this group")
                success_count += sum(1 for v in results.values() if v > 0)


            processed += len(group)

        # Extra delay between groups to avoid bursts (in addition to per-symbol rate limiting)
        if (group_idx * args.batch_size) < len(symbols):
            print(f"Waiting {args.delay}s before next group...")
            await asyncio.sleep(args.delay)

    print(f"\nAll groups completed. Processed: {processed}, groups: {group_idx}")
    print(f"Total inserted: {total_inserted}, symbols with new rows: {success_count}")

    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
