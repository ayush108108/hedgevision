#!/usr/bin/env python3
"""Bootstrap a usable local SQLite dataset for HedgeVision.

This script:
1. Backfills ~2 years of daily data for a curated set of symbols.
2. Computes rolling metrics for SQLite.
3. Optionally seeds a handful of cointegration test results via the local API.

It is designed to make the app usable end-to-end in local-first mode.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
for path in (REPO_ROOT, BACKEND_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from api.services.pipeline_service import PipelineService
from api.utils.config import config

CURATED_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "ADA-USD",
    "AVAX-USD",
    "DOT-USD",
    "LINK-USD",
    "AAVE-USD",
    "DOGE-USD",
    "SPY",
    "QQQ",
    "GLD",
    "TLT",
    "NVDA",
    "TSLA",
    "MSTR",
]

COINTEGRATION_PAIRS = [
    ("BTC-USD", "ETH-USD"),
    ("ETH-USD", "SOL-USD"),
    ("BNB-USD", "SOL-USD"),
    ("ADA-USD", "DOT-USD"),
    ("BTC-USD", "LINK-USD"),
]


def _existing_symbols(db_path: str) -> set[str]:
    with sqlite3.connect(db_path, timeout=5.0) as conn:
        rows = conn.execute("SELECT symbol FROM assets").fetchall()
    return {str(row[0]) for row in rows}


async def _backfill_symbols(symbols: Iterable[str], days_back: int = 730) -> dict[str, int]:
    service = PipelineService()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)

    results: dict[str, int] = {}
    symbol_list = list(symbols)
    print(f"📦 Backfilling {len(symbol_list)} symbols from {start_date.date()} to {end_date.date()}...")

    for i in range(0, len(symbol_list), 5):
        batch = symbol_list[i : i + 5]
        print(f"  • Batch {i // 5 + 1}: {batch}")
        summary = await service.run_multi_fetch_store(
            symbols=batch,
            start_date=start_date,
            end_date=end_date,
            granularity="daily",
            group_size=5,
            validate=True,
        )
        for sym in batch:
            inserted = int(summary["results"].get(sym, {}).get("records_stored", 0))
            results[sym] = results.get(sym, 0) + inserted
            print(f"    - {sym}: {inserted} new rows")

    await service.close()
    return results


def _compute_rolling_metrics() -> None:
    print("📈 Computing rolling metrics for SQLite...")
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "populate_sqlite_metrics.py")],
        check=True,
        cwd=str(REPO_ROOT),
    )


def _seed_cointegration_results() -> None:
    print("🧪 Seeding cointegration results through local API (best effort)...")
    for asset1, asset2 in COINTEGRATION_PAIRS:
        payload = json.dumps(
            {
                "asset1": asset1,
                "asset2": asset2,
                "granularity": "daily",
                "lookback_days": 252,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:8000/api/cointegration/test-pair",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
            print(f"  ✓ {asset1}/{asset2}: test_id={data.get('test_id')}")
        except urllib.error.URLError as exc:
            print(f"  ⚠️  Skipping cointegration seed for {asset1}/{asset2}: {exc}")
            break
        except Exception as exc:  # pragma: no cover - best effort seeding
            print(f"  ⚠️  Seed failed for {asset1}/{asset2}: {exc}")


def _print_db_summary(db_path: str) -> None:
    with sqlite3.connect(db_path, timeout=5.0) as conn:
        asset_count = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
        price_count = int(conn.execute("SELECT COUNT(*) FROM price_history").fetchone()[0])
        metric_count = int(conn.execute("SELECT COUNT(*) FROM rolling_metrics").fetchone()[0])
        try:
            coint_count = int(conn.execute("SELECT COUNT(*) FROM cointegration_scores").fetchone()[0])
        except sqlite3.OperationalError:
            coint_count = 0
        date_min, date_max = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM price_history"
        ).fetchone()

    print("\n✅ SQLite summary")
    print(f"   assets: {asset_count}")
    print(f"   price_history: {price_count}")
    print(f"   rolling_metrics: {metric_count}")
    print(f"   cointegration_scores: {coint_count}")
    print(f"   date_range: {date_min} -> {date_max}")


def main() -> int:
    db_path = str(config.get("DB_PATH", "backend/prices.db"))
    abs_db_path = str((REPO_ROOT / db_path).resolve()) if not os.path.isabs(db_path) else db_path

    print(f"🗄️  Using SQLite database: {abs_db_path}")
    existing = _existing_symbols(abs_db_path)
    target_symbols = [symbol for symbol in CURATED_SYMBOLS if symbol in existing]

    if len(target_symbols) < 6:
        print("❌ Not enough curated symbols exist in SQLite assets table.")
        return 1

    print(f"🎯 Target symbols ({len(target_symbols)}): {', '.join(target_symbols)}")

    results = asyncio.run(_backfill_symbols(target_symbols, days_back=730))
    print(f"\n📊 Backfill complete: {sum(results.values())} new rows across {len(results)} symbols")

    _compute_rolling_metrics()
    _seed_cointegration_results()
    _print_db_summary(abs_db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
