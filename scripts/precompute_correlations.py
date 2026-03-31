"""
Precompute correlation matrices and store them in Supabase.

Usage (PowerShell):

  # Daily, pearson, 60-day lookback (default)
  python scripts/precompute_correlations.py

  # Spearman, 90-day lookback
  python scripts/precompute_correlations.py --method spearman --lookback 90

  # Both methods
  python scripts/precompute_correlations.py --method both --lookback 60

  # Hourly granularity (ensure hourly data available)
  python scripts/precompute_correlations.py --granularity hourly --lookback 240

Environment:
  Requires SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY/ANON) to be set.
  Optionally pass --sector to limit symbols; defaults to all active assets from Supabase,
  falling back to the static asset map if Supabase lookup fails.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import List

# Ensure repo import path and make backend/api importable as package `api`
import sys
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_path = os.path.join(repo_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from dotenv import load_dotenv
from api.utils.supabase_client import get_supabase_client
from api.services.correlation_service import CorrelationService
from api.utils.assets import asset_sectors, name_to_symbol

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("precompute_correlations")


def _get_active_symbols_from_supabase() -> List[str]:
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = (
            client.client.table("assets")
            .select("symbol,is_active")
            .eq("is_active", 1)
            .execute()
        )
        symbols = [row["symbol"] for row in (res.data or []) if row.get("symbol")]
        return sorted(list(set(symbols)))
    except Exception as e:
        logger.warning(f"Unable to read active assets from Supabase: {e}")
        return []


def _symbols_for_sector(sector: str | None) -> List[str]:
    if not sector or sector.lower() == "all":
        # Flatten all sectors
        names = {n for arr in asset_sectors.values() for n in arr}
        return sorted([name_to_symbol.get(n, n) for n in names])

    # Match sector case-insensitively
    for s, names in asset_sectors.items():
        if s.lower() == sector.lower():
            return sorted([name_to_symbol.get(n, n) for n in names])

    logger.warning(f"Unknown sector '{sector}' - defaulting to all mapped assets")
    names = {n for arr in asset_sectors.values() for n in arr}
    return sorted([name_to_symbol.get(n, n) for n in names])


def main():
    # Load environment variables from common locations
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    api_env = os.path.join(repo_root, "backend", "api", ".env")
    root_env = os.path.join(repo_root, ".env")
    # Load backend/api/.env first, then root .env to allow overrides
    load_dotenv(api_env)
    load_dotenv(root_env)

    parser = argparse.ArgumentParser(description="Precompute and store correlation matrices")
    parser.add_argument("--granularity", choices=["daily", "hourly"], default="daily")
    parser.add_argument("--method", choices=["pearson", "spearman", "both"], default="pearson")
    parser.add_argument("--lookback", type=int, default=60, help="Lookback window in days (or hours for hourly)")
    parser.add_argument("--sector", type=str, default=None, help="Optional sector filter (e.g., 'US Stocks')")
    args = parser.parse_args()

    # Verify env
    if not os.getenv("SUPABASE_URL"):
        logger.error("SUPABASE_URL not set")
        sys.exit(1)
    if not (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")):
        logger.error("A Supabase key (SERVICE/ANON) must be set in environment")
        sys.exit(1)

    # Pick symbols
    symbols: List[str] = _get_active_symbols_from_supabase()
    if not symbols:
        logger.info("Falling back to static asset map for symbols")
        symbols = _symbols_for_sector(args.sector)

    if len(symbols) < 2:
        logger.error("Not enough symbols to compute correlations")
        sys.exit(1)

    logger.info(
        f"Starting precompute: granularity={args.granularity}, method={args.method}, lookback={args.lookback}, symbols={len(symbols)}"
    )

    supa = get_supabase_client()
    if not supa:
        logger.error("Failed to initialize Supabase client")
        sys.exit(1)

    svc = CorrelationService(supabase_client=supa)

    methods = [args.method] if args.method != "both" else ["pearson", "spearman"]

    for m in methods:
        logger.info(f"Computing method={m} ...")
        result = svc.compute_correlation_matrix(
            asset_symbols=symbols,
            granularity=args.granularity,
            method=m,
            lookback_days=args.lookback,
        )
        if result:
            logger.info(f"Stored {m} correlation matrix with {len(result)} rows")
        else:
            logger.warning(f"No result for method={m}")

    logger.info("Precompute complete")


if __name__ == "__main__":
    main()
