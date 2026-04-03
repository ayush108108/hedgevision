"""
HedgeVision FastAPI Backend

Core routers are always loaded. Optional routers are gated behind
ENABLE_* environment variables (all disabled by default for lean deployment).

Enable optional features via env vars:
  ENABLE_AUTH=true
  ENABLE_BROKER=true
  ENABLE_PORTFOLIO=true
  ENABLE_BACKTEST=true
  ENABLE_NEWS=true
  ENABLE_CRYPTO=true
  ENABLE_WEBSOCKET=true
  ENABLE_DATA_SYNC=true
  ENABLE_WATCHLIST=true
  ENABLE_CACHE_MGMT=true
  AI_AUDIT_ENABLED=true
"""

import logging
import os
import sys
from datetime import datetime
import importlib
import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path to import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core routers (always loaded)
from api.routers import (
    assets,
    cointegration,
    correlation,
    metrics,
    pair_analysis,
    screener,
    market_intel,
    standardization,
    waitlist,
)
from api.utils.cache import get_cache_manager

# Import configuration
from api.utils.config import config
from api.utils.error_handlers import register_error_handlers
from api.utils.rate_limiter import RateLimitMiddleware, get_rate_limiter
from api.utils.security import (
    sanitized_config_display,
    validate_api_keys_configured,
    validate_required_env_vars,
)
from api.utils.security_headers import SecurityHeadersMiddleware


def _feature_enabled(key: str) -> bool:
    return os.getenv(key, "false").lower() in ("1", "true", "yes")


# Configure logging
logging.basicConfig(
    level=logging.INFO if not config["API_DEBUG"] else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
API_VERSION = os.getenv("API_VERSION", "2.1.0")

# Initialize cache manager
cache_mgr = get_cache_manager(
    redis_host=config["REDIS_HOST"],
    redis_port=config["REDIS_PORT"],
    redis_db=config["REDIS_DB"],
    prefix=config["REDIS_PREFIX"],
)

# Validate required environment variables on startup
env_validation = validate_required_env_vars()
if not all(env_validation.values()):
    logger.warning("Some required environment variables are missing - see logs above")

# Initialize rate limiter
raw_redis_client = None
try:
    if cache_mgr and getattr(cache_mgr, "redis_cache", None):
        raw_redis_client = getattr(cache_mgr.redis_cache, "redis", None)
except Exception:
    raw_redis_client = None

rate_limiter = get_rate_limiter(
    redis_client=raw_redis_client,
    enabled=not config["API_DEBUG"],
)

# Create FastAPI application
app = FastAPI(
    title="HedgeVision API",
    description="Statistical arbitrage & quantitative analysis API",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register standardized error handlers
register_error_handlers(app)

# Middleware stack
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    enabled=not config["API_DEBUG"],
)

cors_origins = config.get("CORS_ORIGINS", ["*"])
logger.info(f"CORS origins: {cors_origins}")
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# --- Router registration ---
# Core routers (always enabled)
CORE_ROUTERS = [
    assets.router,
    correlation.router,
    pair_analysis.router,
    screener.router,
    cointegration.router,
    metrics.router,
    market_intel.router,
    standardization.router,
    waitlist.router,
]

for router in CORE_ROUTERS:
    app.include_router(router)
    app.include_router(router, prefix="/api")

# Optional routers (gated by ENABLE_* env vars)
OPTIONAL_ROUTERS = {
    "ENABLE_AUTH": "api.routers.auth",
    "ENABLE_BROKER": "api.routers.broker",
    "ENABLE_PORTFOLIO": "api.routers.portfolio",
    "ENABLE_BACKTEST": "api.routers.backtest",
    "ENABLE_NEWS": "api.routers.news",
    "ENABLE_CRYPTO": "api.routers.crypto",
    "ENABLE_WEBSOCKET": "api.routers.websocket",
    "ENABLE_DATA_SYNC": "api.routers.data_sync",
    "ENABLE_WATCHLIST": "api.routers.watchlist",
    "ENABLE_CACHE_MGMT": "api.routers.cache",
    "AI_AUDIT_ENABLED": "api.routers.audit",
}

for env_key, module_path in OPTIONAL_ROUTERS.items():
    if _feature_enabled(env_key):
        try:
            mod = importlib.import_module(module_path)
            router = getattr(mod, "router", None)
            if router:
                app.include_router(router)
                app.include_router(router, prefix="/api")
                logger.info(f"Optional router enabled: {module_path}")
        except Exception as exc:
            logger.warning(f"Failed to load optional router {module_path}: {exc}")


# Serving Frontend Static Files
# Path is relative to the backend/api/main.py or absolute /app/frontend-v2/dist
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend-v2", "dist")

if os.path.exists(frontend_path):
    # Mount assets folder
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
    
    # Static files at the root of dist (like vite.svg)
    app.mount("/static_root", StaticFiles(directory=frontend_path), name="static_root")
else:
    logger.warning(f"Frontend dist not found at {frontend_path}. Frontend will not be served.")


@app.get("/")
async def root():
    """Serve frontend index if available, else API info."""
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    return {
        "name": "HedgeVision API",
        "version": API_VERSION,
        "description": "Statistical arbitrage platform powered by Yahoo Finance",
        "status": "healthy",
        "documentation": "/docs",
        "health_check": "/health",
        "timestamp": datetime.now().isoformat(),
    }


# Health check is below


@app.get("/health")
async def health_check():
    """Health check for Heroku and load balancers."""
    from api.utils.supabase_client import get_supabase_client

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "hedgevision-api",
        "version": API_VERSION,
        "checks": {},
    }

    # Check data backend
    try:
        if config.get("DATA_BACKEND") == "sqlite":
            db_path = config.get("DB_PATH")
            with sqlite3.connect(db_path, timeout=1.0) as conn:
                conn.execute("SELECT 1")
            health_status["checks"]["sqlite"] = {"status": "healthy"}
        else:
            supabase = get_supabase_client()
            if supabase:
                health_status["checks"]["supabase"] = {"status": "healthy"}
            else:
                health_status["checks"]["supabase"] = {"status": "degraded"}
                health_status["status"] = "degraded"
    except Exception as e:
        backend = config.get("DATA_BACKEND")
        health_status["checks"][backend] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        return JSONResponse(content=health_status, status_code=503)

    return health_status


@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch-all for React/Frontend routes (must be last)."""
    # Don't interfere with API, docs, or health routes - let routers handle them
    # This only catches frontend SPA routes
    if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json", "health"]:
        # Don't catch - let it 404 naturally from routers
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Serve frontend index.html for all other routes (SPA routing)
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.on_event("startup")
async def startup_event():
    logger.info("Starting HedgeVision API server")
    logger.info(f"Data backend: {config.get('DATA_BACKEND')}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down HedgeVision API server")
