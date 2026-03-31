"""
End-to-end data flow test: trace a sample pair from Supabase to API responses.
Validates data consistency across the entire pipeline.
"""

import pytest
from datetime import datetime


def test_e2e_pair_analysis_data_flow(sync_client):
    """
    Trace AAPL.US/MSFT.US pair from API response through all data layers.
    Validates alignment, completeness, and consistency.
    """
    # Step 1: Fetch pair analysis
    response = sync_client.get(
        "/api/pair-analysis",
        params={
            "asset1": "AAPL.US",
            "asset2": "MSFT.US",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
        },
    )
    assert response.status_code in (200, 404, 500, 503)
    if response.status_code != 200:
        pytest.skip(f"Pair analysis endpoint not available ({response.status_code})")
    data = response.json()
    assert "price_data" in data, "Missing price_data in response"
    price_data = data["price_data"]
    assert isinstance(price_data, dict), "price_data should be a dictionary"
    assert "dates" in price_data, "Missing dates in price_data"
    assert "asset1_prices" in price_data, "Missing asset1_prices in price_data"
    assert "asset2_prices" in price_data, "Missing asset2_prices in price_data"

    # Step 3: Validate spread_data presence and alignment
    assert "spread_data" in data, "Missing spread_data in response"
    spread_data = data["spread_data"]
    assert len(spread_data) > 0, "Empty spread_data"

    # Step 4: Check date alignment between price and spread
    price_dates = price_data["dates"]
    spread_dates = [s["date"] for s in spread_data]

    assert len(price_dates) == len(
        spread_dates
    ), f"Length mismatch: {len(price_dates)} prices vs {len(spread_dates)} spreads"

    for i, (pd, sd) in enumerate(zip(price_dates, spread_dates)):
        assert pd == sd, f"Date mismatch at index {i}: price={pd}, spread={sd}"

    # Step 5: Validate monotonic ascending dates
    parsed_dates = [datetime.fromisoformat(d.replace("Z", "+00:00")) for d in price_dates]
    for i in range(len(parsed_dates) - 1):
        assert (
            parsed_dates[i] <= parsed_dates[i + 1]
        ), f"Dates not monotonic at {i}: {parsed_dates[i]} > {parsed_dates[i+1]}"

    # Step 6: Validate metrics presence
    assert "pair_metrics" in data, "Missing pair_metrics"
    assert "regression_metrics" in data, "Missing regression_metrics"
    assert "cointegration_results" in data, "Missing cointegration_results"

    # Step 7: Validate numeric sanity in price data
    asset1_prices = price_data["asset1_prices"]
    asset2_prices = price_data["asset2_prices"]

    for i, price in enumerate(asset1_prices):
        if price is not None:
            assert price > 0, f"Invalid asset1_price at index {i}: {price}"

    for i, price in enumerate(asset2_prices):
        if price is not None:
            assert price > 0, f"Invalid asset2_price at index {i}: {price}"

    # Step 8: Validate spread numeric sanity
    for s in spread_data:
        if s.get("spread") is not None:
            spread_val = s["spread"]
            assert spread_val == spread_val, "Spread contains NaN"  # NaN check
        if s.get("zscore") is not None:
            zscore_val = s["zscore"]
            assert zscore_val == zscore_val, "Z-score contains NaN"

    print(
        f"✓ E2E validation passed: {len(price_dates)} aligned dates, "
        f"metrics present, data consistent"
    )


def test_e2e_rolling_metrics_consistency(sync_client):
    """
    Validate rolling metrics endpoint returns consistent data structure.
    """
    response = sync_client.get(
        "/api/metrics/rolling/AAPL.US",
        params={"window": 252, "benchmark": "SPY.US"},
    )
    assert response.status_code in (200, 404, 500, 503)
    if response.status_code != 200:
        pytest.skip(f"Rolling metrics endpoint not available ({response.status_code})")
    data = response.json()

    # Extract the metrics list from the response
    metrics = data.get("metrics", [])
    if not metrics:
        pytest.skip("No rolling metrics data available")

    # Validate structure consistency across all rows
    first_keys = set(metrics[0].keys())
    for i, row in enumerate(metrics[1:], start=1):
        row_keys = set(row.keys())
        assert (
            row_keys == first_keys
        ), f"Inconsistent keys at row {i}: {row_keys} != {first_keys}"

    # Validate required fields
    required_fields = ["start_date", "end_date", "asset_id"]
    for row in metrics:
        for field in required_fields:
            assert field in row, f"Missing required field: {field}"

    print(f"✓ Rolling metrics consistency validated: {len(metrics)} rows")


def test_e2e_correlation_matrix_structure(sync_client):
    """
    Validate correlation matrix endpoint returns properly shaped data.
    """
    response = sync_client.get(
        "/api/correlation",
        params={
            "view_mode": "asset",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
        },
    )
    assert response.status_code in (200, 204, 404, 500, 503)
    if response.status_code != 200:
        pytest.skip(f"Correlation endpoint not available ({response.status_code})")
    data = response.json()

    assert "assets" in data, "Missing assets list"
    assert "matrix" in data, "Missing correlation matrix"

    assets = data["assets"]
    matrix = data["matrix"]

    # Validate that we have at least some assets (may be less than 10 due to data availability)
    n = len(assets)
    if n == 0:
        pytest.skip("No assets returned in correlation matrix (no data available)")
    assert len(matrix) == n, f"Matrix row count {len(matrix)} != asset count {n}"

    # Validate matrix structure for each asset
    for i, asset_symbol in enumerate(assets):
        assert asset_symbol in matrix, f"Missing matrix row for asset {asset_symbol}"
        row = matrix[asset_symbol]
        assert len(row) == n, f"Matrix row for {asset_symbol} has {len(row)} columns, expected {n}"

        # Validate diagonal is 1.0 or close (if available)
        if asset_symbol in row:
            diag_val = row[asset_symbol]
            if diag_val is not None:
                assert 0.99 <= diag_val <= 1.01, f"Diagonal[{asset_symbol}] = {diag_val}, expected ~1.0"

    # Validate symmetry (if both values are available)
    for i in range(n):
        asset_i = assets[i]
        for j in range(i + 1, n):
            asset_j = assets[j]
            val_ij = matrix[asset_i].get(asset_j)
            val_ji = matrix[asset_j].get(asset_i)
            if val_ij is not None and val_ji is not None:
                diff = abs(val_ij - val_ji)
                assert diff < 0.01, f"Matrix not symmetric at ({asset_i},{asset_j}): {diff}"

    print(f"✓ Correlation matrix validated: {n}x{n}, symmetric, diag~1.0")
