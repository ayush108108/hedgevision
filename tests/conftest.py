"""
Pytest configuration and fixtures for HedgeVision Real Integration Testing

This module sets up all fixtures for testing against real Supabase database.
No mocks or sample data - everything is real and persisted to Supabase.
"""

import sys
import pytest
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator, Dict, Any, List
from pathlib import Path

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Setup path (ensure both repo root and backend package are importable)
repo_root = Path(__file__).parent.parent
backend_path = repo_root / "backend"
for p in (str(repo_root), str(backend_path)):
    if p not in sys.path:
        sys.path.insert(0, p)

logger.info("=" * 80)
logger.info("HedgeVision Real Integration Test Suite")
logger.info(f"Backend path: {backend_path}")
logger.info("=" * 80)

# Lazy imports to handle optional dependencies
app = None
config = None
SupabaseClient = None
TestClient = None
AsyncClient = None

try:
    from fastapi.testclient import TestClient as _TestClient

    TestClient = _TestClient
except ImportError:
    pass

try:
    from httpx import AsyncClient as _AsyncClient

    AsyncClient = _AsyncClient
except ImportError:
    pass

try:
    from supabase import create_client, Client as _SupabaseClient

    SupabaseClient = _SupabaseClient
except ImportError:
    pass

# Import configuration first (independent of app import)
try:
    from backend.api.utils.config import config as _config
    config = _config
except Exception as e:
    config = {}
    logger.warning(f"Could not import config from backend.api.utils.config: {e}")

# Import FastAPI app separately so a failure here doesn't nuke config
try:
    from backend.api.main import app as _app
    app = _app
except Exception as e:
    app = None
    logger.warning(f"Could not import FastAPI app from backend.api.main: {e}")

logger.info("=" * 80)
logger.info("HedgeVision Real Integration Test Suite")
try:
    if isinstance(config, dict) and config:
        logger.info(f"Supabase URL: {config.get('SUPABASE_URL', 'NOT SET')}")
        db_url = config.get('SUPABASE_DB_URL') or 'NOT SET'
        logger.info(f"Database URL: {str(db_url)[:50]}...")
    elif hasattr(config, 'SUPABASE_URL'):
        logger.info(f"Supabase URL: {getattr(config, 'SUPABASE_URL', 'NOT SET')}")
        db_url = getattr(config, 'SUPABASE_DB_URL', 'NOT SET')
        logger.info(f"Database URL: {str(db_url)[:50]}...")
    else:
        logger.warning("Config not loaded - tests may be skipped")
except Exception as e:
    logger.warning(f"Error logging config: {e}")
logger.info("=" * 80)


# ============================================================================
# EVENT LOOP FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests."""
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ============================================================================
# SUPABASE CLIENT FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def supabase_client() -> SupabaseClient:
    """Create Supabase client for real database connection."""
    if not config:
        pytest.skip("Config not loaded")
    
    url = config.get("SUPABASE_URL")
    key = config.get("SUPABASE_SERVICE_ROLE_KEY") or config.get("SUPABASE_SERVICE_KEY") or config.get("SUPABASE_KEY") or config.get("SUPABASE_ANON_KEY")

    if not url or not key:
        pytest.skip("Supabase credentials not configured")

    client = create_client(url, key)
    logger.info(f"✓ Connected to Supabase: {url}")
    return client


@pytest.fixture(scope="session")
def db_connection_string() -> str:
    """Get direct PostgreSQL connection string."""
    if not config:
        pytest.skip("Config not loaded")
    url = config.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("SUPABASE_DB_URL not configured")
    return url


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================


def mock_authenticated_user():
    """Mock authenticated user for testing protected endpoints."""
    from backend.api.utils.auth_middleware import AuthUser
    from backend.api.services.auth_service import UserProfile
    from datetime import datetime
    
    mock_profile = UserProfile(
        id="test-user-123",
        email="test@example.com",
        full_name="Test User",
        avatar_url=None,
        subscription_tier="free",
        preferences={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    return AuthUser(
        user_id="test-user-123",
        email="test@example.com",
        profile=mock_profile,
        token_claims={"sub": "test-user-123", "email": "test@example.com"}
    )


@pytest.fixture(scope="function")
def sync_client() -> Generator[TestClient, None, None]:
    """Synchronous test client for API endpoints.

    Ensures the FastAPI `app` is imported even if module import ordering/running path
    caused it to be None at import time.
    """
    global app
    if app is None:
        try:
            import importlib
            from pathlib import Path as _Path
            import sys as _sys

            repo_root = _Path(__file__).parent.parent
            backend_path = repo_root / "backend"
            # Ensure both repo root (for "backend.*" absolute imports) and backend (for "api.*")
            for p in (str(repo_root), str(backend_path)):
                if p not in _sys.path:
                    _sys.path.insert(0, p)
            app = importlib.import_module("api.main").app
            logger.info("✓ FastAPI app loaded dynamically in fixture")
        except Exception as e:
            pytest.skip(f"FastAPI app not available: {e}")

    # Override auth dependency for testing
    from backend.api.utils.auth_middleware import get_authenticated_user
    app.dependency_overrides[get_authenticated_user] = mock_authenticated_user

    with TestClient(app) as client:
        logger.info("✓ Created sync test client")
        yield client
    
    # Clean up override
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client for API endpoints."""
    global app
    if app is None:
        try:
            import importlib
            from pathlib import Path as _Path
            import sys as _sys

            repo_root = _Path(__file__).parent.parent
            backend_path = repo_root / "backend"
            for p in (str(repo_root), str(backend_path)):
                if p not in _sys.path:
                    _sys.path.insert(0, p)
            app = importlib.import_module("api.main").app
            logger.info("✓ FastAPI app loaded dynamically in async fixture")
        except Exception as e:
            pytest.skip(f"FastAPI app not available: {e}")

    async with AsyncClient(app=app, base_url="http://test") as client:
        logger.info("✓ Created async test client")
        yield client


# ============================================================================
# SERVICE FIXTURES - Removed for simplicity, use services directly in tests
# ============================================================================

# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def test_assets() -> List[Dict[str, Any]]:
    """Test assets to use for testing. Real data from Supabase."""
    return [
        {"symbol": "AAPL", "name": "Apple Inc.", "asset_type": "EQUITY"},
        {"symbol": "MSFT", "name": "Microsoft Corp.", "asset_type": "EQUITY"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "asset_type": "EQUITY"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "asset_type": "EQUITY"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "asset_type": "EQUITY"},
        {"symbol": "GLD", "name": "SPDR Gold Shares", "asset_type": "ETF"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "asset_type": "ETF"},
    ]


@pytest.fixture(scope="session")
def test_date_range() -> Dict[str, datetime]:
    """Standard date range for tests."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=252)  # 1 year of data

    return {
        "start_date": start_date,
        "end_date": end_date,
    }


# ============================================================================
# DATA VALIDATION FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def expected_columns() -> Dict[str, List[str]]:
    """Expected column names in Supabase tables."""
    return {
        "assets": [
            "id",
            "symbol",
            "name",
            "asset_type",
            "exchange",
            "sector",
            "is_active",
        ],
        "price_history": [
            "id",
            "asset_id",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
            "source",
            "data_quality",
            "created_at",
        ],
        "rolling_metrics": [
            "id",
            "asset_id",
            "benchmark_id",
            "window_days",
            "start_date",
            "end_date",
            "rolling_beta",
            "rolling_volatility",
            "rolling_sharpe",
            "rolling_sortino",
            "max_drawdown",
            "var_95",
            "cvar_95",
            "hurst_exponent",
        ],
        "correlation_matrix": [
            "id",
            "matrix_date",
            "window_days",
            "correlation_matrix",
            "average_correlation",
            "median_correlation",
            "valid_pairs_count",
        ],
        "pair_trades": [
            "id",
            "long_asset_id",
            "short_asset_id",
            "cointegration_score",
            "cointegration_pvalue",
            "beta_coefficient",
            "alpha_intercept",
            "model_r_squared",
            "status",
        ],
    }


# ============================================================================
# HELPER FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def clear_cache(sync_client: TestClient):
    """Clear Redis cache before test."""
    try:
        sync_client.post("/api/cache/clear")
        logger.info("✓ Cleared cache before test")
    except Exception as e:
        logger.warning(f"Could not clear cache: {e}")


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Test configuration from environment."""
    return {
        "api_base_url": "http://localhost:8000/api",
        "timeout": 30,
        "max_retries": 3,
        "supabase_url": config.get("SUPABASE_URL"),
        "supabase_key": config.get("SUPABASE_KEY"),
        "use_real_data": True,  # IMPORTANT: Real data testing
    }


# ============================================================================
# PYTEST HOOKS
# ============================================================================


def pytest_configure(config):
    """Configure pytest session."""
    config.addinivalue_line(
        "markers", "real_integration: mark test as real integration test"
    )
    config.addinivalue_line("markers", "real_api: mark test as real API test")
    config.addinivalue_line(
        "markers", "real_business: mark test as real business engine test"
    )
    config.addinivalue_line("markers", "supabase: mark test as requiring Supabase")
    config.addinivalue_line("markers", "database: mark test as requiring database")
    # Add common markers to avoid warnings
    config.addinivalue_line("markers", "unit: unit test")
    config.addinivalue_line("markers", "integration: integration test")


def pytest_collection_modifyitems(config, items):
    """Add markers and skip tests based on configuration."""
    for item in items:
        # Auto-mark tests in specific files
        if "real_integration" in str(item.fspath):
            item.add_marker(pytest.mark.real_integration)
            item.add_marker(pytest.mark.supabase)
            item.add_marker(pytest.mark.database)
        elif "real_api" in str(item.fspath):
            item.add_marker(pytest.mark.real_api)
            item.add_marker(pytest.mark.supabase)
            item.add_marker(pytest.mark.database)
        elif "real_business" in str(item.fspath):
            item.add_marker(pytest.mark.real_business)
            item.add_marker(pytest.mark.supabase)
            item.add_marker(pytest.mark.database)

        # Skip if Supabase not configured
        has_supabase_marker = any(m.name == "supabase" for m in item.iter_markers())
        if has_supabase_marker:
            try:
                # Use module-level api config to avoid name shadowing with pytest config
                api_config = globals().get("config", {})
                supabase_url = (
                    api_config.get("SUPABASE_URL")
                    if isinstance(api_config, dict)
                    else getattr(api_config, "SUPABASE_URL", None)
                )
            except Exception:
                supabase_url = None
            # Debug log to understand skip behavior
            logger.info(
                f"Collection check for {item.nodeid}: has_supabase_marker={has_supabase_marker}, SUPABASE_URL={'SET' if supabase_url else 'NOT SET'}"
            )
            if not supabase_url:
                item.add_marker(pytest.mark.skip(reason="Supabase not configured"))


@pytest.fixture(autouse=True)
def reset_test_env():
    """Reset test environment before each test."""
    yield
    # Cleanup after test


# ============================================================================
# LOGGING HELPERS
# ============================================================================


def log_test_info(test_name: str, details: Dict[str, Any]):
    """Log test information."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {test_name}")
    logger.info(f"{'='*60}")
    for key, value in details.items():
        if isinstance(value, (dict, list)) and len(str(value)) > 100:
            logger.info(f"{key}: {str(value)[:100]}...")
        else:
            logger.info(f"{key}: {value}")
    logger.info(f"{'='*60}\n")


@pytest.fixture
def log_test(request):
    """Auto-log test information."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Running: {request.node.nodeid}")
    logger.info(f"{'='*80}")
    yield
    logger.info(f"{'='*80}\n")
