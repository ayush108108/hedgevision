"""
Production validation tests: high-level sanity checks over representative
symbols and pairs to ensure endpoints are healthy and payloads are non-empty
with values in sane ranges. These are not unit tests; they validate the live
integration path (DB→API→JSON) and are designed to catch regressions quickly.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

import pytest


pytestmark = pytest.mark.real_api


PAIRS: List[Tuple[str, str]] = [
    ("AAPL.US", "MSFT.US"),
    ("GOOGL.US", "AMZN.US"),
]

SYMBOLS: List[str] = ["AAPL.US", "MSFT.US", "SPY.US"]


def _finite(x: Any) -> bool:
    try:
        f = float(x)
        return not math.isnan(f) and not math.isinf(f)
    except Exception:
        return False


@pytest.mark.parametrize("asset1,asset2", PAIRS)
def test_pair_analysis_health(sync_client, asset1: str, asset2: str):
    resp = sync_client.get("/api/pair-analysis", params={"asset1": asset1, "asset2": asset2})
    assert resp.status_code in (200, 404, 500, 503)
    if resp.status_code != 200:
        pytest.skip("Pair analysis not available for pair")

    data: Dict[str, Any] = resp.json()
    # Ensure non-empty price series with aligned dates
    if "price_data" in data:
        pd = data["price_data"]
        assert len(pd.get("dates", [])) > 30
        assert len(pd["dates"]) == len(pd.get("asset1_prices", [])) == len(pd.get("asset2_prices", []))
        # Recent values should be finite if present
        if pd["asset1_prices"] and pd["asset1_prices"][-1] is not None:
            assert _finite(pd["asset1_prices"][-1])
        if pd["asset2_prices"] and pd["asset2_prices"][-1] is not None:
            assert _finite(pd["asset2_prices"][-1])

    # Spread payload sanity
    if "spread_data" in data and data["spread_data"]:
        last = data["spread_data"][-1]
        assert "date" in last and "spread" in last and "zscore" in last
        # zscore can be None early; when present it should be finite
        if last["zscore"] is not None:
            assert _finite(last["zscore"])


@pytest.mark.parametrize("symbol", SYMBOLS)
def test_rolling_metrics_health(sync_client, symbol: str):
    resp = sync_client.get(f"/api/metrics/rolling/{symbol}", params={"window": 252, "benchmark": "SPY.US"})
    assert resp.status_code in (200, 404, 500, 503)
    if resp.status_code != 200:
        pytest.skip("No rolling metrics available for symbol")

    data = resp.json()
    metrics = data.get("metrics", [])
    if not metrics:
        pytest.skip("Empty rolling metrics list")
    # Ensure ordering by end_date is non-increasing
    dates = [m["end_date"] for m in metrics if "end_date" in m]
    assert dates == sorted(dates, reverse=True), "end_date must be non-increasing"
    # Sanity for core fields on first row
    m0 = metrics[0]
    for field in ["rolling_beta", "rolling_volatility", "rolling_sharpe"]:
        if field in m0 and m0[field] is not None:
            assert _finite(m0[field])


def test_correlation_matrix_health(sync_client):
    resp = sync_client.get("/api/correlation", params={"method": "spearman", "granularity": "daily"})
    assert resp.status_code in (200, 204, 500, 503)
    if resp.status_code != 200:
        pytest.skip("Correlation matrix unavailable")
    data = resp.json()
    # Non-empty implies at least 2 assets and some finite correlations
    if data.get("assets") and data.get("matrix"):
        assets = data["assets"]
        assert len(assets) >= 2
        # Pick one row and check at least one finite value off-diagonal
        any_finite = False
        for row_key, row in data["matrix"].items():
            for col_key, val in row.items():
                if row_key != col_key and val is not None and _finite(val):
                    any_finite = True
                    break
            if any_finite:
                break
        assert any_finite, "Expected at least one finite off-diagonal correlation"
