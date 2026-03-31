"""
Configuration module for the API.

This module loads configuration from environment variables or default values.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from project root first, then backend/api/.env for overrides
root_env_path = Path(__file__).resolve().parents[3] / ".env"
if root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path)
    logger.info(f"Loaded environment variables from {root_env_path}")

# GitHub Actions will provide these as environment variables directly
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.info("No backend/api .env file found, using environment variables from system")


def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.

    Returns:
        Dictionary of configuration values.
    """
    default_db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "prices.db",
    )

    cors_origins_env = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173",
    )
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

    data_backend = os.getenv("DATA_BACKEND", "sqlite").strip().lower()
    if data_backend not in {"sqlite", "supabase"}:
        data_backend = "sqlite"

    supabase_db_url = os.getenv("SUPABASE_DB_URL")

    config = {
        # API server configuration
        "API_HOST": os.getenv("API_HOST", "0.0.0.0"),
        "API_PORT": int(os.getenv("API_PORT", "8000")),
        "API_DEBUG": os.getenv("API_DEBUG", "false").lower() in ("true", "1", "yes"),
        # Redis configuration
        "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
        "REDIS_PORT": int(os.getenv("REDIS_PORT", "6379")),
        "REDIS_DB": int(os.getenv("REDIS_DB", "0")),
        "REDIS_PREFIX": os.getenv("REDIS_PREFIX", "statarb:api:"),
        "REDIS_TTL": int(os.getenv("REDIS_TTL", "3600")),
        "REDIS_CONNECT_TIMEOUT_SECONDS": float(
            os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "1.0")
        ),
        # Database configuration - prioritize TimescaleDB over Supabase over SQLite
        "DB_PATH": os.getenv("DB_PATH", default_db_path),
        "USE_TIMESCALEDB": bool(os.getenv("DATABASE_URL"))
        and "stackhero" in os.getenv("DATABASE_URL", ""),
        "DATA_BACKEND": data_backend,
        "USE_SUPABASE_DB": data_backend == "supabase" or bool(supabase_db_url),
        "USE_SQLITE_DB": data_backend == "sqlite",
        "DATABASE_URL": os.getenv("DATABASE_URL")
        or os.getenv("TIMESCALEDB_URL")
        or supabase_db_url
        or f"sqlite:///{default_db_path}",
        # CORS configuration - allow common development ports and production
        # NOTE: In production, set CORS_ORIGINS env var to specific domains (e.g., "https://hedgevision.app,https://www.hedgevision.app")
        "CORS_ORIGINS": cors_origins or ["*"],
        # Supabase configuration
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY"),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        "SUPABASE_DB_URL": os.getenv("SUPABASE_DB_URL"),  # Direct PostgreSQL connection
        # Supabase JWT configuration
        "SUPABASE_JWT_SECRET": os.getenv("SUPABASE_JWT_SECRET"),
        "SUPABASE_JWKS_URL": os.getenv("SUPABASE_JWKS_URL")
        or f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/auth/v1/keys",
        "JWT_STORAGE_KEY": os.getenv("JWT_STORAGE_KEY", "hedgevision_token"),
        # Data provider API keys (all external API integrations)
        "TIINGO_API_KEY": os.getenv("TIINGO_API_KEY"),
        "BINANCE_API_KEY": os.getenv(
            "BINANCE_API_KEY"
        ),  # Optional for public endpoints
        "BINANCE_API_SECRET": os.getenv("BINANCE_API_SECRET")
        or os.getenv("BINANCE_SECRET_KEY"),  # Backward compatible alias
        "POLYGON_API_KEY": os.getenv("POLYGON_API_KEY"),
        "FINNHUB_API_KEY": os.getenv("FINNHUB_API_KEY"),
        "FMP_API_KEY": os.getenv("FMP_API_KEY"),  # Financial Modeling Prep
        "EODHD_API_KEY": os.getenv("EODHD_API_KEY"),
        "ALPHA_VANTAGE_API_KEY": os.getenv("ALPHA_VANTAGE_API_KEY"),
        "COINMARKETCAP_API_KEY": os.getenv("COINMARKETCAP_API_KEY"),
        # DB Health integration settings
        "DB_HEALTH_ENABLED": os.getenv("DB_HEALTH_ENABLED", "true").lower()
        in ("true", "1", "yes"),
        "DB_HEALTH_API_URL": os.getenv("DB_HEALTH_API_URL", "http://localhost:8000"),
        "DB_HEALTH_API_KEY": os.getenv("DB_HEALTH_API_KEY"),
        # Data ingestion settings
        "INGESTION_MAX_CONCURRENT": int(os.getenv("INGESTION_MAX_CONCURRENT", "5")),
        "INGESTION_RETRY_ATTEMPTS": int(os.getenv("INGESTION_RETRY_ATTEMPTS", "3")),
        "INGESTION_RATE_LIMIT_BUFFER": float(
            os.getenv("INGESTION_RATE_LIMIT_BUFFER", "1.1")
        ),  # 10% buffer
        # Computation settings
        "COMPUTATION_ENABLED": os.getenv("COMPUTATION_ENABLED", "true").lower()
        in ("true", "1", "yes"),
        "COMPUTATION_SCHEDULE": os.getenv("COMPUTATION_SCHEDULE", "02:00"),  # UTC time
        "COMPUTATION_DELAY_MINUTES": int(os.getenv("COMPUTATION_DELAY_MINUTES", "30")),
        "MODEL_VERSION": os.getenv("MODEL_VERSION", "prod-v1"),
        "ENABLE_EXTERNAL_LLM": os.getenv("ENABLE_EXTERNAL_LLM", "false").lower()
        in ("true", "1", "yes"),
        "LOCAL_ML_BACKEND": os.getenv("LOCAL_ML_BACKEND", "numpy").strip().lower(),
        "LOCAL_ML_MODEL_PATH": os.getenv("LOCAL_ML_MODEL_PATH"),
        "BROKER_BACKEND": os.getenv("BROKER_BACKEND", "paper").strip().lower(),
        "CCXT_EXCHANGE": os.getenv("CCXT_EXCHANGE", "binance").strip().lower(),
        "CCXT_API_KEY": os.getenv("CCXT_API_KEY") or os.getenv("BINANCE_API_KEY"),
        "CCXT_API_SECRET": os.getenv("CCXT_API_SECRET")
        or os.getenv("BINANCE_API_SECRET")
        or os.getenv("BINANCE_SECRET_KEY"),
        "ENABLE_AUTO_POPULATE_ON_STARTUP": os.getenv(
            "ENABLE_AUTO_POPULATE_ON_STARTUP", "false"
        ).lower()
        in ("true", "1", "yes"),
        "CORRELATION_WINDOW_DAYS": int(os.getenv("CORRELATION_WINDOW_DAYS", "60")),
        "ROLLING_METRICS_WINDOWS": [
            int(x)
            for x in os.getenv("ROLLING_METRICS_WINDOWS", "30,60,90,180,252").split(",")
        ],
        # Data quality settings
        "DATA_QUALITY_MIN_THRESHOLD": float(
            os.getenv("DATA_QUALITY_MIN_THRESHOLD", "0.8")
        ),
        "DATA_RETENTION_DAYS": int(
            os.getenv("DATA_RETENTION_DAYS", "3650")
        ),  # 10 years
        "STALE_DATA_THRESHOLD_HOURS": int(
            os.getenv("STALE_DATA_THRESHOLD_HOURS", "48")
        ),
        # Pre-computation settings
        "PRECOMPUTE_MAX_AGE_HOURS": int(os.getenv("PRECOMPUTE_MAX_AGE_HOURS", "6")),
        "PRECOMPUTE_MIN_CORRELATION": float(
            os.getenv("PRECOMPUTE_MIN_CORRELATION", "0.7")
        ),
        "PRECOMPUTE_MAX_PAIRS": int(os.getenv("PRECOMPUTE_MAX_PAIRS", "100")),
        # Default parameters
        "DEFAULT_LOOKBACK_DAYS": int(os.getenv("DEFAULT_LOOKBACK_DAYS", "365")),
        "DEFAULT_MIN_HISTORY_DAYS": int(os.getenv("DEFAULT_MIN_HISTORY_DAYS", "252")),
    }

    return config


# Load configuration on module import
config = get_config()

logger.info(
    f"Loaded configuration: API_PORT={config['API_PORT']}, REDIS_HOST={config['REDIS_HOST']}"
)
