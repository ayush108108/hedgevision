#!/usr/bin/env python3
"""
Update yfinance ticker mappings for the pilot validation universe.

Ensures assets inserted via bootstrap use provider tickers that match Yahoo Finance
identifiers so price ingestion scripts resolve asset IDs correctly.

Usage (PowerShell):
  python scripts/db/update_pilot_tickers.py --commit
  python scripts/db/update_pilot_tickers.py              # dry-run preview
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT_DIR))

from backend.api.utils.config import get_config  # type: ignore
from supabase import create_client  # type: ignore


TICKER_MAP: Dict[str, Dict[str, str]] = {
    # Equities / ETFs remain unchanged (SPY, QQQ, KO, PEP)
    "USDJPY": {"yfinance_ticker": "JPY=X", "name": "usd/jpy"},
    "EURUSD": {"yfinance_ticker": "EURUSD=X", "name": "eur/usd"},
    "XAUUSD": {"yfinance_ticker": "GC=F", "name": "gold futures"},
    "WTI": {"yfinance_ticker": "CL=F", "name": "wti crude oil"},
    "BTC": {"yfinance_ticker": "BTC-USD", "name": "bitcoin"},
    "ETH": {"yfinance_ticker": "ETH-USD", "name": "ethereum"},
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Update Supabase yfinance tickers for pilot assets")
    ap.add_argument(
        "--commit",
        action="store_true",
        help="Apply updates. Without this flag the script runs as a dry-run.",
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cfg = get_config()
    service_key = cfg.get("SUPABASE_SERVICE_KEY") or cfg.get("SUPABASE_KEY")
    if not cfg.get("SUPABASE_URL") or not service_key:
        print("Missing SUPABASE_URL or Supabase key; aborting.")
        return 1

    client = create_client(cfg["SUPABASE_URL"], service_key)
    pending_updates = []

    for source_symbol, payload in TICKER_MAP.items():
        try:
            resp = (
                client.table("assets")
                .select("id,yfinance_ticker,name")
                .eq("yfinance_ticker", source_symbol)
                .limit(1)
                .execute()
            )
            row = resp.data[0] if resp.data else None
            if not row:
                print(f"[skip] No asset found with yfinance_ticker='{source_symbol}'")
                continue

            update = {"id": row["id"], **payload}
            pending_updates.append(update)
            print(
                f"[plan] id={row['id']}: {source_symbol} -> {payload.get('yfinance_ticker', source_symbol)}"
            )
        except Exception as exc:
            print(f"[error] Failed lookup for {source_symbol}: {exc}")

    if not pending_updates:
        print("No matching assets found; nothing to update.")
        return 0

    if not args.commit:
        print("\nDry run complete. Use --commit to apply updates.")
        return 0

    for update in pending_updates:
        asset_id = update.pop("id")
        try:
            client.table("assets").update(update).eq("id", asset_id).execute()
            print(f"[ok] Updated asset id={asset_id}")
        except Exception as exc:
            print(f"[error] Failed update for id={asset_id}: {exc}")

    print("Pilot ticker updates complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
