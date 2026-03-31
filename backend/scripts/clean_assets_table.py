#!/usr/bin/env python3
"""
Clean & normalize assets table:
1. De-duplicate symbols (case-insensitive; prefer .US suffixed version as canonical)
2. Normalize human-readable names to lowercase (apple, microsoft, netflix)
3. Add descriptions where missing
4. Ensure all provider tickers mapped (yfinance, eodhd, polygon, etc.)
5. Merge data from duplicate rows into canonical row
6. Delete duplicates

Usage (PowerShell):
  python backend/scripts/clean_assets_table.py --dry-run
  python backend/scripts/clean_assets_table.py --commit
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.utils.config import get_config
from supabase import create_client

# Friendly names mapping (lowercase)
NAME_MAP = {
    "AAPL": "apple",
    "MSFT": "microsoft",
    "GOOGL": "alphabet",
    "AMZN": "amazon",
    "META": "meta platforms",
    "NVDA": "nvidia",
    "TSLA": "tesla",
    "NFLX": "netflix",
    "SPY": "s&p 500 etf",
    "QQQ": "nasdaq 100 etf",
    "DIA": "dow jones etf",
    "IWM": "russell 2000 etf",
    "GLD": "gold etf",
    "SLV": "silver etf",
    "TLT": "20+ year treasury etf",
    "IEF": "7-10 year treasury etf",
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
}

# Description templates
DESC_MAP = {
    "AAPL": "Consumer electronics and software; iPhone, Mac, iPad",
    "MSFT": "Software and cloud computing; Windows, Azure, Office",
    "GOOGL": "Internet services and advertising; Google Search, YouTube, Android",
    "AMZN": "E-commerce and cloud computing; AWS, Prime, Marketplace",
    "META": "Social media and virtual reality; Facebook, Instagram, WhatsApp",
    "NVDA": "Graphics processors and AI chips; GeForce, data center GPUs",
    "TSLA": "Electric vehicles and energy storage; Model S/3/X/Y, Powerwall",
    "NFLX": "Streaming entertainment service",
    "SPY": "SPDR S&P 500 ETF Trust tracking the S&P 500 index",
    "QQQ": "Invesco QQQ Trust tracking Nasdaq-100 index",
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    ap.add_argument("--commit", action="store_true", help="Actually apply changes to DB")
    return ap.parse_args()


def normalize_symbol(sym: str) -> str:
    """Extract base symbol from variants like AAPL.US, AAPL, etc."""
    return sym.replace(".US", "").replace(".FOREX", "").replace(".CC", "").upper()


def get_canonical_suffix(symbols: List[str]) -> str:
    """Pick canonical format; prefer .US for stocks."""
    if any(s.endswith(".US") for s in symbols):
        return next(s for s in symbols if s.endswith(".US"))
    return sorted(symbols)[0]  # fallback to alphabetical


def main():
    args = parse_args()
    if not args.dry_run and not args.commit:
        print("Specify --dry-run or --commit")
        return 1

    cfg = get_config()
    client = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_KEY"])
    resp = client.table("assets").select("*").execute()
    assets = resp.data or []

    # Group by normalized base symbol
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for a in assets:
        base = normalize_symbol(a["symbol"])
        groups.setdefault(base, []).append(a)

    to_delete = []
    to_update = []

    for base, rows in groups.items():
        if len(rows) == 1:
            # No duplicate; just normalize name/description
            r = rows[0]
            friendly = NAME_MAP.get(base, base.lower())
            desc = DESC_MAP.get(base, f"{friendly} asset")
            if r["name"] != friendly or not r.get("description"):
                to_update.append({
                    "id": r["id"],
                    "name": friendly,
                    "description": desc,
                })
        else:
            # Duplicate found
            canonical_sym = get_canonical_suffix([r["symbol"] for r in rows])
            canonical = next(r for r in rows if r["symbol"] == canonical_sym)
            dupes = [r for r in rows if r["id"] != canonical["id"]]

            friendly = NAME_MAP.get(base, base.lower())
            desc = DESC_MAP.get(base, f"{friendly} asset")

            # Merge ticker mappings
            merged = {
                "id": canonical["id"],
                "symbol": canonical["symbol"],
                "name": friendly,
                "description": desc,
                "yfinance_ticker": canonical.get("yfinance_ticker") or base,
                "eodhd_ticker": canonical.get("eodhd_ticker") or f"{base}.US",
                "polygon_ticker": canonical.get("polygon_ticker") or base,
            }
            # Override with any non-null values from dupes
            for d in dupes:
                for k in ["yfinance_ticker", "eodhd_ticker", "polygon_ticker"]:
                    if d.get(k):
                        merged[k] = d[k]

            to_update.append(merged)
            to_delete.extend([d["id"] for d in dupes])

            print(f"\nDuplicate: {base}")
            print(f"  Canonical: {canonical['symbol']} (id={canonical['id']})")
            print(f"  Duplicates to delete: {[d['symbol'] + ' (id=' + str(d['id']) + ')' for d in dupes]}")

    print(f"\nSummary:")
    print(f"  Assets to update: {len(to_update)}")
    print(f"  Assets to delete: {len(to_delete)}")

    if args.dry_run:
        print("\nDry-run complete. Use --commit to apply changes.")
        return 0

    # Apply updates
    for u in to_update:
        try:
            client.table("assets").update({
                "name": u["name"],
                "description": u.get("description"),
                "yfinance_ticker": u.get("yfinance_ticker"),
                "eodhd_ticker": u.get("eodhd_ticker"),
                "polygon_ticker": u.get("polygon_ticker"),
            }).eq("id", u["id"]).execute()
            print(f"Updated asset id={u['id']}")
        except Exception as e:
            print(f"Error updating id={u['id']}: {e}")

    # Delete duplicates
    for did in to_delete:
        try:
            client.table("assets").delete().eq("id", did).execute()
            print(f"Deleted asset id={did}")
        except Exception as e:
            print(f"Error deleting id={did}: {e}")

    print("\nCleanup complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
