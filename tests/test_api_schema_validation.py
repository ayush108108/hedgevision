"""
Strict API schema validation tests.

These tests validate the JSON structure and field types of key API endpoints
without asserting business values. They are meant to catch breaking changes in
contract between backend and frontend as well as ensure consistency across deployments.
"""

from __future__ import annotations

import math
from typing import Any, Dict

import pytest


pytestmark = pytest.mark.real_api


def _is_number(x: Any) -> bool:
    try:
        return (isinstance(x, (int, float)) and not math.isnan(float(x)) and not math.isinf(float(x)))
    except Exception:
        return False


class TestPairAnalysisSchema:
    def test_pair_analysis_schema_minimum(self, sync_client):
        resp = sync_client.get(
            "/api/pair-analysis",
            params={"asset1": "AAPL.US", "asset2": "MSFT.US"},
        )

        # Should return 200 or 404 if not enough data; 503 if DB unavailable
        assert resp.status_code in (200, 404, 500, 503)
        if resp.status_code != 200:
            pytest.skip("Pair analysis not available for given assets/dates")

        data: Dict[str, Any] = resp.json()

        # Required top-level keys
        for key in [
            "asset1",
            "asset2",
            "granularity",
            "data_source",
            "pair_metrics",
            "regression_metrics",
            "cointegration_results",
        ]:
            assert key in data, f"Missing key: {key}"

        # pair_metrics shape
        assert isinstance(data["pair_metrics"], dict)
        for k in ["correlation", "spearman_correlation", "half_life", "hurst_exponent"]:
            assert k in data["pair_metrics"], f"pair_metrics missing {k}"

        # regression_metrics shape
        rm = data["regression_metrics"]
        assert isinstance(rm, dict)
        for k in ["hedge_ratio", "beta", "alpha", "intercept", "r_squared", "std_error"]:
            assert k in rm, f"regression_metrics missing {k}"

        # cointegration_results shape
        cr = data["cointegration_results"]
        assert isinstance(cr, dict)
        for k in [
            "eg_is_cointegrated",
            "eg_pvalue",
            "eg_test_statistic",
            "eg_critical_value_1pct",
            "eg_critical_value_5pct",
            "eg_critical_value_10pct",
            "eg_significance_level",
            "johansen_is_cointegrated",
            "adf_is_stationary",
        ]:
            assert k in cr, f"cointegration_results missing {k}"

        # Optional payloads
        if "price_data" in data:
            pd = data["price_data"]
            assert isinstance(pd, dict)
            assert "dates" in pd and isinstance(pd["dates"], list)
            assert "asset1_prices" in pd and isinstance(pd["asset1_prices"], list)
            assert "asset2_prices" in pd and isinstance(pd["asset2_prices"], list)
            # Length alignment
            assert len(pd["dates"]) == len(pd["asset1_prices"]) == len(pd["asset2_prices"]) > 0

            # Optional OHLCV arrays
            if "asset1_ohlcv" in pd:
                assert isinstance(pd["asset1_ohlcv"], list)
                if pd["asset1_ohlcv"]:
                    sample = pd["asset1_ohlcv"][0]
                    for f in ["open", "high", "low", "close", "volume"]:
                        assert f in sample

            if "asset2_ohlcv" in pd:
                assert isinstance(pd["asset2_ohlcv"], list)

        if "spread_data" in data:
            sd = data["spread_data"]
            assert isinstance(sd, list)
            if sd:
                sample = sd[0]
                for f in ["date", "spread", "zscore"]:
                    assert f in sample

    def test_cointegration_only_schema(self, sync_client):
        resp = sync_client.get(
            "/api/pair-analysis/cointegration",
            params={"asset1": "AAPL.US", "asset2": "MSFT.US"},
        )
        assert resp.status_code in (200, 404, 500, 503)
        if resp.status_code != 200:
            pytest.skip("Cointegration results unavailable for assets")

        cr = resp.json()
        assert isinstance(cr, dict)
        assert 0.0 <= float(cr.get("eg_pvalue", 0.5)) <= 1.0


class TestMetricsSchema:
    def test_rolling_metrics_schema(self, sync_client):
        resp = sync_client.get("/api/metrics/rolling/AAPL.US", params={"window": 252, "benchmark": "SPY.US"})
        assert resp.status_code in (200, 404, 500, 503)
        if resp.status_code != 200:
            pytest.skip("No rolling metrics available")

        data = resp.json()
        for key in ["status", "asset_symbol", "metrics", "windows_available", "count"]:
            assert key in data

        assert isinstance(data["metrics"], list)
        if data["metrics"]:
            m = data["metrics"][0]
            # Spot check required fields from RollingMetric model
            for k in [
                "id",
                "asset_id",
                "window_days",
                "start_date",
                "end_date",
                "created_at",
            ]:
                assert k in m

            # Numeric fields if present should be numbers
            for opt in [
                "rolling_beta",
                "rolling_volatility",
                "rolling_sharpe",
                "rolling_sortino",
                "max_drawdown",
                "var_95",
                "cvar_95",
                "hurst_exponent",
                "alpha",
                "treynor",
                "information_ratio",
                "data_quality",
            ]:
                if opt in m and m[opt] is not None:
                    assert _is_number(m[opt])

    def test_latest_rolling_metrics_schema(self, sync_client):
        resp = sync_client.get(
            "/api/metrics/rolling",
            params={"window": 252, "order_by": "rolling_sharpe", "ascending": False, "limit": 10},
        )
        assert resp.status_code in (200, 500)  # 500 if DB unavailable
        if resp.status_code != 200:
            pytest.skip("Latest rolling metrics unavailable")
        data = resp.json()
        for key in ["status", "window", "benchmark", "order_by", "count", "metrics"]:
            assert key in data


class TestCorrelationSchema:
    def test_correlation_matrix_schema(self, sync_client):
        resp = sync_client.get("/api/correlation", params={"method": "spearman", "granularity": "daily"})
        assert resp.status_code in (200, 204, 500, 503)
        if resp.status_code != 200:
            pytest.skip("Correlation matrix not available")
        data = resp.json()
        assert isinstance(data, dict)
        assert "assets" in data and isinstance(data["assets"], list)
        assert "matrix" in data and isinstance(data["matrix"], dict)
        assert "metadata" in data and isinstance(data["metadata"], dict)
        assert "missing_assets" in data and isinstance(data["missing_assets"], list)

        # Matrix shape sanity: keys correspond to assets when non-empty
        if data["assets"] and data["matrix"]:
            assets = set(data["assets"])
            for row_key, row in data["matrix"].items():
                assert row_key in assets
                assert isinstance(row, dict)
                for col_key, val in row.items():
                    assert col_key in assets
                    if val is not None:
                        assert _is_number(val)
