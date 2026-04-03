#!/usr/bin/env python3
"""Initialize the SQLite database schema for HedgeVision.

Creates all tables used in local-first (SQLite) mode.
Safe to run multiple times — uses CREATE TABLE IF NOT EXISTS.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
for p in (REPO_ROOT, BACKEND_ROOT):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from api.utils.config import config


def init_db() -> None:
    import sqlite3

    db_path = config.get("DB_PATH", str(BACKEND_ROOT / "prices.db"))
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=10.0)
    cur = conn.cursor()

    # --- Core tables (from DataWriter) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            yfinance_ticker TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            source TEXT DEFAULT 'yfinance',
            FOREIGN KEY (asset_id) REFERENCES assets(id),
            UNIQUE(asset_id, timestamp, source)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_history_asset_ts
        ON price_history(asset_id, timestamp)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rolling_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            benchmark_id INTEGER,
            window_days INTEGER NOT NULL,
            start_date TEXT, end_date TEXT,
            beta REAL, volatility_annual REAL,
            sharpe_ratio REAL, sortino_ratio REAL,
            max_drawdown REAL, var_95 REAL, cvar_95 REAL,
            hurst_exponent REAL, alpha REAL,
            treynor_ratio REAL, information_ratio REAL,
            data_quality_score REAL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        )
    """)

    # --- Cointegration scores ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cointegration_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset1_symbol TEXT NOT NULL,
            asset2_symbol TEXT NOT NULL,
            test_date TEXT,
            granularity TEXT DEFAULT 'daily',
            lookback_days INTEGER DEFAULT 365,
            cointegration_score REAL,
            p_value REAL,
            eg_test_stat REAL,
            eg_critical_1pct REAL,
            eg_critical_5pct REAL,
            eg_critical_10pct REAL,
            half_life_days REAL,
            sharpe_ratio REAL,
            test_results TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # --- Correlation screener ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS correlation_screener (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset1_id INTEGER NOT NULL,
            asset2_id INTEGER NOT NULL,
            correlation REAL NOT NULL,
            p_value REAL,
            method TEXT NOT NULL DEFAULT 'spearman',
            granularity TEXT NOT NULL DEFAULT 'daily',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(asset1_id, asset2_id, method, granularity)
        )
    """)

    # --- Waitlist signups ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS waitlist_signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            source_page TEXT,
            source_label TEXT,
            metadata_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database initialized at {db_path}")


if __name__ == "__main__":
    init_db()
