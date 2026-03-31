"""
Fetch corporate actions (dividends and stock splits) for full asset universe.

Creates/updates corporate_actions table with dividend and split data.
"""

import argparse
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add backend clients to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd
from supabase import create_client, Client
from clients.yfinance_client import get_yfinance_client
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("corporate_actions_backfill")


async def backfill_corporate_actions(
    supabase: Client,
    only_active: bool = True,
    limit: Optional[int] = None,
    batch_size: int = 10,
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

    logger.info(f"Found {len(assets)} assets to fetch corporate actions for (only_active={only_active})")

    def chunk(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    total_dividends = 0
    total_splits = 0
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
        task = pg.add_task("Backfill corporate actions", total=len(batches))

        for batch_idx, batch in enumerate(batches, start=1):
            logger.info(f"Batch {batch_idx}/{len(batches)}: processing {len(batch)} symbols")

            for asset in batch:
                sym = asset.get("yfinance_ticker")
                if not sym:
                    logger.warning(f"  ⚠ Asset {asset.get('id')} has no yfinance_ticker; skipping")
                    failed += 1
                    continue

                try:
                    # Fetch corporate actions
                    actions = await yf.fetch_corporate_actions(sym)

                    dividends_df = actions.get('dividends', pd.DataFrame())
                    splits_df = actions.get('splits', pd.DataFrame())

                    # Process dividends
                    dividend_records = []
                    if not dividends_df.empty:
                        for _, row in dividends_df.iterrows():
                            dividend_records.append({
                                "asset_id": asset.get("id"),
                                "timestamp": pd.to_datetime(row["timestamp"]).isoformat(),
                                "action_type": "dividend",
                                "amount": float(row.get("amount", 0)),
                                "source": str(row.get("source", "yfinance")),
                            })

                    # Process splits
                    split_records = []
                    if not splits_df.empty:
                        for _, row in splits_df.iterrows():
                            split_records.append({
                                "asset_id": asset.get("id"),
                                "timestamp": pd.to_datetime(row["timestamp"]).isoformat(),
                                "action_type": "split",
                                "ratio": float(row.get("ratio", 1)),
                                "source": str(row.get("source", "yfinance")),
                            })

                    all_records = dividend_records + split_records

                    if not all_records:
                        logger.info(f"  No corporate actions for {sym}")
                        succeeded += 1
                        continue

                    if dry_run:
                        logger.info(f"  (dry-run) Would upsert {len(dividend_records)} dividends and {len(split_records)} splits for {sym}")
                        total_dividends += len(dividend_records)
                        total_splits += len(split_records)
                    else:
                        # Upsert in chunks to avoid payload size limits
                        for idx in range(0, len(all_records), 500):
                            chunk_records = all_records[idx : idx + 500]
                            supabase.table("corporate_actions").upsert(
                                chunk_records,
                                on_conflict="asset_id,timestamp,action_type"
                            ).execute()

                        total_dividends += len(dividend_records)
                        total_splits += len(split_records)
                        logger.info(f"  ✓ Upserted {len(dividend_records)} dividends and {len(split_records)} splits for {sym}")

                    succeeded += 1

                except Exception as e:
                    logger.error(f"  ✗ Failed to fetch corporate actions for {sym}: {e}")
                    failed += 1

            pg.advance(task)

    return {
        "assets": len(assets),
        "succeeded": succeeded,
        "failed": failed,
        "dividends": total_dividends,
        "splits": total_splits
    }


async def main():
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)

    # Use get_config() for consistent environment variable loading
    from api.utils.config import get_config
    cfg = get_config()
    supabase_url = cfg["SUPABASE_URL"]
    supabase_key = cfg["SUPABASE_KEY"]
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment")

    supabase: Client = create_client(supabase_url, supabase_key)

    parser = argparse.ArgumentParser(description="Backfill corporate actions (dividends & splits) for asset universe")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of assets to fetch (0 or omit for all)")
    parser.add_argument("--dry-run", action="store_true", help="Just fetch and report counts, don't write to DB")
    parser.add_argument("--delay", type=float, default=20.0, help="Delay between Yahoo requests (seconds)")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of symbols to process per batch")
    parser.add_argument("--only-active", action="store_true", default=True, help="Only process assets where is_active=1 (default True)")

    args = parser.parse_args()

    only_active = True if args.only_active else False

    result = await backfill_corporate_actions(
        supabase, only_active=only_active, limit=args.limit, batch_size=args.batch_size, dry_run=args.dry_run, delay=args.delay
    )
    logger.info(f"DONE: {result}")


if __name__ == "__main__":
    asyncio.run(main())