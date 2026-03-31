"""
Database schema validation tests using direct Postgres introspection.

These tests assert the presence of critical tables and columns and lightly
validate data types and constraints. They run against the configured Supabase
Postgres instance and will be skipped if no DB URL is configured.
"""

from __future__ import annotations
from typing import Dict, List, Tuple

import psycopg2
import pytest


pytestmark = [pytest.mark.supabase, pytest.mark.database]


def _connect_or_skip(dsn: str):
    try:
        return psycopg2.connect(dsn)
    except Exception as e:
        pytest.skip(f"Direct DB connection unavailable: {e}")


def _columns_for_table(conn, table: str, schema: str = "public") -> List[Tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return cur.fetchall()


def _tables_exist(conn, tables: List[str], schema: str = "public") -> Dict[str, bool]:
    exists: Dict[str, bool] = {}
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
                """,
                (schema, t),
            )
            exists[t] = cur.fetchone()[0]
    return exists


@pytest.mark.parametrize(
    "table_key",
    ["assets", "price_history", "rolling_metrics", "correlation_matrix", "pair_trades"],
)
def test_tables_and_columns_present(db_connection_string: str, expected_columns: Dict[str, List[str]], table_key: str):
    conn = _connect_or_skip(db_connection_string)
    try:
        # Table exists
        table_exists = _tables_exist(conn, [table_key])[table_key]
        assert table_exists, f"Table '{table_key}' does not exist in schema"

        # Required columns exist (as subset)
        cols = _columns_for_table(conn, table_key)
        col_names = {name for name, _ in cols}
        missing = [c for c in expected_columns[table_key] if c not in col_names]
        assert not missing, f"Missing columns in {table_key}: {missing}"
    finally:
        conn.close()


def test_rolling_metrics_column_types(db_connection_string: str):
    conn = _connect_or_skip(db_connection_string)
    try:
        cols = dict(_columns_for_table(conn, "rolling_metrics"))

        # Core identifiers and dates
        assert cols.get("id") in {"integer", "bigint"}
        assert cols.get("asset_id") in {"integer", "bigint"}
        assert cols.get("window_days") in {"integer", "bigint"}
        assert cols.get("start_date") in {"date", "timestamp without time zone", "timestamp with time zone"}
        assert cols.get("end_date") in {"date", "timestamp without time zone", "timestamp with time zone"}

        # Metrics should be numeric-ish
        numeric_like = {"numeric", "double precision", "real"}
        for mcol in [
            "rolling_beta",
            "rolling_volatility",
            "rolling_sharpe",
            "rolling_sortino",
            "max_drawdown",
            "var_95",
            "cvar_95",
            "hurst_exponent",
        ]:
            if mcol in cols:  # tolerate absent optional columns
                assert cols[mcol] in numeric_like, f"{mcol} should be numeric, got {cols[mcol]}"

    finally:
        conn.close()


def test_optional_rolling_correlation_column_presence(db_connection_string: str):
    """
    Document the presence/absence of rolling_correlation in rolling_metrics.

    If absent, skip with a clear message to indicate backend support hasn't been
    wired yet. This prevents false negatives while keeping visibility.
    """
    conn = _connect_or_skip(db_connection_string)
    try:
        cols = dict(_columns_for_table(conn, "rolling_metrics"))
        if "rolling_correlation" not in cols:
            pytest.skip("rolling_correlation column not present in rolling_metrics (expected future addition)")
        # If present, ensure numeric type
        assert cols["rolling_correlation"] in {"numeric", "double precision", "real"}
    finally:
        conn.close()
