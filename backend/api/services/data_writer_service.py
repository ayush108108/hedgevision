"""
Data Writer Service for HedgeVision API.

Handles WRITE operations to Supabase database for price data storage.
Extracted from query_service.py DataManager class (November 3, 2025).

This service is focused solely on persisting price data to the database.
For READ operations, use direct Supabase queries in your service layer.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional, Any, cast

import pandas as pd
from api.utils.config import config
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Set up logging
logger = logging.getLogger(__name__)

try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    # Provide lightweight stubs so static type checkers don't complain
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available. Install with: pip install supabase")
    Client = Any  # type: ignore
    def create_client(*_args: Any, **_kwargs: Any) -> Any:  # type: ignore
        raise RuntimeError("Supabase client not available")


class DataWriter:
    """
    DataWriter handles WRITE operations for financial data stores.

    Responsibilities:
    - Store daily OHLCV data to price_history table
    - Store hourly OHLCV data to price_history table
    - Batch upsert operations with conflict resolution
    - Asset ID resolution from symbol
    """

    def __init__(self):
        """Initialize data writer with local SQLite default and optional Supabase."""
        self.backend = str(config.get("DATA_BACKEND", "sqlite")).lower()
        self.db_path = str(config.get("DB_PATH"))
        self.supabase = None

        if self.backend == "sqlite":
            self._ensure_sqlite_schema()
            logger.info("DataWriter: SQLite backend initialized at %s", self.db_path)
            return

        # Use service key for write access when available
        self.supabase_url = config["SUPABASE_URL"]
        self.supabase_key = (
            config.get("SUPABASE_SERVICE_KEY")
            or config.get("SUPABASE_KEY")
            or config.get("SUPABASE_ANON_KEY")
        )

        if not self.supabase_url or not self.supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_KEY must be configured")
            self.supabase = None
            return

        if not SUPABASE_AVAILABLE:
            logger.error("Supabase client not available")
            self.supabase = None
            return

        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("DataWriter: Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {e}")
            self.supabase = None

    def _sqlite_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _ensure_sqlite_schema(self) -> None:
        try:
            with self._sqlite_connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL UNIQUE,
                        name TEXT,
                        yfinance_ticker TEXT UNIQUE,
                        is_active INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS price_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset_id INTEGER NOT NULL,
                        timestamp TEXT NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        source TEXT NOT NULL DEFAULT 'yfinance',
                        UNIQUE(asset_id, timestamp, source),
                        FOREIGN KEY(asset_id) REFERENCES assets(id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rolling_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset_id INTEGER NOT NULL,
                        benchmark_id INTEGER,
                        window_days INTEGER NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        rolling_beta REAL,
                        rolling_volatility REAL,
                        rolling_sharpe REAL,
                        rolling_sortino REAL,
                        max_drawdown REAL,
                        var_95 REAL,
                        cvar_95 REAL,
                        hurst_exponent REAL,
                        alpha REAL,
                        treynor REAL,
                        information_ratio REAL,
                        data_quality REAL,
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT,
                        UNIQUE(asset_id, benchmark_id, window_days, end_date),
                        FOREIGN KEY(asset_id) REFERENCES assets(id)
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_price_history_asset_ts "
                    "ON price_history(asset_id, timestamp)"
                )
        except Exception as exc:
            logger.error("Failed to initialize SQLite schema: %s", exc)

    def _get_asset_id(self, ticker: str, provider: str = "yfinance") -> Optional[int]:
        """Resolve asset_id for a ticker using provider-specific ticker column.

        Args:
            ticker: The provider-specific ticker (e.g., "AAPL" for yfinance, "AAPL.US" for EODHD)
            provider: Data provider name (yfinance, eodhd, polygon, etc.)
        
        Mappings by provider:
          - yfinance: assets.yfinance_ticker == ticker
          - eodhd: assets.eodhd_ticker == ticker
          - polygon: assets.polygon_ticker == ticker
          - tiingo: assets.tiingo_ticker == ticker
          - finnhub: assets.finnhub_ticker == ticker
          - fmp: assets.fmp_ticker == ticker
        """
        if self.backend == "sqlite":
            symbol = ticker.strip().upper()
            try:
                with self._sqlite_connect() as conn:
                    row = conn.execute(
                        "SELECT id FROM assets WHERE yfinance_ticker = ? OR symbol = ? LIMIT 1",
                        (ticker, symbol),
                    ).fetchone()
                    if row:
                        return int(row[0])
                    cursor = conn.execute(
                        "INSERT INTO assets(symbol, name, yfinance_ticker, is_active) VALUES (?, ?, ?, 1)",
                        (symbol, symbol, ticker),
                    )
                    return int(cursor.lastrowid)
            except Exception as exc:
                logger.error("Error resolving sqlite asset id for %s: %s", ticker, exc)
                return None

        if not self.supabase:
            return None
        
        # Map provider to column name
        provider_columns = {
            "yfinance": "yfinance_ticker",
            "eodhd": "eodhd_ticker",
            "polygon": "polygon_ticker",
            "tiingo": "tiingo_ticker",
            "binance": "binance_ticker",
            "finnhub": "finnhub_ticker",
            "fmp": "fmp_ticker",
        }
        
        column = provider_columns.get(provider.lower())
        if not column:
            logger.error(f"Unknown provider: {provider}")
            return None
        
        try:
            resp = (
                self.supabase.table("assets")
                .select("id")
                .eq(column, ticker)
                .limit(1)
                .execute()
            )
            if hasattr(resp, "data") and resp.data:
                return int(resp.data[0]["id"])

            logger.error(
                f"Asset not found for ticker '{ticker}' via {column}"
            )
            return None
        except Exception as e:
            logger.error(f"Error resolving asset id for {ticker} ({provider}): {e}")
            return None

    def store_multiple_symbols(
        self, data: dict[str, pd.DataFrame], source: str = "yfinance"
    ) -> dict[str, int]:
        """
        Store multiple symbols' daily OHLCV into price_history via a combined batch upsert.

        Args:
            data: Dictionary mapping symbol to DataFrame with OHLCV data
            source: Data source identifier (default: "yfinance")
        Returns:
            Dict of symbol -> newly inserted row count
        """
        results: dict[str, int] = {}
        if self.backend == "sqlite":
            for symbol, df in data.items():
                try:
                    results[symbol] = self.store_data(symbol, df, source=source)
                except Exception as exc:
                    logger.error("SQLite store failed for %s: %s", symbol, exc)
                    results[symbol] = 0
            return results

        if not self.supabase:
            logger.error("Supabase client not initialized; cannot store data")
            return results

        # Build rows for all symbols; also prefetch existing timestamps per symbol for duplicate detection
        all_rows: list[dict] = []
        existing_map: dict[int, set[str]] = {}
        symbol_asset: dict[str, int] = {}

        # Normalize then collect rows per symbol
        per_symbol_rows: dict[str, list[dict]] = {}
        for symbol, df in data.items():
            if df is None or df.empty:
                results[symbol] = 0
                continue
            asset_id = self._get_asset_id(symbol, provider=source)
            if asset_id is None:
                results[symbol] = 0
                continue
            symbol_asset[symbol] = asset_id

            # Normalize accepted columns similar to store_data
            if "date" in df.columns and "Date" not in df.columns:
                df = df.rename(
                    columns={
                        "date": "Date",
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                    }
                )
            if "timestamp" in df.columns and "Date" not in df.columns:
                df = df.rename(columns={"timestamp": "Date"})

            # Accept lowercase OHLCV column names even when 'timestamp' was present
            lower_to_title = {
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
            rename_map = {}
            for low_col, title_col in lower_to_title.items():
                if low_col in df.columns and title_col not in df.columns:
                    rename_map[low_col] = title_col
            if rename_map:
                df = df.rename(columns=rename_map)

            expected = ["Date", "Open", "High", "Low", "Close", "Volume"]
            if any(c not in df.columns for c in expected):
                results[symbol] = 0
                continue

            rows = []
            for _, row in df.iterrows():
                try:
                    # Extract & validate primitives first
                    open_val = row.get("Open")
                    high_val = row.get("High")
                    low_val_raw = row.get("Low")
                    close_val = row.get("Close")
                    vol_val = row.get("Volume")

                    o = float(open_val) if pd.notna(open_val) else None
                    h = float(high_val) if pd.notna(high_val) else None
                    low_v = float(low_val_raw) if pd.notna(low_val_raw) else None
                    c = float(close_val) if pd.notna(close_val) else None
                    v = float(vol_val) if (vol_val is not None and pd.notna(vol_val)) else None

                    if None in (o, h, low_v, c):
                        continue
                    # Narrow types for static analysis
                    o_f = cast(float, o)
                    h_f = cast(float, h)
                    low_f = cast(float, low_v)
                    c_f = cast(float, c)
                    if not (low_f <= h_f and low_f <= o_f <= h_f and low_f <= c_f <= h_f):
                        continue
                    ts = pd.to_datetime(row["Date"], utc=True).normalize().isoformat()
                    rows.append(
                        {
                            "asset_id": asset_id,
                            "timestamp": ts,
                            "open": o_f,
                            "high": h_f,
                            "low": low_f,
                            "close": c_f,
                            "volume": v,
                            "source": source,
                        }
                    )
                except Exception:
                    continue

            per_symbol_rows[symbol] = rows

        # Prefetch existing timestamps per symbol (within their respective date windows)
        for symbol, rows in per_symbol_rows.items():
            if not rows:
                results[symbol] = 0
                continue
            asset_id = symbol_asset[symbol]
            ts_min = min(r["timestamp"] for r in rows)
            ts_max = max(r["timestamp"] for r in rows)
            try:
                q = (
                    self.supabase.table("price_history")
                    .select("timestamp")
                    .eq("asset_id", asset_id)
                    .gte("timestamp", ts_min)
                    .lte("timestamp", ts_max)
                    .execute()
                )
                existing_map[asset_id] = set(str(r.get("timestamp")) for r in (q.data or []))
            except Exception:
                existing_map[asset_id] = set()

        # Compute inserted counts by set difference; aggregate all rows for bulk upsert
        for symbol, rows in per_symbol_rows.items():
            if not rows:
                continue
            asset_id = symbol_asset[symbol]
            existing = existing_map.get(asset_id, set())
            inserted_count = sum(1 for r in rows if r["timestamp"] not in existing)
            results[symbol] = inserted_count
            all_rows.extend(rows)

        # Bulk upsert across all symbols (schema-flexible on_conflict)
        if all_rows:
            batch_size = 500
            for i in range(0, len(all_rows), batch_size):
                batch = all_rows[i : i + batch_size]
                upsert_ok = False
                # Try with (asset_id,timestamp,source) then fallback to (asset_id,timestamp)
                for conflict_cols in ("asset_id,timestamp,source", "asset_id,timestamp"):
                    try:
                        (
                            self.supabase.table("price_history")
                            .upsert(batch, on_conflict=conflict_cols)
                            .execute()
                        )
                        upsert_ok = True
                        break
                    except Exception as e:
                        logger.debug(
                            f"Bulk upsert attempt with on_conflict='{conflict_cols}' failed: {e}"
                        )
                if not upsert_ok:
                    logger.error(
                        f"Bulk upsert failed for rows {i}-{i+len(batch)} after trying multiple on_conflict variants"
                    )

        # Log per-symbol outcomes
        for symbol, count in results.items():
            if count == 0:
                logger.info(f"No new rows for {symbol} — skipped (duplicates)")
            else:
                logger.info(f"Inserted {count} new rows for {symbol}")

        return results

    def store_data(self, symbol: str, df: pd.DataFrame, source: str = "yfinance") -> int:
        """
        Store daily OHLCV data for a single symbol into price_history.

        Args:
            symbol: Provider-specific ticker (e.g., "AAPL" for yfinance, "AAPL.US" for EODHD)
            df: DataFrame with columns: Date, Open, High, Low, Close, Volume
            source: Data source identifier/provider (default: "yfinance")
        """
        if df is None or df.empty:
            return 0
        asset_id = self._get_asset_id(symbol, provider=source)
        if asset_id is None:
            return 0

        # Normalize and validate columns (accept both Titlecase and lowercase standardized)
        cols = {c: c for c in df.columns}
        # If lowercase schema, map to Titlecase expected for internal handling
        if "date" in cols and "Date" not in cols:
            df = df.rename(
                columns={
                    "date": "Date",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
        if "timestamp" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"timestamp": "Date"})

        # Accept lowercase OHLCV column names when 'timestamp' path used
        lower_to_title = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        rename_map = {}
        for low_col, title_col in lower_to_title.items():
            if low_col in df.columns and title_col not in df.columns:
                rename_map[low_col] = title_col
        if rename_map:
            df = df.rename(columns=rename_map)

        expected = ["Date", "Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in expected if c not in df.columns]
        if missing:
            logger.error(f"Missing columns for {symbol}: {missing}")
            return 0

        rows = []
        for _, row in df.iterrows():
            try:
                open_val = row.get("Open")
                high_val = row.get("High")
                low_val_raw = row.get("Low")
                close_val = row.get("Close")
                vol_val = row.get("Volume")

                o = float(open_val) if pd.notna(open_val) else None
                h = float(high_val) if pd.notna(high_val) else None
                low_v = float(low_val_raw) if pd.notna(low_val_raw) else None
                c = float(close_val) if pd.notna(close_val) else None
                v = float(vol_val) if (vol_val is not None and pd.notna(vol_val)) else None

                if None in (o, h, low_v, c):
                    continue
                o_f = cast(float, o)
                h_f = cast(float, h)
                low_f = cast(float, low_v)
                c_f = cast(float, c)
                if not (low_f <= h_f and low_f <= o_f <= h_f and low_f <= c_f <= h_f):
                    continue
                dt_val = pd.to_datetime(row["Date"], utc=True)
                ts = dt_val.normalize().isoformat()
                rows.append(
                    {
                        "asset_id": asset_id,
                        "timestamp": ts,
                        "open": o_f,
                        "high": h_f,
                        "low": low_f,
                        "close": c_f,
                        "volume": v,
                        "source": source,
                    }
                )
            except Exception:
                continue

        if not rows:
            logger.warning(f"No valid rows to store for {symbol}")
            return 0

        if self.backend == "sqlite":
            ts_values = [r["timestamp"] for r in rows]
            ts_min = min(ts_values)
            ts_max = max(ts_values)
            try:
                with self._sqlite_connect() as conn:
                    existing = conn.execute(
                        """
                        SELECT timestamp FROM price_history
                        WHERE asset_id = ? AND timestamp >= ? AND timestamp <= ? AND source = ?
                        """,
                        (asset_id, ts_min, ts_max, source),
                    ).fetchall()
                    existing_ts = {str(r[0]) for r in existing}
                    conn.executemany(
                        """
                        INSERT INTO price_history(
                            asset_id, timestamp, open, high, low, close, volume, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(asset_id, timestamp, source) DO UPDATE SET
                            open=excluded.open,
                            high=excluded.high,
                            low=excluded.low,
                            close=excluded.close,
                            volume=excluded.volume
                        """,
                        [
                            (
                                r["asset_id"],
                                r["timestamp"],
                                r["open"],
                                r["high"],
                                r["low"],
                                r["close"],
                                r["volume"],
                                r["source"],
                            )
                            for r in rows
                        ],
                    )
                inserted_count = sum(1 for r in rows if r["timestamp"] not in existing_ts)
                if inserted_count == 0:
                    logger.info(
                        "No new rows for %s in %s..%s — skipped (duplicates)",
                        symbol,
                        ts_min[:10],
                        ts_max[:10],
                    )
                return inserted_count
            except Exception as exc:
                logger.error("SQLite store_data failed for %s: %s", symbol, exc)
                return 0

        if not self.supabase:
            return 0

        # Determine time window and fetch existing timestamps for duplicate detection
        ts_values = [r["timestamp"] for r in rows]
        ts_min = min(ts_values)
        ts_max = max(ts_values)

        try:
            before = (
                self.supabase.table("price_history")
                .select("timestamp")
                .eq("asset_id", asset_id)
                .gte("timestamp", ts_min)
                .lte("timestamp", ts_max)
                .execute()
            )
            existing_ts = set(str(r.get("timestamp")) for r in (before.data or []))
        except Exception:
            existing_ts = set()

        # Batch upserts to avoid payload limits (schema-flexible on_conflict)
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            upsert_ok = False
            for conflict_cols in ("asset_id,timestamp,source", "asset_id,timestamp"):
                try:
                    (
                        self.supabase.table("price_history")
                        .upsert(batch, on_conflict=conflict_cols)
                        .execute()
                    )
                    upsert_ok = True
                    break
                except Exception as e:
                    logger.debug(
                        f"Upsert attempt for {symbol} with on_conflict='{conflict_cols}' failed: {e}"
                    )
            if not upsert_ok:
                logger.error(
                    f"Upsert batch failed for {symbol} after trying multiple on_conflict variants"
                )

        # Estimate inserted as those timestamps not present before
        inserted_count = sum(1 for r in rows if r["timestamp"] not in existing_ts)

        # If no new rows inserted, likely duplicates
        if inserted_count == 0:
            logger.info(f"No new rows for {symbol} in {ts_min[:10]}..{ts_max[:10]} — skipped (duplicates)")

        return inserted_count

    def store_hourly_prices(
        self, symbol: str, hourly_df: pd.DataFrame, source: str = "yfinance"
    ) -> int:
        """
        Store hourly OHLCV data for a symbol into price_history.

        Args:
            symbol: Stock symbol
            hourly_df: DataFrame with columns: Timestamp, Open, High, Low, Close, Volume
            source: Data source identifier (default: "yfinance")
        """
        if hourly_df is None or hourly_df.empty:
            return 0
        asset_id = self._get_asset_id(symbol, provider=source)
        if asset_id is None:
            return 0

        # Accept lowercase/timestamp variants
        if "timestamp" in hourly_df.columns and "Timestamp" not in hourly_df.columns:
            hourly_df = hourly_df.rename(columns={"timestamp": "Timestamp"})
        if "date" in hourly_df.columns and "Timestamp" not in hourly_df.columns:
            hourly_df = hourly_df.rename(columns={"date": "Timestamp"})
        if "open" in hourly_df.columns and "Open" not in hourly_df.columns:
            hourly_df = hourly_df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )

        expected = ["Timestamp", "Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in expected if c not in hourly_df.columns]
        if missing:
            logger.error(f"Missing hourly columns for {symbol}: {missing}")
            return 0

        rows = []
        for _, row in hourly_df.iterrows():
            try:
                open_val = row.get("Open")
                high_val = row.get("High")
                low_val_raw = row.get("Low")
                close_val = row.get("Close")
                vol_val = row.get("Volume")

                o = float(open_val) if pd.notna(open_val) else None
                h = float(high_val) if pd.notna(high_val) else None
                low_v = float(low_val_raw) if pd.notna(low_val_raw) else None
                c = float(close_val) if pd.notna(close_val) else None
                v = float(vol_val) if (vol_val is not None and pd.notna(vol_val)) else None
                if None in (o, h, low_v, c):
                    continue
                o_f = cast(float, o)
                h_f = cast(float, h)
                low_f = cast(float, low_v)
                c_f = cast(float, c)
                if not (low_f <= h_f and low_f <= o_f <= h_f and low_f <= c_f <= h_f):
                    continue
                ts = pd.to_datetime(row["Timestamp"], utc=True).isoformat()
                rows.append(
                    {
                        "asset_id": asset_id,
                        "timestamp": ts,
                        "open": o_f,
                        "high": h_f,
                        "low": low_f,
                        "close": c_f,
                        "volume": v,
                        "source": source,
                    }
                )
            except Exception:
                continue

        if not rows:
            logger.warning(f"No valid hourly rows to store for {symbol}")
            return 0

        if self.backend == "sqlite":
            ts_values = [r["timestamp"] for r in rows]
            ts_min = min(ts_values)
            ts_max = max(ts_values)
            try:
                with self._sqlite_connect() as conn:
                    existing = conn.execute(
                        """
                        SELECT timestamp FROM price_history
                        WHERE asset_id = ? AND timestamp >= ? AND timestamp <= ? AND source = ?
                        """,
                        (asset_id, ts_min, ts_max, source),
                    ).fetchall()
                    existing_ts = {str(r[0]) for r in existing}
                    conn.executemany(
                        """
                        INSERT INTO price_history(
                            asset_id, timestamp, open, high, low, close, volume, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(asset_id, timestamp, source) DO UPDATE SET
                            open=excluded.open,
                            high=excluded.high,
                            low=excluded.low,
                            close=excluded.close,
                            volume=excluded.volume
                        """,
                        [
                            (
                                r["asset_id"],
                                r["timestamp"],
                                r["open"],
                                r["high"],
                                r["low"],
                                r["close"],
                                r["volume"],
                                r["source"],
                            )
                            for r in rows
                        ],
                    )
                inserted_count = sum(1 for r in rows if r["timestamp"] not in existing_ts)
                if inserted_count == 0:
                    logger.info(
                        "No new hourly rows for %s in %s..%s — skipped (duplicates)",
                        symbol,
                        ts_min,
                        ts_max,
                    )
                return inserted_count
            except Exception as exc:
                logger.error("SQLite store_hourly_prices failed for %s: %s", symbol, exc)
                return 0

        if not self.supabase:
            return 0

        # Determine time window and fetch existing timestamps
        ts_values = [r["timestamp"] for r in rows]
        ts_min = min(ts_values)
        ts_max = max(ts_values)
        try:
            before = (
                self.supabase.table("price_history")
                .select("timestamp")
                .eq("asset_id", asset_id)
                .gte("timestamp", ts_min)
                .lte("timestamp", ts_max)
                .execute()
            )
            existing_ts = set(str(r.get("timestamp")) for r in (before.data or []))
        except Exception:
            existing_ts = set()

        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            upsert_ok = False
            for conflict_cols in ("asset_id,timestamp,source", "asset_id,timestamp"):
                try:
                    (
                        self.supabase.table("price_history")
                        .upsert(batch, on_conflict=conflict_cols)
                        .execute()
                    )
                    upsert_ok = True
                    break
                except Exception as e:
                    logger.debug(
                        f"Upsert hourly attempt for {symbol} with on_conflict='{conflict_cols}' failed: {e}"
                    )
            if not upsert_ok:
                logger.error(
                    f"Upsert hourly batch failed for {symbol} after trying multiple on_conflict variants"
                )

        inserted_count = sum(1 for r in rows if r["timestamp"] not in existing_ts)

        if inserted_count == 0:
            logger.info(f"No new hourly rows for {symbol} in {ts_min}..{ts_max} — skipped (duplicates)")

        return inserted_count


# Global data writer instance
_data_writer = None


def get_data_writer() -> DataWriter:
    """Get the global data writer instance."""
    global _data_writer
    if _data_writer is None:
        _data_writer = DataWriter()
    return _data_writer
