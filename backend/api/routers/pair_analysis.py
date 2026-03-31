"""
Pair analysis endpoints - THIN ROUTER

This router delegates all business logic to analytics_service.
It's a "thin" API layer that just handles HTTP concerns.

Architecture:
  pair_analysis.py (router) → analytics_service.py → cointegration_service.py

NOTE: Complex _run_analysis logic moved to analytics_service.get_full_pair_report()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pair-analysis", tags=["pair-analysis"])


class RollingBetaRequest(BaseModel):
    asset: str = Field(..., description="Display name of the asset")
    benchmark: str = Field(
        "S&P 500 ETF", description="Display name of the benchmark asset"
    )
    window: int = Field(60, ge=2, description="Rolling window size in periods")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    granularity: str = Field("daily", description="Data frequency (daily|hourly)")


class RollingBetaPoint(BaseModel):
    date: datetime
    beta: Optional[float]


class RollingBetaResponse(BaseModel):
    asset: str
    benchmark: str
    window: int
    granularity: str
    data: List[RollingBetaPoint]


class RollingVolatilityRequest(BaseModel):
    asset: str = Field(..., description="Display name of the asset")
    window: int = Field(21, ge=2, description="Rolling window size in periods")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    granularity: str = Field("daily", description="Data frequency (daily|hourly)")
    annualization_factor: Optional[int] = Field(
        None, description="Optional annualization factor override"
    )


class RollingVolatilityPoint(BaseModel):
    date: datetime
    volatility: Optional[float]


class RollingVolatilityResponse(BaseModel):
    asset: str
    window: int
    granularity: str
    data: List[RollingVolatilityPoint]


# ============================================================================
# PAIR ANALYSIS ENDPOINTS (THIN WRAPPERS)
# ============================================================================
# All business logic moved to analytics_service.get_full_pair_report()
# These endpoints are thin HTTP wrappers that delegate to the service layer.
# ============================================================================

@router.get("")
async def get_pair_analysis(
    asset1: str = Query(..., description="Display name of the first asset"),
    asset2: str = Query(..., description="Display name of the second asset"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query("daily", description="Data frequency"),
    use_precomputed: bool = Query(
        True, description="Use pre-computed results if available"
    ),
) -> Dict[str, Any]:
    """
    Get comprehensive pair analysis.
    
    THIN ROUTER: Delegates all logic to analytics_service.get_full_pair_report()
    """
    try:
        report = await analytics_service.get_full_pair_report(
            asset1=asset1,
            asset2=asset2,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            use_precomputed=use_precomputed,
            include_price_data=True,
            include_spread_data=True
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pair analysis endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cointegration")
async def get_cointegration_results(
    asset1: str = Query(...),
    asset2: str = Query(...),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = "daily",
    use_precomputed: bool = Query(
        True, description="Use pre-computed results if available"
    ),
) -> Dict[str, Any]:
    """
    Get cointegration results only.
    
    THIN ROUTER: Calls analytics_service and extracts cointegration section.
    """
    try:
        report = await analytics_service.get_full_pair_report(
            asset1=asset1,
            asset2=asset2,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            use_precomputed=use_precomputed,
            include_price_data=False,
            include_spread_data=False
        )
        
        cointegration_results = report.get("cointegration_results")
        if not cointegration_results:
            raise HTTPException(
                status_code=404,
                detail="Cointegration results unavailable"
            )
        return cointegration_results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cointegration results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: /spread removed - use /api/cointegration/pairs/{asset1}/{asset2}/spread
# Provides historical spread data from DB with trading signals and z-scores


# ============================================================================
# DEPRECATED: Screener endpoints removed on 2025-10-30
# Screener endpoints have been consolidated in api/routers/screener.py
# Use /api/screener/* endpoints instead of /api/pair-analysis/screener/*
# ============================================================================
