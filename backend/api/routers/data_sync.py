"""
API endpoints for triggering data sync operations.
Called by Supabase Edge Functions or manual triggers.

Updated to use pipeline_service.py for data ingestion.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..services.pipeline_service import PipelineService
from ..utils.config import config
from ..utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# Router prefix (note: /api prefix added in main.py, so this results in /api/data-sync)
router = APIRouter(prefix="/data-sync", tags=["data-sync"])


class SyncRequest(BaseModel):
    """Request model for sync operations."""

    source: str = "manual"  # manual, edge_function, cron
    timestamp: Optional[str] = None
    symbols: Optional[list[str]] = None  # Optional: specific symbols to sync
    force: bool = False  # Force re-fetch even if data exists


class SyncResponse(BaseModel):
    """Response model for sync operations."""

    success: bool
    message: str
    symbols_processed: int = 0
    records_added: int = 0
    records_updated: int = 0
    time_elapsed: str = "0s"
    providers_used: list[str] = []
    errors: list[str] = []


def verify_api_secret(authorization: str = Header(None)) -> bool:
    """Verify API secret key from request headers."""
    expected_secret = config.get("API_SECRET_KEY")

    if not expected_secret:
        logger.error("API_SECRET_KEY not configured in environment")
        raise HTTPException(status_code=500, detail="Server configuration error")

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.replace("Bearer ", "")

    if token != expected_secret:
        logger.warning(f"Invalid API secret attempt from source")
        raise HTTPException(status_code=401, detail="Invalid API secret")

    return True


@router.post("/daily", response_model=SyncResponse)
async def trigger_daily_sync(
    request: SyncRequest, authorized: bool = Depends(verify_api_secret)
):
    """
    Trigger daily data sync for all active symbols.

    This endpoint:
    1. Fetches latest price data from all configured providers
    2. Updates database with new records
    3. Computes analytics (correlations, pairs, etc.)
    4. Returns summary statistics

    Called by:
    - Supabase Edge Function (scheduled via pg_cron)
    - Manual admin triggers
    - CI/CD pipelines
    """
    logger.info(f"Daily sync triggered by: {request.source}")
    start_time = datetime.now()

    try:
        # Initialize pipeline service
        pipeline_service = PipelineService()
        supabase = get_supabase_client()

        # Determine symbols to sync
        if request.symbols:
            symbols_to_sync = request.symbols
        else:
            # Get all active assets from database
            assets_response = (
                supabase.client.table("assets")
                .select("symbol")
                .eq("is_active", 1)
                .execute()
            )
            symbols_to_sync = [asset["symbol"] for asset in assets_response.data] if assets_response.data else []

        if not symbols_to_sync:
            logger.warning("No symbols to sync")
            return SyncResponse(
                success=True,
                message="No symbols to sync",
                time_elapsed="0s",
            )

        # Determine date range (last 7 days to catch any missed data)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        logger.info(f"Starting data ingestion for {len(symbols_to_sync)} symbols...")
        
        # Run batch pipeline
        ingestion_result = await pipeline_service.run_batch_pipeline(
            symbols=symbols_to_sync,
            start_date=start_date,
            end_date=end_date,
            granularity="daily",
            max_concurrent=5,
            validate=True
        )

        # Calculate elapsed time
        elapsed = (datetime.now() - start_time).total_seconds()

        # Compile response
        response = SyncResponse(
            success=True,
            message="Daily sync completed successfully",
            symbols_processed=ingestion_result.get("successful", 0) + ingestion_result.get("partial", 0),
            records_added=ingestion_result.get("total_records_stored", 0),
            records_updated=0,  # Pipeline service doesn't track updates separately
            time_elapsed=f"{elapsed:.2f}s",
            providers_used=["yfinance"],  # Currently only using yfinance
            errors=[],  # Batch errors are included in individual results
        )

        logger.info(f"Daily sync completed: {response.dict()}")
        return response

    except Exception as e:
        logger.error(f"Daily sync failed: {str(e)}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()

        return SyncResponse(
            success=False,
            message=f"Daily sync failed: {str(e)}",
            time_elapsed=f"{elapsed:.2f}s",
            errors=[str(e)],
        )


@router.post("/hourly", response_model=SyncResponse)
async def trigger_hourly_sync(
    request: SyncRequest, authorized: bool = Depends(verify_api_secret)
):
    """
    Trigger hourly data sync for high-priority symbols.

    Fetches intraday updates for:
    - Major indices (SPY, QQQ, DIA)
    - High-volume tech stocks (AAPL, MSFT, GOOGL)
    - Actively traded pairs

    Does NOT recompute full analytics (too expensive).
    """
    logger.info(f"Hourly sync triggered by: {request.source}")
    start_time = datetime.now()

    try:
        pipeline_service = PipelineService()

        # High-priority symbols for hourly updates
        priority_symbols = request.symbols or [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "SPY",
            "QQQ",
            "DIA",
        ]

        # Quick ingestion - last 2 days only
        end_date = datetime.now()
        start_date = end_date - timedelta(days=2)

        result = await pipeline_service.run_batch_pipeline(
            symbols=priority_symbols,
            start_date=start_date,
            end_date=end_date,
            granularity="hourly",
            max_concurrent=5,
            validate=True
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        return SyncResponse(
            success=True,
            message="Hourly sync completed",
            symbols_processed=result.get("successful", 0) + result.get("partial", 0),
            records_added=result.get("total_records_stored", 0),
            time_elapsed=f"{elapsed:.2f}s",
            providers_used=["yfinance"],
        )

    except Exception as e:
        logger.error(f"Hourly sync failed: {str(e)}", exc_info=True)
        elapsed = (datetime.now() - start_time).total_seconds()

        return SyncResponse(
            success=False,
            message=f"Hourly sync failed: {str(e)}",
            time_elapsed=f"{elapsed:.2f}s",
            errors=[str(e)],
        )


@router.get("/status")
async def get_sync_status():
    """
    Get current data sync status without authentication.

    Returns:
    - Total assets tracked
    - Recent sync activity
    - Data freshness
    """
    try:
        supabase = get_supabase_client()
        
        # Get total active assets
        assets_response = (
            supabase.client.table("assets")
            .select("id, symbol, last_price_update", count="exact")
            .eq("is_active", 1)
            .execute()
        )
        
        total_assets = len(assets_response.data) if assets_response.data else 0
        
        # Get most recent price update
        recent_price_response = (
            supabase.client.table("price_history")
            .select("timestamp")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        
        last_update = None
        if recent_price_response.data and len(recent_price_response.data) > 0:
            last_update = recent_price_response.data[0].get("timestamp")
        
        status = {
            "total_assets": total_assets,
            "last_sync": last_update,
            "data_provider": "yfinance",
            "sync_status": "operational",
        }

        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
