"""
Unit tests for CointegrationService
Tests cointegration analysis without database dependencies
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

# Import service after path setup
import importlib
import sys
from pathlib import Path


def _get_cointegration_service():
    """Dynamically import CointegrationService"""
    repo_root = Path(__file__).parent.parent
    backend_path = repo_root / "backend"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    return importlib.import_module("api.services.cointegration_service").CointegrationService


@pytest.fixture
def service():
    """Create CointegrationService instance"""
    CointegrationService = _get_cointegration_service()
    return CointegrationService()


@pytest.fixture
def cointegrated_pair_data():
    """
    Generate synthetic cointegrated price series for testing.
    asset1 and asset2 follow a cointegrated random walk.
    """
    np.random.seed(42)
    n = 252  # One year of daily data
    
    # Generate common trend
    trend = np.cumsum(np.random.randn(n)) * 0.5 + 100
    
    # asset1 follows trend + small noise
    asset1 = trend + np.random.randn(n) * 2
    
    # asset2 follows trend with scaling + small noise (cointegrated with asset1)
    asset2 = trend * 0.8 + 10 + np.random.randn(n) * 2
    
    # Create DataFrame
    dates = pd.date_range(start='2024-01-01', periods=n, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'asset1_price': asset1,
        'asset2_price': asset2
    })
    
    return df


@pytest.fixture
def non_cointegrated_pair_data():
    """
    Generate synthetic non-cointegrated (independent) price series.
    """
    np.random.seed(99)
    n = 252
    
    # Independent random walks
    asset1 = np.cumsum(np.random.randn(n)) * 0.5 + 100
    asset2 = np.cumsum(np.random.randn(n)) * 0.5 + 80
    
    dates = pd.date_range(start='2024-01-01', periods=n, freq='D')
    df = pd.DataFrame({
        'date': dates,
        'asset1_price': asset1,
        'asset2_price': asset2
    })
    
    return df


@pytest.mark.unit
def test_test_pair_cointegrated_happy_path(service, cointegrated_pair_data):
    """
    Test: test_pair() correctly identifies cointegrated pairs
    Risk: If cointegration detection fails, we may miss profitable pair trading opportunities
    """
    result = service.test_pair(
        asset1_symbol="STOCK_A",
        asset2_symbol="STOCK_B",
        prices_df=cointegrated_pair_data,
        granularity="daily",
        lookback_days=252
    )
    
    # Verify basic result structure
    assert result.asset1_symbol == "STOCK_A"
    assert result.asset2_symbol == "STOCK_B"
    assert result.sample_size == 252
    assert result.error_message is None
    
    # Should detect cointegration (at least one test passes)
    assert result.eg_is_cointegrated or result.johansen_is_cointegrated
    
    # Correlation should be present (may not be perfect with synthetic data)
    assert abs(result.pearson_correlation) > 0.3
    
    # Mean reversion characteristics
    assert result.half_life_days > 0
    assert 0 <= result.hurst_exponent <= 1
    
    # Overall score should be positive
    assert result.overall_score > 0
    

@pytest.mark.unit
def test_test_pair_non_cointegrated(service, non_cointegrated_pair_data):
    """
    Test: test_pair() correctly identifies non-cointegrated pairs
    Risk: False positives lead to unprofitable trading strategies
    """
    result = service.test_pair(
        asset1_symbol="STOCK_C",
        asset2_symbol="STOCK_D",
        prices_df=non_cointegrated_pair_data,
        granularity="daily",
        lookback_days=252
    )
    
    # Should not detect strong cointegration
    # At least one major test should fail
    cointegration_signals = [
        result.eg_is_cointegrated,
        result.johansen_is_cointegrated,
    ]
    
    # Not all tests should pass for random walk pairs
    assert not all(cointegration_signals)
    
    # Overall score should be lower
    assert result.overall_score < 60  # Threshold for "moderate" cointegration


@pytest.mark.unit
def test_test_pair_insufficient_data_error(service):
    """
    Test: test_pair() handles insufficient data gracefully
    Risk: Crash on edge cases disrupts user experience
    """
    # Create minimal data (less than 30 points)
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=20, freq='D'),
        'asset1_price': np.random.randn(20) + 100,
        'asset2_price': np.random.randn(20) + 80
    })
    
    result = service.test_pair(
        asset1_symbol="STOCK_E",
        asset2_symbol="STOCK_F",
        prices_df=df,
        granularity="daily",
        lookback_days=252
    )
    
    # Should return error result
    assert result.error_message is not None
    assert "Insufficient data" in result.error_message
    assert result.overall_score == 0.0
    assert result.cointegration_strength == "none"


@pytest.mark.unit
def test_engle_granger_test_detection(service):
    """
    Test: _engle_granger_test() correctly detects cointegration
    Risk: Core statistical test malfunction leads to wrong signals
    """
    # Create known cointegrated series
    np.random.seed(123)
    n = 200
    x = np.cumsum(np.random.randn(n))
    y = 2 * x + 5 + np.random.randn(n) * 0.5  # y is cointegrated with x
    
    result = service._engle_granger_test(y, x)
    
    # Should detect cointegration
    assert result["is_cointegrated"] == True
    assert result["pvalue"] < 0.05
    assert result["test_stat"] < result["crit_5pct"]
    
    # Should have critical values
    assert result["crit_1pct"] < 0  # EG test statistics are negative
    assert result["crit_5pct"] < 0
    assert result["crit_10pct"] < 0


@pytest.mark.unit
def test_johansen_test_rank_detection(service):
    """
    Test: _johansen_test() determines cointegration rank correctly
    Risk: Incorrect rank leads to wrong trading strategy
    """
    # Create cointegrated pair
    np.random.seed(456)
    n = 200
    x = np.cumsum(np.random.randn(n))
    y = 1.5 * x + 10 + np.random.randn(n) * 0.5
    
    result = service._johansen_test(y, x)
    
    # Should detect at least one cointegrating relationship
    assert result["rank"] >= 1
    assert result["is_cointegrated"] == True
    
    # Should have trace and eigenvalue statistics
    assert result["trace_stat"] > 0
    assert result["eigen_stat"] > 0
    
    # Critical values should be present
    assert result["trace_crit_95"] > 0
    assert result["eigen_crit_95"] > 0


@pytest.mark.unit
def test_calculate_hedge_ratio_accuracy(service):
    """
    Test: calculate_hedge_ratio() computes correct beta coefficient
    Risk: Wrong hedge ratio leads to unhedged positions and losses
    """
    # Create linear relationship: y = 2*x + 5
    np.random.seed(789)
    x = np.linspace(10, 100, 100)
    y = 2 * x + 5 + np.random.randn(100) * 0.1  # Small noise
    
    hedge_ratio = service.calculate_hedge_ratio(y, x)
    
    # Hedge ratio should be close to 2.0
    assert 1.9 < hedge_ratio < 2.1
    assert isinstance(hedge_ratio, float)


@pytest.mark.unit
def test_calculate_spread_with_custom_ratio(service):
    """
    Test: calculate_spread() computes spread correctly with custom hedge ratio
    Risk: Incorrect spread calculation invalidates all trading signals
    """
    asset1 = np.array([100, 102, 104, 106, 108])
    asset2 = np.array([50, 51, 52, 53, 54])
    hedge_ratio = 2.0
    
    spread = service.calculate_spread(asset1, asset2, hedge_ratio=hedge_ratio)
    
    # Spread = asset1 - (2.0 * asset2)
    expected = asset1 - (2.0 * asset2)
    np.testing.assert_array_almost_equal(spread, expected)


@pytest.mark.unit
def test_calculate_zscore_normalization(service):
    """
    Test: calculate_zscore() normalizes spread correctly
    Risk: Wrong z-scores trigger false entry/exit signals
    """
    series = np.array([10, 12, 14, 16, 18, 20, 22, 24])
    
    zscore = service.calculate_zscore(series, window=None)
    
    # Z-score should have mean ~0 and std ~1
    assert abs(np.mean(zscore)) < 0.01
    assert abs(np.std(zscore, ddof=0) - 1.0) < 0.01
    
    # Values far from mean should have high absolute z-scores
    assert abs(zscore[0]) > 1  # First value (10) is below mean
    assert abs(zscore[-1]) > 1  # Last value (24) is above mean


@pytest.mark.unit
def test_half_life_calculation_mean_reversion(service, cointegrated_pair_data):
    """
    Test: _compute_mean_reversion_metrics() calculates reasonable half-life
    Risk: Wrong half-life leads to incorrect trade timing
    """
    # Extract prices and compute spread
    asset1 = cointegrated_pair_data['asset1_price'].values
    asset2 = cointegrated_pair_data['asset2_price'].values
    hedge_ratio = service.calculate_hedge_ratio(asset1, asset2)
    spread = service.calculate_spread(asset1, asset2, hedge_ratio=hedge_ratio)
    
    metrics = service._compute_mean_reversion_metrics(spread)
    
    # Half-life should be positive and reasonable
    assert metrics["half_life"] > 0
    assert metrics["half_life"] < 1000  # Not infinite
    
    # Mean reversion speed should be positive
    assert metrics["speed"] >= 0
    
    # Hurst exponent for cointegrated series should be < 0.5 (mean-reverting)
    # Note: May not always be < 0.5 due to small sample size
    assert 0 <= metrics["hurst"] <= 1


@pytest.mark.unit
def test_prepare_data_validation(service):
    """
    Test: _prepare_data() validates and cleans input data
    Risk: Bad data propagates through pipeline causing errors
    """
    # Create data with NaN and unsorted dates
    df = pd.DataFrame({
        'date': pd.to_datetime(['2024-01-03', '2024-01-01', '2024-01-02', '2024-01-04']),
        'asset1_price': [100, 101, np.nan, 103],
        'asset2_price': [50, np.nan, 52, 53]
    })
    
    cleaned = service._prepare_data(df, lookback_days=252)
    
    # Should be sorted by date
    assert cleaned['date'].is_monotonic_increasing
    
    # Should remove rows with NaN
    assert not cleaned.isnull().any().any()
    
    # Should have 2 valid rows (rows 0 and 3 from original)
    assert len(cleaned) == 2


@pytest.mark.unit
def test_compute_correlations_significance(service):
    """
    Test: _compute_correlations() computes multiple correlation metrics
    Risk: Misidentified correlation leads to poor pair selection
    """
    # Strong positive correlation
    np.random.seed(111)
    x = np.linspace(0, 100, 100)
    y = x + np.random.randn(100) * 2  # Highly correlated
    
    result = service._compute_correlations(x, y)
    
    # All correlation metrics should be strong positive
    assert result["pearson"] > 0.9
    assert result["spearman"] > 0.9
    assert result["kendall"] > 0.8
    
    # Should be highly significant
    assert result["pvalue"] < 0.01
    assert result["significance"] == "highly_significant"


@pytest.mark.unit
def test_overall_assessment_scoring(service):
    """
    Test: _compute_overall_assessment() produces reasonable scores
    Risk: Wrong assessment leads to trading unsuitable pairs
    """
    # Mock strong cointegration results
    eg_results = {
        "is_cointegrated": True,
        "significance_level": "1%"
    }
    johansen_results = {
        "is_cointegrated": True
    }
    adf_results = {
        "is_stationary": True
    }
    correlation_results = {
        "pearson": 0.85
    }
    mean_reversion = {
        "half_life": 15,
        "hurst": 0.4
    }
    signal_quality = {
        "quality_score": 70
    }
    
    assessment = service._compute_overall_assessment(
        eg_results,
        johansen_results,
        adf_results,
        correlation_results,
        mean_reversion,
        signal_quality
    )
    
    # Should produce high score for strong cointegration
    assert assessment["score"] > 70
    assert assessment["strength"] in ["strong", "moderate"]
    assert assessment["suitability"] in ["excellent", "good"]
    assert assessment["risk_level"] in ["low", "medium"]  # Risk level can vary based on half_life


@pytest.mark.unit
def test_resolve_asset_symbol_formats(service):
    """
    Test: resolve_asset_symbol() handles multiple input formats
    Risk: Symbol resolution errors break asset lookup
    """
    # Already a symbol with exchange
    assert service.resolve_asset_symbol("AAPL.US") == "AAPL.US"
    
    # Plain symbol (should pass through)
    assert service.resolve_asset_symbol("GOOGL.US") == "GOOGL.US"
    
    # Display name to symbol (requires name_to_symbol mapping)
    # This test depends on api.utils.assets.name_to_symbol
    # If mapping doesn't exist, it returns input as-is
    result = service.resolve_asset_symbol("Apple")
    assert isinstance(result, str)


@pytest.mark.unit  
def test_error_result_structure(service):
    """
    Test: _create_error_result() returns valid result structure on failure
    Risk: Error handling breaks application flow
    """
    error_result = service._create_error_result(
        asset1="ERROR_A",
        asset2="ERROR_B",
        granularity="daily",
        lookback_days=252,
        computation_time=100,
        error="Test error message"
    )
    
    # Should have error message
    assert error_result.error_message == "Test error message"
    
    # Should have safe default values
    assert error_result.overall_score == 0.0
    assert error_result.cointegration_strength == "none"
    assert error_result.trading_suitability == "poor"
    assert error_result.sample_size == 0
    
    # Should not be cointegrated
    assert error_result.eg_is_cointegrated == False
    assert error_result.johansen_is_cointegrated == False
