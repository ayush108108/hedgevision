"""
Unit tests for CorrelationService and correlation calculation functions
Tests correlation matrix computation without database dependencies
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import Mock, MagicMock, patch

# Import service after path setup
import importlib
import sys
from pathlib import Path


def _get_correlation_module():
    """Dynamically import correlation_service module"""
    repo_root = Path(__file__).parent.parent
    backend_path = repo_root / "backend"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    return importlib.import_module("api.services.correlation_service")


@pytest.fixture
def correlation_module():
    """Get correlation service module"""
    return _get_correlation_module()


@pytest.fixture
def mock_supabase_client():
    """Create mock Supabase client"""
    client = Mock()
    client.store_correlation_matrix = Mock(return_value=True)
    return client


@pytest.fixture
def mock_data_manager():
    """Create mock DataManager"""
    manager = Mock()
    
    # Create sample price data
    dates = pd.date_range('2024-01-01', periods=100, freq='D', tz='UTC')
    
    # Stock A: trending up
    manager.get_daily_data = Mock(side_effect=lambda symbol, start_date, end_date: (
        pd.DataFrame({
            'Date': dates,
            'Close': np.linspace(100, 110, 100) + np.random.randn(100) * 0.5
        }) if symbol == "AAPL.US" else
        pd.DataFrame({
            'Date': dates,
            'Close': np.linspace(80, 88, 100) + np.random.randn(100) * 0.5
        }) if symbol == "MSFT.US" else
        pd.DataFrame()
    ))
    
    return manager


@pytest.fixture
def correlation_service(correlation_module, mock_supabase_client, mock_data_manager):
    """Create CorrelationService instance with mocked data fetching"""
    service_class = correlation_module.CorrelationService
    service = service_class(mock_supabase_client)
    service.data_manager = mock_data_manager

    # Patch module-level _fetch_price_data which is what compute_correlation_matrix actually uses
    dates = pd.date_range('2024-01-01', periods=100, freq='D', tz='UTC')

    def _mock_fetch(symbol, start_date, end_date, granularity="daily"):
        if symbol == "AAPL.US":
            return pd.DataFrame({
                'Date': dates,
                'Close': np.linspace(100, 110, 100) + np.random.randn(100) * 0.5
            })
        elif symbol == "MSFT.US":
            return pd.DataFrame({
                'Date': dates,
                'Close': np.linspace(80, 88, 100) + np.random.randn(100) * 0.5
            })
        return pd.DataFrame()

    # Store original and patch
    service._original_fetch = getattr(correlation_module, '_fetch_price_data', None)
    correlation_module._fetch_price_data = _mock_fetch

    yield service

    # Restore original
    if service._original_fetch is not None:
        correlation_module._fetch_price_data = service._original_fetch


@pytest.mark.unit
def test_get_sorted_correlation_matrix_sorts_by_average(correlation_module):
    """
    Test: get_sorted_correlation_matrix() sorts by average correlation
    Risk: Incorrect sorting makes heatmaps confusing and hard to interpret
    """
    # Create correlation matrix where B has highest avg correlation
    corr_df = pd.DataFrame({
        'A': [1.0, 0.3, 0.2],
        'B': [0.3, 1.0, 0.8],  # B has highest avg: (0.3 + 0.8) / 2 = 0.55
        'C': [0.2, 0.8, 1.0]
    }, index=['A', 'B', 'C'])
    
    sorted_df = correlation_module.get_sorted_correlation_matrix(corr_df)
    
    # B should be first (highest avg correlation)
    assert sorted_df.index[0] == 'B'
    assert sorted_df.columns[0] == 'B'
    
    # Matrix should remain symmetric
    assert (sorted_df == sorted_df.T).all().all()


@pytest.mark.unit
def test_get_sorted_correlation_matrix_handles_empty(correlation_module):
    """
    Test: get_sorted_correlation_matrix() handles empty DataFrame gracefully
    Risk: Empty data causes crashes in production
    """
    empty_df = pd.DataFrame()
    
    result = correlation_module.get_sorted_correlation_matrix(empty_df)
    
    assert result is not None
    assert result.empty


@pytest.mark.unit
def test_compute_correlation_matrix_pearson_method(correlation_service):
    """
    Test: compute_correlation_matrix() computes Pearson correlation correctly
    Risk: Wrong correlation method produces incorrect pair recommendations
    """
    asset_symbols = ["AAPL.US", "MSFT.US"]
    
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=asset_symbols,
        granularity="daily",
        method="pearson",
        lookback_days=252
    )
    
    # Should return correlation dictionary
    assert isinstance(result, dict)
    assert len(result) > 0
    
    # Should have entries for both assets
    assert "AAPL.US" in result
    assert "MSFT.US" in result
    
    # Self-correlation should be 1.0
    assert result["AAPL.US"]["AAPL.US"] == 1.0
    assert result["MSFT.US"]["MSFT.US"] == 1.0
    
    # Cross-correlation should exist and be between -1 and 1
    cross_corr = result["AAPL.US"]["MSFT.US"]
    assert -1.0 <= cross_corr <= 1.0


@pytest.mark.unit
def test_compute_correlation_matrix_spearman_method(correlation_service):
    """
    Test: compute_correlation_matrix() supports Spearman correlation
    Risk: Spearman (rank-based) correlation needed for non-linear relationships
    """
    asset_symbols = ["AAPL.US", "MSFT.US"]
    
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=asset_symbols,
        granularity="daily",
        method="spearman",
        lookback_days=252
    )
    
    # Should compute successfully
    assert isinstance(result, dict)
    assert len(result) > 0
    
    # Diagonal should still be 1.0
    assert result["AAPL.US"]["AAPL.US"] == 1.0


@pytest.mark.unit
def test_compute_correlation_matrix_insufficient_assets(correlation_service):
    """
    Test: compute_correlation_matrix() handles <2 assets gracefully
    Risk: Single asset correlation crashes or returns invalid data
    """
    # Only one asset
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US"],
        granularity="daily",
        method="pearson",
        lookback_days=252
    )
    
    # Should return empty dict (need at least 2 assets)
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.unit
def test_compute_correlation_matrix_invalid_granularity(correlation_service):
    """
    Test: compute_correlation_matrix() rejects invalid granularity
    Risk: Invalid granularity causes data fetch errors
    """
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US", "MSFT.US"],
        granularity="weekly",  # Invalid
        method="pearson",
        lookback_days=252
    )
    
    # Should return empty dict
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.unit
def test_compute_correlation_matrix_invalid_method(correlation_service):
    """
    Test: compute_correlation_matrix() rejects invalid correlation method
    Risk: Invalid methods produce meaningless results
    """
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US", "MSFT.US"],
        granularity="daily",
        method="kendall",  # Not supported
        lookback_days=252
    )
    
    # Should return empty dict
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.unit
def test_compute_correlation_matrix_stores_in_supabase(correlation_service, mock_supabase_client):
    """
    Test: compute_correlation_matrix() stores results in Supabase
    Risk: Precomputed correlations not persisted for fast retrieval
    """
    asset_symbols = ["AAPL.US", "MSFT.US"]
    
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=asset_symbols,
        granularity="daily",
        method="pearson",
        lookback_days=252
    )
    
    # Should call Supabase storage
    assert mock_supabase_client.store_correlation_matrix.called
    
    # Check the payload structure
    call_args = mock_supabase_client.store_correlation_matrix.call_args
    payload = call_args[0][0]
    
    assert "correlation_matrix" in payload
    assert "granularity" in payload
    assert "method" in payload
    assert payload["granularity"] == "daily"
    assert payload["method"] == "pearson"


@pytest.mark.unit
def test_compute_correlation_matrix_handles_nan_values(correlation_module, mock_supabase_client):
    """
    Test: compute_correlation_matrix() handles NaN values in price data
    Risk: Missing data causes correlation computation failures
    """
    # Mock data manager to return data with NaNs
    dates = pd.date_range('2024-01-01', periods=50, freq='D', tz='UTC')

    def get_data_with_nans(symbol, start_date, end_date, granularity="daily"):
        prices = np.linspace(100, 110, 50).copy()
        # Add some NaN values
        prices[10:15] = np.nan
        return pd.DataFrame({
            'Date': dates,
            'Close': prices
        })

    service_class = correlation_module.CorrelationService
    service = service_class(mock_supabase_client)

    original_fetch = correlation_module._fetch_price_data
    correlation_module._fetch_price_data = get_data_with_nans
    try:
        result = service.compute_correlation_matrix(
            asset_symbols=["AAPL.US", "MSFT.US"],
            granularity="daily",
            method="pearson",
            lookback_days=252
        )
    finally:
        correlation_module._fetch_price_data = original_fetch

    # Should handle NaNs gracefully (pandas.corr() drops them)
    assert isinstance(result, dict)


@pytest.mark.unit
def test_compute_correlation_matrix_zero_variance_handling(correlation_module, mock_supabase_client):
    """
    Test: compute_correlation_matrix() handles constant (zero variance) series
    Risk: Zero variance causes division by zero in correlation calculation
    """
    # Mock data with constant prices (zero variance)
    dates = pd.date_range('2024-01-01', periods=50, freq='D', tz='UTC')

    def get_constant_data(symbol, start_date, end_date, granularity="daily"):
        return pd.DataFrame({
            'Date': dates,
            'Close': np.full(50, 100.0)  # All same value
        })

    service_class = correlation_module.CorrelationService
    service = service_class(mock_supabase_client)

    original_fetch = correlation_module._fetch_price_data
    correlation_module._fetch_price_data = get_constant_data
    try:
        result = service.compute_correlation_matrix(
            asset_symbols=["AAPL.US", "MSFT.US"],
            granularity="daily",
            method="pearson",
            lookback_days=252
        )
    finally:
        correlation_module._fetch_price_data = original_fetch

    # Should handle gracefully (correlation undefined for constant series)
    assert isinstance(result, dict)
    # Result may be empty or have NaN correlations


@pytest.mark.unit
def test_compute_correlation_matrix_empty_asset_list(correlation_service):
    """
    Test: compute_correlation_matrix() handles empty asset list
    Risk: Empty input causes unexpected errors
    """
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=[],
        granularity="daily",
        method="pearson",
        lookback_days=252
    )
    
    # Should return empty dict
    assert isinstance(result, dict)
    assert len(result) == 0


@pytest.mark.unit
def test_compute_correlation_matrix_lookback_period_validation(correlation_service):
    """
    Test: compute_correlation_matrix() handles various lookback periods
    Risk: Edge cases in time windows cause data fetch issues
    """
    # Very short lookback
    result_short = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US", "MSFT.US"],
        granularity="daily",
        method="pearson",
        lookback_days=30
    )
    
    # Should work with short lookback
    assert isinstance(result_short, dict)
    
    # Very long lookback
    result_long = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US", "MSFT.US"],
        granularity="daily",
        method="pearson",
        lookback_days=1000
    )
    
    # Should work with long lookback
    assert isinstance(result_long, dict)


@pytest.mark.unit
def test_compute_correlation_matrix_symmetry(correlation_service):
    """
    Test: compute_correlation_matrix() produces symmetric correlation matrix
    Risk: Asymmetric matrix indicates computational error
    """
    result = correlation_service.compute_correlation_matrix(
        asset_symbols=["AAPL.US", "MSFT.US"],
        granularity="daily",
        method="pearson",
        lookback_days=252
    )
    
    if len(result) > 0:
        # corr(A, B) should equal corr(B, A)
        if "AAPL.US" in result and "MSFT.US" in result:
            corr_ab = result["AAPL.US"]["MSFT.US"]
            corr_ba = result["MSFT.US"]["AAPL.US"]
            
            assert abs(corr_ab - corr_ba) < 1e-10  # Should be identical


@pytest.mark.unit
def test_correlation_service_initialization(correlation_module, mock_supabase_client):
    """
    Test: CorrelationService initializes correctly with Supabase client
    Risk: Initialization errors prevent service usage
    """
    service_class = correlation_module.CorrelationService
    service = service_class(mock_supabase_client)
    
    assert service.supabase_client is mock_supabase_client
    assert service.logger is not None
    # data_manager may be None if DataManager import fails (acceptable)


@pytest.mark.unit
def test_correlation_service_no_data_available(correlation_module, mock_supabase_client):
    """
    Test: CorrelationService handles when no data is available from fetch
    Risk: Service crashes if data fetch fails
    """
    service_class = correlation_module.CorrelationService
    service = service_class(mock_supabase_client)
    
    # Mock _fetch_price_data to return empty DataFrames
    with patch('api.services.correlation_service._fetch_price_data', return_value=pd.DataFrame()):
        result = service.compute_correlation_matrix(
            asset_symbols=["AAPL.US", "MSFT.US"],
            granularity="daily",
            method="pearson",
            lookback_days=252
        )
    
    # Should return empty dict without crashing when no data available
    assert isinstance(result, dict)
    assert len(result) == 0
