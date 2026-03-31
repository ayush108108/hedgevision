"""
Real API Endpoint Tests for HedgeVision

Tests all API routes with real Supabase data.
NO MOCKS - All tests use real endpoints and real data.
"""

import pytest
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.real_api


class TestCorrelationEndpoints:
    """Test all correlation API endpoints."""

    def test_correlation_matrix_endpoint_with_dates(self, sync_client, test_date_range):
        """Test /api/correlation with date parameters."""
        response = sync_client.get(
            "/api/correlation",
            params={
                "start_date": test_date_range["start_date"].isoformat(),
                "end_date": test_date_range["end_date"].isoformat(),
                "method": "pearson",
            },
        )

        # Should return 200 or 204 if no data
        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info("✓ Correlation matrix returned")

    def test_correlation_matrix_with_symbols(self, sync_client, test_assets):
        """Test /api/correlation with specific date range."""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=60)

        response = sync_client.get(
            "/api/correlation",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code in [200, 204]
        logger.info("✓ Correlation matrix with date range returned")

    def test_correlation_top_pairs_endpoint(self, sync_client):
        """Test /api/screener/correlation/top-pairs endpoint."""
        response = sync_client.get(
            "/api/screener/correlation/top-pairs", params={"limit": 5, "min_correlation": 0.5}
        )

        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "pairs" in data:
                logger.info(f"✓ Found {len(data['pairs'])} top correlated pairs")
            elif isinstance(data, list):
                logger.info(f"✓ Found {len(data)} top correlated pairs")

    def test_correlation_cointegration_top_pairs(self, sync_client):
        """Test /api/screener/cointegration/top-pairs endpoint."""
        response = sync_client.get(
            "/api/screener/cointegration/top-pairs", params={"limit": 5}
        )

        assert response.status_code in [200, 204]
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "pairs" in data:
                logger.info(f"✓ Found {len(data['pairs'])} top cointegrated pairs")
            elif isinstance(data, list):
                logger.info(f"✓ Found {len(data)} top cointegrated pairs")
        logger.info("✓ Rolling correlation endpoint returned")

    def test_correlation_endpoint_invalid_symbols(self, sync_client):
        """Test correlation endpoint with invalid date format."""
        response = sync_client.get(
            "/api/correlation",
            params={
                "start_date": "invalid-date-format",
                "end_date": datetime.now().date().isoformat(),
            },
        )

        # Should return validation error (400 or 422)
        assert response.status_code in [400, 422]
        logger.info("✓ Invalid date format properly rejected")


class TestPairAnalysisEndpoints:
    """Test all pair analysis API endpoints."""

    def test_pair_analysis_cointegration_endpoint(self, sync_client, test_date_range):
        """Test /api/pair-analysis/cointegration endpoint."""
        response = sync_client.get(
            "/api/pair-analysis/cointegration",
            params={
                "asset1": "AAPL.US",
                "asset2": "MSFT.US",
                "start_date": test_date_range["start_date"].isoformat(),
                "end_date": test_date_range["end_date"].isoformat(),
            },
        )

        assert response.status_code in [200, 204, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info("✓ Cointegration analysis returned")

    def test_pair_analysis_spread_endpoint(self, sync_client, test_date_range):
        """Test /api/pair-analysis/spread endpoint."""
        response = sync_client.get(
            "/api/pair-analysis/spread",
            params={
                "asset1": "GOOGL.US",
                "asset2": "AMZN.US",
                "start_date": test_date_range["start_date"].isoformat(),
                "end_date": test_date_range["end_date"].isoformat(),
            },
        )

        assert response.status_code in [200, 204, 404]
        logger.info("✓ Spread analysis endpoint returned")

    def test_pair_analysis_rolling_beta_endpoint(self, sync_client, test_date_range):
        """Test /api/pair-analysis/rolling-beta endpoint (POST)."""
        payload = {
            "asset": "AAPL",
            "benchmark": "SPY",
            "window": 60,
            "start_date": test_date_range["start_date"].isoformat(),
            "end_date": test_date_range["end_date"].isoformat(),
        }

        response = sync_client.post("/api/pair-analysis/rolling-beta", json=payload)

        assert response.status_code in [200, 204, 404]
        logger.info("✓ Rolling beta endpoint returned")

    def test_pair_analysis_rolling_volatility_endpoint(
        self, sync_client, test_date_range
    ):
        """Test /api/pair-analysis/rolling-volatility endpoint (POST)."""
        payload = {
            "asset": "MSFT",
            "window": 30,
            "start_date": test_date_range["start_date"].isoformat(),
            "end_date": test_date_range["end_date"].isoformat(),
        }

        response = sync_client.post(
            "/api/pair-analysis/rolling-volatility", json=payload
        )

        assert response.status_code in [200, 204, 404]
        logger.info("✓ Rolling volatility endpoint returned")


class TestBacktestEndpoints:
    """Test all backtesting API endpoints."""

    def test_backtest_run_endpoint_minimal(self, sync_client, test_date_range):
        """Test /api/backtest/run with minimal config."""
        config = {
            "initial_capital": 100000,
            "strategy": "buy_and_hold",
            "symbol": "AAPL",
            "start_date": test_date_range["start_date"].isoformat(),
            "end_date": test_date_range["end_date"].isoformat(),
        }

        response = sync_client.post("/api/backtest/run", json=config)

        # Should return result or error
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Backtest returned: {list(data.keys())}")

    def test_backtest_run_endpoint_pair_trading(self, sync_client, test_date_range):
        """Test /api/backtest/run with pair trading strategy."""
        config = {
            "initial_capital": 100000,
            "strategy": "pair_trading",
            "long_symbol": "AAPL",
            "short_symbol": "MSFT",
            "start_date": test_date_range["start_date"].isoformat(),
            "end_date": test_date_range["end_date"].isoformat(),
        }

        response = sync_client.post("/api/backtest/run", json=config)

        assert response.status_code in [200, 400, 422]
        logger.info("✓ Pair trading backtest endpoint returned")

    def test_backtest_default_config_endpoint(self, sync_client):
        """Test /api/backtest/default-config endpoint."""
        response = sync_client.get("/api/backtest/default-config")

        assert response.status_code in [200, 404]  # Endpoint may not exist
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            logger.info(
                f"✓ Default backtest config returned with keys: {list(data.keys())}"
            )

    def test_backtest_invalid_config(self, sync_client):
        """Test backtest with invalid configuration."""
        config = {
            "initial_capital": -100,  # Invalid: negative capital
            "strategy": "invalid_strategy",
            "symbol": "AAPL",
        }

        response = sync_client.post("/api/backtest/run", json=config)

        # Should reject invalid config
        assert response.status_code in [400, 422]
        logger.info("✓ Invalid backtest config properly rejected")


class TestScreenerEndpoints:
    """Test all asset screener API endpoints."""

    def test_screener_status_endpoint(self, sync_client):
        """Test /api/screener/status endpoint."""
        response = sync_client.get("/api/screener/status")

        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            if "status" in data:
                logger.info(f"✓ Screener status: {data['status']}")

    def test_screener_top_pairs_endpoint(self, sync_client):
        """Test /api/screener/correlation/top-pairs endpoint with params."""
        response = sync_client.get(
            "/api/screener/correlation/top-pairs", params={"limit": 10, "min_correlation": 0.7}
        )

        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "pairs" in data:
                logger.info(f"✓ Found {len(data['pairs'])} top pairs")
            elif isinstance(data, list):
                logger.info(f"✓ Found {len(data)} top pairs")

    def test_screener_filter_by_correlation(self, sync_client):
        """Test screener with correlation filter."""
        response = sync_client.get(
            "/api/screener/correlation/top-pairs",
            params={"min_correlation": 0.8, "max_correlation": 0.95},
        )

        assert response.status_code in [200, 204]
        logger.info("✓ Screener filter by correlation returned")

    def test_screener_trigger_precomputation(self, sync_client):
        """Test triggering screener precomputation."""
        response = sync_client.post("/api/screener/trigger-precomputation")

        # May return 202 (accepted) or 200 (complete)
        assert response.status_code in [200, 202, 204]
        logger.info("✓ Screener precomputation triggered")


class TestCacheEndpoints:
    """Test cache management endpoints."""

    def test_cache_clear_endpoint(self, sync_client):
        """Test /api/cache/clear endpoint."""
        response = sync_client.post("/api/cache/clear")

        assert response.status_code in [200, 204]
        logger.info("✓ Cache cleared successfully")

    def test_cache_stats_endpoint(self, sync_client):
        """Test /api/cache/stats endpoint."""
        response = sync_client.get("/api/cache/stats")

        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Cache stats: {list(data.keys())}")

    def test_cache_health_endpoint(self, sync_client):
        """Test /api/cache/health endpoint."""
        response = sync_client.get("/api/cache/health")

        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            logger.info(f"✓ Cache health: {data['status']}")


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_missing_required_parameters(self, sync_client):
        """Test endpoints with missing required parameters."""
        # Missing required query parameters on cointegration endpoint
        response = sync_client.get("/api/pair-analysis/cointegration")

        # Should return 422 or 400 for missing params
        assert response.status_code in [400, 422]
        logger.info("✓ Missing parameters properly rejected")

    def test_invalid_date_format(self, sync_client):
        """Test endpoints with invalid date format."""
        response = sync_client.get(
            "/api/correlation",
            params={"start_date": "not-a-date", "end_date": "also-not-a-date"},
        )

        # Should return 400 or 422 for invalid dates
        assert response.status_code in [400, 422]
        logger.info("✓ Invalid date format properly rejected")

    def test_invalid_numeric_parameters(self, sync_client):
        """Test endpoints with invalid numeric parameters."""
        response = sync_client.get(
            "/api/screener/correlation/top-pairs",
            params={"limit": "not-a-number", "min_correlation": "also-not-a-number"},
        )

        # Should return 400 or 422
        assert response.status_code in [400, 422]
        logger.info("✓ Invalid numeric parameters properly rejected")


class TestResponseFormats:
    """Test response format and structure compliance."""

    def test_correlation_response_structure(self, sync_client, test_date_range):
        """Verify correlation response follows expected structure."""
        response = sync_client.get(
            "/api/correlation",
            params={
                "start_date": test_date_range["start_date"].isoformat(),
                "end_date": test_date_range["end_date"].isoformat(),
            },
        )

        if response.status_code == 200:
            data = response.json()

            # Verify it's a valid JSON response
            assert isinstance(data, (dict, list))

            # If dict, check for expected keys
            if isinstance(data, dict):
                # Should have data, metadata, or error keys
                assert any(
                    key in data
                    for key in [
                        "data",
                        "correlation_matrix",
                        "pairs",
                        "error",
                        "assets",
                        "matrix",
                    ]
                )

            logger.info("✓ Correlation response has valid structure")

    def test_backtest_response_structure(self, sync_client, test_date_range):
        """Verify backtest response follows expected structure."""
        config = {
            "initial_capital": 100000,
            "strategy": "buy_and_hold",
            "symbol": "AAPL",
            "start_date": test_date_range["start_date"].isoformat(),
            "end_date": test_date_range["end_date"].isoformat(),
        }

        response = sync_client.post("/api/backtest/run", json=config)

        if response.status_code == 200:
            data = response.json()

            # Verify structure
            assert isinstance(data, dict)

            # Should contain results or status
            assert any(key in data for key in ["results", "status", "data"])

            logger.info("✓ Backtest response has valid structure")


@pytest.mark.real_api
class TestAPIPerformance:
    """Test API performance with real data."""

    def test_health_endpoint_performance(self, sync_client):
        """Health endpoint should respond very quickly."""
        import time

        start = time.time()
        response = sync_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5, f"Health endpoint took {elapsed}s (should be < 0.5s)"
        logger.info(f"✓ Health endpoint responded in {elapsed:.3f}s")

    def test_top_pairs_endpoint_performance(self, sync_client):
        """Top pairs should respond within reasonable time."""
        import time

        start = time.time()
        response = sync_client.get("/api/screener/correlation/top-pairs", params={"limit": 10})
        elapsed = time.time() - start

        assert response.status_code in [200, 204]
        assert elapsed < 5.0, f"Top pairs took {elapsed}s (should be < 5s)"
        logger.info(f"✓ Top pairs endpoint responded in {elapsed:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
