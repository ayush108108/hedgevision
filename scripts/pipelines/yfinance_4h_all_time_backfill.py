"""
4h ALL-TIME backfill for active assets.

Fetch 1h data up to ~730 days from Yahoo Finance, aggregate to 4h and upsert.

Defaults: 20s between requests, batch multi-ticker downloads to speed up.
"""

import argparse
import asyncio
import logging
from typing import List, Dict, Any, Optional
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta

import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# Add backend clients to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from clients.yfinance_client import get_yfinance_client
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("backfill_4h_all_time")


async def backfill_4h_all_time(
    supabase: Client,
    days: int = 730,
    only_active: bool = True,
    limit: Optional[int] = None,
    batch_size: int = 5,
    dry_run: bool = False,
    delay: float = 20.0,
) -> Dict[str, Any]:
    yf = get_yfinance_client()
    yf.config.delay_between_requests = delay

    q = supabase.table("assets").select("id, yfinance_ticker, is_active")
    if only_active:
        q = q.eq("is_active", 1)
    resp = q.execute()
    assets: List[Dict[str, Any]] = resp.data or []
    if limit and limit > 0:
        assets = assets[:limit]

    logger.info(f"Found {len(assets)} assets to backfill (only_active={only_active})")

    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()

    total_candles = 0
    succeeded = 0
    failed = 0

    batches = list(chunk(assets, batch_size))

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} batches"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ) as pg:
        task = pg.add_task("Backfill 4h batches", total=len(batches))

        for batch_idx, batch in enumerate(batches, start=1):
            syms = [a.get("yfinance_ticker") for a in batch]
            syms = [s for s in syms if s]
            if not syms:
                logger.warning(f"Batch {batch_idx}: no symbols, skipping")
                pg.advance(task)
                continue

            logger.info(f"Batch {batch_idx}/{len(batches)}: fetching {len(syms)} symbols")

            fetched = await yf.fetch_batch_multi(
                symbols=syms,
                start_date=start_date,
                end_date=end_date,
                interval="1h",
                asset_types=None,
                group_size=batch_size,
            )

            for asset in batch:
                sym = asset.get("yfinance_ticker")
                if not sym:
                    logger.warning(f"  ⚠ Asset {asset.get('id')} has no yfinance_ticker; skipping")
                    failed += 1
                    continue

                df_hourly = fetched.get(sym)
                if df_hourly is None:
                    df_hourly = pd.DataFrame()
                if df_hourly.empty:
                    logger.warning(f"  No 1h data for {sym}")
                    failed += 1
                    continue

                if 'timestamp' not in df_hourly.columns:
                    logger.warning(f"  No 'timestamp' column in 1h data for {sym}")
                    failed += 1
                    continue

                df_4h = yf._aggregate_to_4hour(df_hourly)
                if df_4h.empty:
                    logger.warning(f"  No aggregated 4h for {sym}")
                    failed += 1
                    continue

                cols = ["timestamp", "open", "high", "low", "close", "volume", "adjusted_close", "source"]
                df_4h = df_4h[cols].copy()

                records = []
                for _, row in df_4h.iterrows():
                    records.append(
                        {
                            "asset_id": asset.get("id"),
                            "timestamp": pd.to_datetime(row["timestamp"]).isoformat(),
                            "open": float(row["open"]) if pd.notna(row.get("open")) else None,
                            "high": float(row["high"]) if pd.notna(row.get("high")) else None,
                            "low": float(row["low"]) if pd.notna(row.get("low")) else None,
                            "close": float(row["close"]) if pd.notna(row.get("close")) else None,
                            "volume": int(row["volume"]) if pd.notna(row.get("volume")) else 0,
                            "adjusted_close": float(row["adjusted_close"]) if pd.notna(row.get("adjusted_close")) else None,
                            "source": str(row.get("source", "yfinance")),
                        }
                    )

                if not records:
                    logger.warning(f"  No valid 4h records for {sym}")
                    failed += 1
                    continue

                if dry_run:
                    logger.info(f"  (dry-run) Would upsert {len(records)} 4h candles for {sym}")
                    inserted = len(records)
                else:
                    inserted = 0
                    for idx in range(0, len(records), 1000):
                        chunk_records = records[idx : idx + 1000]
                        supabase.table("intraday_price_history").upsert(chunk_records, on_conflict="asset_id,timestamp").execute()
                        inserted += len(chunk_records)

                total_candles += inserted
                succeeded += 1

            pg.advance(task)

    return {"assets": len(assets), "succeeded": succeeded, "failed": failed, "candles": total_candles}


async def main():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Use get_config() for consistent environment variable loading
    from api.utils.config import get_config
    cfg = get_config()
    supabase_url = cfg["SUPABASE_URL"]
    supabase_key = cfg["SUPABASE_KEY"]
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment")

    supabase: Client = create_client(supabase_url, supabase_key)

    parser = argparse.ArgumentParser(description="Backfill 4h intraday ALL-TIME from Yahoo (1h -> 4h aggregation)")
    parser.add_argument("--days", type=int, default=730, help="Max days of 1h data to fetch (Yahoo cap is ~730)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of assets to fetch (0 or omit for all)")
    parser.add_argument("--dry-run", action="store_true", help="Just fetch and report counts, don't write to DB")
    parser.add_argument("--delay", type=float, default=20.0, help="Delay between Yahoo requests (seconds)")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of symbols to fetch per multi-ticker request")
    parser.add_argument("--only-active", action="store_true", default=True, help="Only backfill assets where is_active=1 (default True)")

    args = parser.parse_args()

    only_active = True if args.only_active else False

    result = await backfill_4h_all_time(
        supabase, days=args.days, only_active=only_active, limit=args.limit, batch_size=args.batch_size, dry_run=args.dry_run, delay=args.delay
    )
    logger.info(f"DONE: {result}")


if __name__ == "__main__":
    asyncio.run(main())
