import types

import numpy as np
import pandas as pd
import pytest
import importlib
import sys
from pathlib import Path


def _ensure_backend_on_path():
    repo_root = Path(__file__).parent.parent
    backend_path = repo_root / "backend"
    # Make both 'backend.*' and 'api.*' importable
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))


def _get_analytics_module():
    _ensure_backend_on_path()
    return importlib.import_module("api.services.analytics_service")


@pytest.mark.unit
def test_extract_pairs_from_matrix_sorts_and_dedupes():
    """
    Test _extract_pairs_from_matrix returns unique pairs sorted by abs correlation.
    Risk: If duplicate A-B/B-A pairs or wrong sort order slip through, the screener UI
    may show inconsistent results and mislead users into picking suboptimal pairs.
    """
    AnalyticsService = _get_analytics_module().AnalyticsService
    svc = AnalyticsService()

    matrix = {
        "A": {"A": 1.0, "B": 0.8, "C": -0.6},
        "B": {"A": 0.8, "B": 1.0, "C": 0.3},
        "C": {"A": -0.6, "B": 0.3, "C": 1.0},
    }

    pairs = svc._extract_pairs_from_matrix(matrix, min_correlation=0.4, limit=10)

    # Unique expected pairs: (A,B) with 0.8, (A,C) with -0.6 (abs 0.6), (B,C) 0.3 filtered out by threshold
    assert len(pairs) == 2
    # Sorted by abs corr desc
    assert pairs[0]["abs_correlation"] >= pairs[1]["abs_correlation"]
    # Deduped (no B-A if A-B present)
    seen = {tuple(sorted((p["asset1"], p["asset2"])) ) for p in pairs}
    assert len(seen) == len(pairs)


@pytest.mark.unit
def test_compute_pairs_on_fly_uses_injected_correlation(monkeypatch):
    """
    Test _compute_pairs_on_fly with a monkeypatched correlation matrix to avoid external deps.
    Risk: If dynamic computation path breaks, the app can't fallback when precompute is missing,
    leading to empty screener results in production.
    """
    AnalyticsService = _get_analytics_module().AnalyticsService
    svc = AnalyticsService()

    # Monkeypatch module-level imported function inside analytics_service
    # to return a small deterministic correlation DataFrame
    analytics_mod = _get_analytics_module()

    corr_df = pd.DataFrame(
        data=[[1.0, 0.75, -0.2], [0.75, 1.0, 0.55], [-0.2, 0.55, 1.0]],
        index=["X", "Y", "Z"],
        columns=["X", "Y", "Z"],
    )
    monkeypatch.setattr(analytics_mod, "get_correlation_data", lambda *args, **kwargs: corr_df)

    result = svc._compute_pairs_on_fly(
        min_correlation=0.5, limit=5, granularity="daily", method="spearman"
    )

    assert result["cache_status"] in ("dynamic", "dynamic_error")
    assert result["granularity"] == "daily"
    assert result["method"] == "spearman"
    # Pairs: (X,Y)=0.75, (Y,Z)=0.55 pass threshold; (X,Z)=0.2 filtered
    pairs = result["pairs"]
    assert len(pairs) == 2
    assert {tuple(sorted((p["asset1"], p["asset2"])) ) for p in pairs} == {("X", "Y"), ("Y", "Z")}


@pytest.mark.unit
def test_format_cointegration_report_happy_path(monkeypatch):
    """
    Test _format_cointegration_report builds complete payload including price and spread data.
    Risk: If report formatting is wrong, the front-end charts and KPIs will be incorrect,
    potentially causing users to trade on wrong metrics.
    """
    AnalyticsService = _get_analytics_module().AnalyticsService
    svc = AnalyticsService()

    # Fake cointegration test result object with necessary attributes
    test_result = types.SimpleNamespace(
        granularity="daily",
        pearson_correlation=0.85,
        spearman_correlation=0.82,
        half_life_days=12.3,
        hurst_exponent=0.42,
        beta_coefficient=1.5,
        alpha_intercept=0.01,
        regression_r_squared=0.92,
        regression_std_error=0.05,
        eg_is_cointegrated=True,
        eg_pvalue=0.01,
        eg_test_statistic=-3.1,
        eg_critical_value_1pct=-3.5,
        eg_critical_value_5pct=-2.9,
        eg_critical_value_10pct=-2.6,
        eg_significance_level=0.05,
        johansen_is_cointegrated=True,
        adf_is_stationary=True,
        overall_score=0.9,
    )

    # Provide small deterministic price data
    prices_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "asset1_price": [10.0, 10.5, 11.0],
            "asset2_price": [6.0, 6.2, 6.4],
        }
    )

    # Stub cointegration_service methods used by _format_cointegration_report
    class StubCoint:
        @staticmethod
        def calculate_spread(asset1_prices, asset2_prices, hedge_ratio):
            # y - beta*x
            return np.array(asset1_prices) - hedge_ratio * np.array(asset2_prices)

        @staticmethod
        def calculate_zscore(spread, window=None):
            # simple zscore for deterministic output
            s = np.array(spread, dtype=float)
            return (s - s.mean()) / (s.std(ddof=0) + 1e-9)

    monkeypatch.setattr(svc, "cointegration_service", StubCoint(), raising=False)

    report = svc._format_cointegration_report(
        test_result=test_result,
        prices_df=prices_df,
        asset1="AAA",
        asset2="BBB",
        include_price_data=True,
        include_spread_data=True,
    )

    # Validate key structure
    assert report["asset1"] == "AAA" and report["asset2"] == "BBB"
    assert report["granularity"] == "daily"
    assert "pair_metrics" in report and "regression_metrics" in report
    assert report["cointegration_results"]["eg_is_cointegrated"] is True

    # Validate time series payload lengths align with input rows
    assert len(report["price_data"]["dates"]) == 3
    assert len(report["spread_data"]) == 3


@pytest.mark.unit
def test_get_screener_top_pairs_falls_back_to_dynamic(monkeypatch):
    """
    Test get_screener_top_pairs falls back to dynamic compute when no precomputed matrix.
    We stub supabase_client.get_correlation_matrix to return None and inject a small corr df.
    """
    AnalyticsService = _get_analytics_module().AnalyticsService
    svc = AnalyticsService()

    # Stub supabase client to force fallback
    class StubSupabase:
        def get_correlation_matrix(self, *args, **kwargs):
            return None

    monkeypatch.setattr(svc, "supabase_client", StubSupabase(), raising=False)

    # Inject correlation data for dynamic path
    analytics_mod = _get_analytics_module()
    corr_df = pd.DataFrame(
        data=[[1.0, 0.9], [0.9, 1.0]], index=["P", "Q"], columns=["P", "Q"]
    )
    monkeypatch.setattr(analytics_mod, "get_correlation_data", lambda *a, **k: corr_df)

    out = svc.get_screener_top_pairs(min_correlation=0.5, limit=5, granularity="daily", method="pearson")
    assert out["total_pairs"] == 1
    assert out["pairs"][0]["asset1_symbol"] in ("P", "Q")
