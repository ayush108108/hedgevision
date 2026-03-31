"""
Test rolling metrics alignment and correctness.
Validates start_date <= end_date, descending order, and window span.
"""

import pytest
from datetime import datetime


@pytest.mark.parametrize(
    "symbol,window,benchmark",
    [
        ("AAPL.US", 252, "SPY.US"),
        ("MSFT.US", 180, "SPY.US"),
        ("GOOGL.US", 90, "SPY.US"),
    ],
)
def test_rolling_metrics_date_boundaries(sync_client, symbol, window, benchmark):
    """Test that start_date <= end_date for all rolling metrics rows."""
    response = sync_client.get(
        f"/api/metrics/rolling/{symbol}",
        params={"window": window, "benchmark": benchmark},
    )
    assert response.status_code == 200
    data = response.json()
    rows = data.get("metrics", []) if isinstance(data, dict) else data

    if not rows:
        pytest.skip(f"No rolling metrics data for {symbol} window={window}")

    for row in rows:
        start = datetime.fromisoformat(row["start_date"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(row["end_date"].replace("Z", "+00:00"))
        assert start <= end, f"start_date {start} > end_date {end} for {symbol}"


@pytest.mark.parametrize(
    "symbol,window,benchmark",
    [
        ("AAPL.US", 252, "SPY.US"),
        ("MSFT.US", 180, "SPY.US"),
        ("GOOGL.US", 90, "SPY.US"),
    ],
)
def test_rolling_metrics_descending_order(sync_client, symbol, window, benchmark):
    """Test that rolling metrics are returned in descending end_date order."""
    response = sync_client.get(
        f"/api/metrics/rolling/{symbol}",
        params={"window": window, "benchmark": benchmark},
    )
    assert response.status_code == 200
    data = response.json()
    rows = data.get("metrics", []) if isinstance(data, dict) else data

    if len(rows) < 2:
        pytest.skip(f"Insufficient data for order test: {symbol}")

    end_dates = [
        datetime.fromisoformat(row["end_date"].replace("Z", "+00:00"))
        for row in rows
    ]

    for i in range(len(end_dates) - 1):
        assert (
            end_dates[i] >= end_dates[i + 1]
        ), f"end_dates not descending at index {i}: {end_dates[i]} < {end_dates[i+1]}"


@pytest.mark.parametrize(
    "symbol,window,benchmark",
    [
        ("AAPL.US", 252, "SPY.US"),
        ("MSFT.US", 180, "SPY.US"),
        ("GOOGL.US", 90, "SPY.US"),
    ],
)
def test_rolling_metrics_window_span(sync_client, symbol, window, benchmark):
    """Test that each rolling window spans approximately 'window' days."""
    response = sync_client.get(
        f"/api/metrics/rolling/{symbol}",
        params={"window": window, "benchmark": benchmark},
    )
    assert response.status_code == 200
    data = response.json()
    rows = data.get("metrics", []) if isinstance(data, dict) else data

    if not rows:
        pytest.skip(f"No rolling metrics data for {symbol} window={window}")

    for row in rows:
        start = datetime.fromisoformat(row["start_date"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(row["end_date"].replace("Z", "+00:00"))
        span_days = (end - start).days

        # Allow some tolerance for weekends/holidays (actual trading days should be close to window)
        # Calendar span should be at least window-1 days
        assert (
            span_days >= window - 1
        ), f"Window span {span_days} < expected {window-1} for {symbol} ending {end}"


def test_rolling_metrics_numeric_sanity(sync_client):
    """Test that rolling metrics contain finite numeric values where present."""
    response = sync_client.get(
        "/api/metrics/rolling/AAPL.US",
        params={"window": 252, "benchmark": "SPY.US"},
    )
    assert response.status_code == 200
    data = response.json()
    rows = data.get("metrics", []) if isinstance(data, dict) else data

    if not rows:
        pytest.skip("No data for numeric sanity test")

    numeric_fields = [
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
        "beta",
        "max_drawdown",
    ]

    for row in rows:
        for field in numeric_fields:
            if field in row and row[field] is not None:
                val = row[field]
                assert isinstance(val, (int, float)), f"{field} is not numeric: {val}"
                assert not (val != val), f"{field} is NaN"  # NaN check
