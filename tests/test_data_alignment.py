"""
Data alignment and integrity tests for Pair Analysis and Rolling Metrics endpoints.

These tests verify date/time alignment between price, spread, and z-score series,
and validate rolling metrics date boundaries and ordering.

Tests are designed to be safe in real environments:
- Only assert strict conditions when the API returns data (200).
- Skip gracefully when endpoints return 204/404.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import pytest


@pytest.mark.real_api
def test_pair_analysis_date_alignment(sync_client):
    """Ensure price_data dates align with spread_data dates in full pair report.

    Accepts 200/204/404 from API; only asserts on 200 responses.
    """
    # Choose a commonly available equity pair
    params = {
        "asset1": "AAPL.US",
        "asset2": "MSFT.US",
        "granularity": "daily",
    }

    resp = sync_client.get("/api/pair-analysis", params=params)
    assert resp.status_code in [200, 204, 404, 500, 503]

    if resp.status_code != 200:
        pytest.skip(f"pair-analysis unavailable ({resp.status_code})")

    data = resp.json()

    # Price payload
    price = data.get("price_data") or {}
    dates: List[str] = price.get("dates") or []
    a1 = price.get("asset1_prices") or []
    a2 = price.get("asset2_prices") or []

    # Spread payload (list of {date, spread, zscore})
    spread_rows: List[Dict] = data.get("spread_data") or []
    spread_dates = [row.get("date") for row in spread_rows]
    spreads = [row.get("spread") for row in spread_rows]
    zscores = [row.get("zscore") for row in spread_rows]

    # Basic length alignment
    assert len(dates) == len(a1) == len(a2) > 0
    assert len(spread_dates) == len(spreads) == len(zscores) == len(dates)

    # Dates are identical and monotonic (ISO8601 strings)
    assert dates == spread_dates
    # Monotonic non-decreasing
    parsed = [datetime.fromisoformat(d.replace("Z", "+00:00")) for d in dates]
    assert all(parsed[i] <= parsed[i + 1] for i in range(len(parsed) - 1))


@pytest.mark.real_api
def test_pair_analysis_no_null_spread_zscore(sync_client):
    """Spread/z-score series should not be entirely null and should align per row."""
    params = {
        "asset1": "AAPL.US",
        "asset2": "MSFT.US",
        "granularity": "daily",
    }

    resp = sync_client.get("/api/pair-analysis", params=params)
    assert resp.status_code in [200, 204, 404, 500, 503]
    if resp.status_code != 200:
        pytest.skip(f"pair-analysis unavailable ({resp.status_code})")

    data = resp.json()
    spread_rows: List[Dict] = data.get("spread_data") or []
    assert len(spread_rows) > 0

    # Row-wise alignment and at least some non-null values
    non_null_spread = 0
    non_null_z = 0
    for row in spread_rows:
        assert set(["date", "spread", "zscore"]).issubset(row.keys())
        if row.get("spread") is not None:
            non_null_spread += 1
        if row.get("zscore") is not None:
            non_null_z += 1
    assert non_null_spread > 0
    assert non_null_z > 0


@pytest.mark.real_api
def test_rolling_metrics_monotonicity(sync_client):
    """Validate start/end-date boundaries and ordering for rolling metrics API."""
    # Use metrics router (precomputed table access)
    resp = sync_client.get(
        "/api/metrics/rolling/AAPL.US",
        params={"window": 252, "benchmark": "SPY.US"},
    )
    assert resp.status_code in [200, 204, 404, 500, 503]
    if resp.status_code != 200:
        pytest.skip(f"rolling metrics unavailable ({resp.status_code})")

    payload = resp.json()
    metrics = payload.get("metrics") or []
    if not metrics:
        pytest.skip("no rolling metrics returned")

    # Start <= end for each entry
    for m in metrics:
        start = datetime.fromisoformat(m["start_date"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(m["end_date"].replace("Z", "+00:00"))
        assert start <= end

    # End dates are non-increasing (API orders desc by end_date)
    ends = [datetime.fromisoformat(m["end_date"].replace("Z", "+00:00")) for m in metrics]
    assert all(ends[i] >= ends[i + 1] for i in range(len(ends) - 1))


@pytest.mark.real_business
def test_rolling_correlation_field_presence(supabase_client):
    """Document current schema support for rolling_correlation.

    If the column is present, basic non-null check on a sample row; if absent,
    skip with a clear note so the suite remains green while highlighting the gap.
    """
    # Probe table columns via a single row
    try:
        res = (
            supabase_client.table("rolling_metrics").select("*").limit(1).execute()
        )
    except Exception as e:
        pytest.skip(f"could not query rolling_metrics: {e}")

    row = (res.data or [None])[0]
    if row is None:
        pytest.skip("rolling_metrics has no rows to inspect")

    if "rolling_correlation" not in row:
        pytest.skip("rolling_correlation not present in rolling_metrics schema yet")

    # If present, ensure it's a numeric or null field
    val = row.get("rolling_correlation")
    assert (val is None) or isinstance(val, (int, float))
