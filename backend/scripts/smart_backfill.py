#!/usr/bin/env python3
"""
Smart Incremental Backfill Script
==================================

Queries DB for last date per asset and fetches only missing data.
Optimized for minimal API calls and duplicate avoidance.

Usage:
  python backend/scripts/smart_backfill.py --table eod
  python backend/scripts/smart_backfill.py --table intraday
  python backend/scripts/smart_backfill.py --table both

Environment:
  YF_DELAY_BETWEEN_REQUESTS (default: 20s)
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.utils.config import get_config
from supabase import create_client
from clients.yfinance_client import get_yfinance_client
from api.services.data_writer_service import get_data_writer
import argparse


def get_last_dates_for_assets(client, table_name: str = "price_history") -> Dict[int, Optional[datetime]]:
    """
    Query DB for the last timestamp per asset_id in the specified table.
    
    Returns:
        Dict mapping asset_id -> last datetime (or None if no data)
    """
    print(f"\n🔍 Querying last dates from {table_name}...")
    
    # Get all active assets
    assets_resp = (
        client.table("assets")
        .select("id,yfinance_ticker")
        .eq("is_active", 1)
        .not_.is_("yfinance_ticker", "null")
        .order("yfinance_ticker")
        .execute()
    )
    
    assets = {r["id"]: r["yfinance_ticker"] for r in (assets_resp.data or [])}
    last_dates = {}
    
    # Query last date for each asset
    for asset_id, ticker in assets.items():
        try:
            resp = (
                client.table(table_name)
                .select("timestamp")
                .eq("asset_id", asset_id)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            
            if resp.data:
                last_ts = resp.data[0]["timestamp"]
                last_dates[asset_id] = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
                print(f"  {ticker:20s} (id={asset_id:2d}): last date = {last_ts[:10]}")
            else:
                last_dates[asset_id] = None
                print(f"  {ticker:20s} (id={asset_id:2d}): NO DATA (will fetch all)")
        except Exception as e:
            print(f"  {ticker:20s} (id={asset_id:2d}): ERROR querying - {e}")
            last_dates[asset_id] = None
    
    return last_dates


async def backfill_eod_missing(client, args, dry_run: bool = False):
    """
    Backfill missing EOD data for all assets.
    Only fetches data from (last_date + 1 day) to today.
    """
    print(f"\n{'='*70}")
    print(f"EOD SMART BACKFILL (Missing Data Only)")
    print(f"{'='*70}")
    
    # Get last dates per asset
    last_dates = get_last_dates_for_assets(client, "price_history")
    
    # Get active assets mapping
    assets_resp = (
        client.table("assets")
        .select("id,yfinance_ticker")
        .eq("is_active", 1)
        .not_.is_("yfinance_ticker", "null")
        .order("yfinance_ticker")
        .execute()
    )
    
    id_to_ticker = {r["id"]: r["yfinance_ticker"] for r in (assets_resp.data or [])}
    ticker_to_id = {r["yfinance_ticker"]: r["id"] for r in (assets_resp.data or [])}
    
    # Build fetch plan
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    fetch_plan = []
    
    for asset_id, last_date in last_dates.items():
        ticker = id_to_ticker.get(asset_id)
        if not ticker:
            continue
        
        if last_date is None:
            # No data - fetch based on --days argument or default to 2 years
            days_to_fetch = getattr(args, 'days', 730)
            start_date = today - timedelta(days=days_to_fetch)
            days_missing = (today - start_date).days
        else:
            # Fetch from day after last date
            # Ensure last_date has timezone info
            if last_date.tzinfo is None:
                last_date = last_date.replace(tzinfo=timezone.utc)
            start_date = last_date + timedelta(days=1)
            days_missing = (today - start_date).days
        
        # Only fetch if missing days > 0
        if days_missing > 0:
            fetch_plan.append({
                "ticker": ticker,
                "asset_id": asset_id,
                "start_date": start_date,
                "end_date": today,
                "days_missing": days_missing,
            })
    
    print(f"\n📊 Fetch Plan Summary:")
    print(f"   Total assets: {len(id_to_ticker)}")
    print(f"   Assets needing updates: {len(fetch_plan)}")
    print(f"   Assets already current: {len(id_to_ticker) - len(fetch_plan)}")
    
    if not fetch_plan:
        print("\n✅ All assets are up-to-date! No fetching needed.")
        return {"status": "up-to-date", "fetched": 0, "inserted": 0}
    
    # Show top missing
    fetch_plan_sorted = sorted(fetch_plan, key=lambda x: x["days_missing"], reverse=True)
    print(f"\n📅 Top assets by missing days:")
    for item in fetch_plan_sorted[:10]:
        print(f"   {item['ticker']:20s}: {item['days_missing']:4d} days ({item['start_date'].date()} → {item['end_date'].date()})")
    
    if dry_run:
        print("\n🔍 DRY RUN complete. Use without --dry-run to execute.")
        return {"status": "dry-run", "plan": fetch_plan}
    
    # Execute fetch & store
    print(f"\n🚀 Starting incremental backfill for {len(fetch_plan)} assets...")
    print(f"   Rate limit: {os.getenv('YF_DELAY_BETWEEN_REQUESTS', '20')}s between requests")
    
    yf_client = get_yfinance_client()
    writer = get_data_writer()
    
    total_fetched = 0
    total_inserted = 0
    
    for idx, item in enumerate(fetch_plan, 1):
        ticker = item["ticker"]
        start_date = item["start_date"]
        end_date = item["end_date"]
        
        print(f"\n[{idx}/{len(fetch_plan)}] Fetching {ticker} from {start_date.date()} to {end_date.date()}...")
        
        try:
            df = await yf_client.fetch_historical_data(
                symbol=ticker,
                start_date=start_date,
                end_date=end_date,
                interval="1d",
                asset_type=None,
            )
            
            if df.empty:
                print(f"   ⚠️  No data returned for {ticker}")
                continue
            
            total_fetched += len(df)
            print(f"   ✓ Fetched {len(df)} rows")
            
            # Store data
            inserted = writer.store_data(ticker, df, source="yfinance")
            total_inserted += inserted
            
            if inserted > 0:
                print(f"   ✓ Inserted {inserted} new rows")
            else:
                print(f"   ℹ️  No new rows (duplicates or already exists)")
                
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            continue
    
    print(f"\n{'='*70}")
    print(f"EOD BACKFILL COMPLETE")
    print(f"{'='*70}")
    print(f"   Assets processed: {len(fetch_plan)}")
    print(f"   Total rows fetched: {total_fetched}")
    print(f"   Total rows inserted: {total_inserted}")
    
    return {
        "status": "complete",
        "assets_processed": len(fetch_plan),
        "rows_fetched": total_fetched,
        "rows_inserted": total_inserted,
    }


async def backfill_intraday_missing(client, args, dry_run: bool = False):
    """
    Backfill missing intraday 4h data for all assets.
    Only fetches data from (last_datetime + 4 hours) to now.
    """
    print(f"\n{'='*70}")
    print(f"INTRADAY 4H SMART BACKFILL (Missing Data Only)")
    print(f"{'='*70}")
    
    # Note: Intraday data uses same price_history table but with hourly timestamps
    # For true 4h intraday, we'd need a separate table or filter by time component
    # For now, treat as incremental from last timestamp
    
    last_dates = get_last_dates_for_assets(client, "price_history")
    
    # Get active assets
    assets_resp = (
        client.table("assets")
        .select("id,yfinance_ticker")
        .eq("is_active", 1)
        .not_.is_("yfinance_ticker", "null")
        .order("yfinance_ticker")
        .execute()
    )
    
    id_to_ticker = {r["id"]: r["yfinance_ticker"] for r in (assets_resp.data or [])}
    
    # Build fetch plan for intraday
    now = datetime.now(timezone.utc)
    fetch_plan = []
    
    for asset_id, last_date in last_dates.items():
        ticker = id_to_ticker.get(asset_id)
        if not ticker:
            continue
        
        if last_date is None:
            # No data - fetch last 30 days of intraday
            start_date = now - timedelta(days=30)
        else:
            # Fetch from 4 hours after last timestamp
            start_date = last_date + timedelta(hours=4)
        
        hours_missing = (now - start_date).total_seconds() / 3600
        
        # Only fetch if missing > 4 hours
        if hours_missing > 4:
            fetch_plan.append({
                "ticker": ticker,
                "asset_id": asset_id,
                "start_date": start_date,
                "end_date": now,
                "hours_missing": hours_missing,
            })
    
    print(f"\n📊 Fetch Plan Summary:")
    print(f"   Total assets: {len(id_to_ticker)}")
    print(f"   Assets needing intraday updates: {len(fetch_plan)}")
    
    if not fetch_plan:
        print("\n✅ All assets have current intraday data!")
        return {"status": "up-to-date", "fetched": 0, "inserted": 0}
    
    if dry_run:
        print("\n🔍 DRY RUN complete. Use without --dry-run to execute.")
        return {"status": "dry-run", "plan": fetch_plan}
    
    # Execute fetch & store
    print(f"\n🚀 Starting intraday backfill for {len(fetch_plan)} assets...")
    
    yf_client = get_yfinance_client()
    writer = get_data_writer()
    
    total_fetched = 0
    total_inserted = 0
    
    for idx, item in enumerate(fetch_plan, 1):
        ticker = item["ticker"]
        start_date = item["start_date"]
        end_date = item["end_date"]
        
        print(f"\n[{idx}/{len(fetch_plan)}] Fetching {ticker} intraday from {start_date.isoformat()[:19]}...")
        
        try:
            df = await yf_client.fetch_4hour_intraday(
                symbol=ticker,
                start_date=start_date,
                end_date=end_date,
                asset_type=None,
            )
            
            if df.empty:
                print(f"   ⚠️  No intraday data returned for {ticker}")
                continue
            
            total_fetched += len(df)
            print(f"   ✓ Fetched {len(df)} 4h candles")
            
            # Store hourly data
            inserted = writer.store_hourly_prices(ticker, df, source="yfinance")
            total_inserted += inserted
            
            if inserted > 0:
                print(f"   ✓ Inserted {inserted} new 4h candles")
            else:
                print(f"   ℹ️  No new candles (duplicates)")
                
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            continue
    
    print(f"\n{'='*70}")
    print(f"INTRADAY BACKFILL COMPLETE")
    print(f"{'='*70}")
    print(f"   Assets processed: {len(fetch_plan)}")
    print(f"   Total 4h candles fetched: {total_fetched}")
    print(f"   Total candles inserted: {total_inserted}")
    
    return {
        "status": "complete",
        "assets_processed": len(fetch_plan),
        "candles_fetched": total_fetched,
        "candles_inserted": total_inserted,
    }


async def main():
    parser = argparse.ArgumentParser(description="Smart incremental backfill")
    parser.add_argument(
        "--table",
        choices=["eod", "intraday", "both"],
        required=True,
        help="Which data to backfill",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--days", type=int, default=730, help="Days of history to fetch for new assets (default: 730)")
    args = parser.parse_args()
    
    cfg = get_config()
    client = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_KEY"])
    
    print(f"\n{'#'*70}")
    print(f"# SMART INCREMENTAL BACKFILL")
    print(f"{'#'*70}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Target: {args.table}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'COMMIT'}")
    
    results = {}
    
    if args.table in ("eod", "both"):
        results["eod"] = await backfill_eod_missing(client, args, args.dry_run)
    
    if args.table in ("intraday", "both"):
        results["intraday"] = await backfill_intraday_missing(client, args, args.dry_run)
    
    # Save report
    if not args.dry_run:
        out_dir = Path(__file__).parent.parent / "output"
        out_dir.mkdir(exist_ok=True)
        report_path = out_dir / f"smart_backfill_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "table": args.table,
            "results": results,
        }
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to: {report_path}")
    
    print(f"\n{'#'*70}")
    print(f"# BACKFILL COMPLETE")
    print(f"{'#'*70}\n")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
