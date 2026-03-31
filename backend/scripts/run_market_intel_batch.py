#!/usr/bin/env python3
"""Batch runner for Market Intelligence sequential workflow.

Example:
  python backend/scripts/run_market_intel_batch.py --tickers AAPL,MSFT,NVDA \
      --output backend/output/market_intel_results_latest.json

Generates consolidated JSON with per-ticker market data, sentiment (neutral if no URL),
quant metrics, and strategy decision.
"""
from __future__ import annotations

import argparse, json, datetime, sys, os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.market_intel import run_sequential  # type: ignore


def parse_args():
    ap = argparse.ArgumentParser(description="Run market-intel sequential workflow for multiple tickers")
    ap.add_argument("--tickers", required=True, help="Comma-separated tickers (e.g. AAPL,MSFT,NVDA)")
    ap.add_argument("--output", default=None, help="Output JSON path (default: backend/output/market_intel_results_<ts>.json)")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        print("No tickers provided")
        return 1

    results = {}
    for t in tickers:
        try:
            res = run_sequential(t)
            results[t] = res.to_dict()
        except Exception as e:
            results[t] = {"error": str(e)}

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = args.output or f"backend/output/market_intel_results_{ts}.json"
    Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "tickers": tickers,
        "results": results,
        "workflow": "sequential-market-intel",
        "version": "v1",
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
