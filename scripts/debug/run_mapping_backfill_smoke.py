#!/usr/bin/env python3
"""
Smoke-run mapping validation + small backfill for a handful of assets.

This script is intentionally conservative: defaults to dry-run and skip-validation.
Run with --commit --backfill to actually write changes and backfill price history.

Example:
    python scripts/debug/run_mapping_backfill_smoke.py --commit --backfill --symbols BTC-USD,ETH-USD

"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Add project root to sys.path so `backend` package is importable
sys.path.insert(0, str(ROOT))

from backend.scripts.validate_and_fix_yfinance_tickers import validate_and_fix_tickers


def _parse_args():
    ap = argparse.ArgumentParser(description="Run mapping validation and optionally small backfill")
    ap.add_argument("--commit", action="store_true", help="Apply mapping changes to DB (default: dry-run)")
    ap.add_argument("--skip-validation", action="store_true", help="Skip yfinance validation for faster runs")
    ap.add_argument("--backfill", action="store_true", help="Run a small backfill for specified symbols")
    ap.add_argument("--symbols", type=str, default="", help="Comma-separated symbols to backfill");
    return ap.parse_args()


def main():
    args = _parse_args()

    print("Running yfinance mapping validation (dry-run unless --commit)")
    results = validate_and_fix_tickers(commit=args.commit, skip_validation=args.skip_validation)
    print("Mapping validation results:", results)

    if args.backfill:
        print("Backfill requested. Note this will perform network calls and DB writes via DataWriter")
        if not args.symbols:
            print("No symbols provided. Use --symbols to pass a list like BTC-USD,ETH-USD")
            return
        from scripts.pipelines.populate_price_history_all_time import main as pf_main
        # Build args string for pipeline
        sys_argv = ["populate_price_history_all_time.py", "--symbols", args.symbols, "--limit-assets", "0", "--dry-run"]
        if args.commit:
            # If commit, then not dry-run for the second stage
            sys_argv = ["populate_price_history_all_time.py", "--symbols", args.symbols]
        print(f"Launching backfill pipeline with args: {sys_argv}")
        import sys as _sys
        _sys.argv = sys_argv
        pf_main()


if __name__ == "__main__":
    sys.exit(main())
