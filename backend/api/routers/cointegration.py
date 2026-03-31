"""
Cointegration Analysis API Router

This module provides endpoints for cointegration testing, pair screening,
and trading signal generation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Any

import numpy as np

# Import unified models from screener
from api.routers.screener import UnifiedScreenerPair, UnifiedScreenerResponse
from api.services.cointegration_service import CointegrationService
from api.services.data_standardization_service import data_standardization_service
from api.utils.cache_adapter import get_cache_adapter
from api.utils.config import config
from api.utils.supabase_client import get_supabase_client
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def convert_value(val):
    """
    Convert numpy types to native Python types for JSON serialization.
    
    Args:
        val: Value to convert (can be numpy type or native Python type)
    
    Returns:
        Native Python type suitable for JSON serialization
    """
    if val is None:
        return None
    # Handle boolean types first (before int check, since bool is subclass of int)
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        return float(val) if not np.isnan(val) and not np.isinf(val) else None
    if isinstance(val, str):
        return str(val)
    return val


def convert_dict_values(d):
    """
    Recursively convert all values in a dictionary to JSON-serializable types.
    
    Args:
        d: Dictionary to convert
    
    Returns:
        Dictionary with all values converted to native Python types
    """
    if not isinstance(d, dict):
        return convert_value(d)
    
    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = convert_dict_values(value)
        elif isinstance(value, list):
            result[key] = [convert_dict_values(item) if isinstance(item, dict) else convert_value(item) for item in value]
        else:
            result[key] = convert_value(value)
    return result


# Initialize router
router = APIRouter(prefix="/cointegration", tags=["Cointegration"])

# Initialize services
cointegration_service = CointegrationService()
cache = get_cache_adapter(default_ttl=config.get("REDIS_TTL", 3600))
supabase = get_supabase_client()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class TestPairRequest(BaseModel):
    """Request model for testing a single pair"""

    asset1: str = Field(..., description="First asset symbol")
    asset2: str = Field(..., description="Second asset symbol")
    granularity: str = Field(default="daily", description="Data granularity (daily/4h)")
    lookback_days: int = Field(
        default=252, description="Lookback period in days", ge=60, le=1260
    )


class TestPairResponse(BaseModel):
    """Response model for pair test results"""

    test_id: str
    asset1_symbol: str
    asset2_symbol: str
    test_date: str
    granularity: str
    lookback_days: int
    sample_size: int

    # Overall assessment
    overall_score: float
    cointegration_strength: str
    trading_suitability: str
    risk_level: str

    # Key metrics
    eg_is_cointegrated: bool
    eg_pvalue: float
    beta_coefficient: float
    half_life_days: float
    sharpe_ratio: Optional[float]

    computation_time_ms: int


class ScreenRequest(BaseModel):
    """Request model for batch screening"""

    granularity: str = Field(default="daily", description="Data granularity")
    lookback_days: int = Field(
        default=252, description="Lookback period", ge=60, le=1260
    )
    min_correlation: float = Field(
        default=0.7, description="Minimum correlation", ge=0.0, le=1.0
    )
    assets: Optional[List[str]] = Field(
        default=None, description="Specific assets to screen (None = all)"
    )


class ScreenStatusResponse(BaseModel):
    """Response model for screening job status"""

    job_id: str
    status: str  # pending, running, completed, failed
    progress: dict
    started_at: str
    completed_at: Optional[str]
    results_count: Optional[int]


# ============================================================================
# ENDPOINTS: PAIR TESTING
# ============================================================================


@router.post("/test-pair", response_model=TestPairResponse)
async def test_pair(request: TestPairRequest):
    """
    Run comprehensive cointegration tests on a single asset pair.

    Executes 8 statistical tests:
    - Engle-Granger cointegration test
    - Johansen multivariate test
    - Augmented Dickey-Fuller (ADF)
    - Phillips-Perron test
    - KPSS stationarity test
    - Linear regression (hedge ratio)
    - Mean reversion metrics
    - Trading quality assessment

    Returns 69 fields of test results stored in the database.
    """
    try:
        logger.info(f"Testing pair: {request.asset1} - {request.asset2}")

        # Convert asset names to symbols if needed (handle both "SPY" and "SPY.US" formats)
        from api.utils.assets import name_to_symbol
        
        asset1_symbol = request.asset1
        if "." not in asset1_symbol:
            # Try to find it in name_to_symbol dict or append .US
            asset1_symbol = name_to_symbol.get(asset1_symbol, f"{asset1_symbol}.US")
        
        asset2_symbol = request.asset2
        if "." not in asset2_symbol:
            asset2_symbol = name_to_symbol.get(asset2_symbol, f"{asset2_symbol}.US")

        logger.info(f"Resolved symbols: {asset1_symbol} - {asset2_symbol}")

        # 1. Fetch price data from database
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=request.lookback_days)

        # Fetch data for both assets
        asset1_data = await _fetch_price_data(
            asset1_symbol,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            request.granularity,
        )

        asset2_data = await _fetch_price_data(
            asset2_symbol,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            request.granularity,
        )

        if asset1_data.empty or asset2_data.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient price data for {request.asset1} or {request.asset2}",
            )

        # 2. Standardize data
        asset1_std = data_standardization_service.standardize_price_data(
            df=asset1_data, symbol=request.asset1, data_type="ohlcv", validate=True
        )

        asset2_std = data_standardization_service.standardize_price_data(
            df=asset2_data, symbol=request.asset2, data_type="ohlcv", validate=True
        )

        # 3. Create pair DataFrame
        pair_df = data_standardization_service.create_pair_dataframe(
            asset1_df=asset1_std,
            asset2_df=asset2_std,
            asset1_symbol=request.asset1,
            asset2_symbol=request.asset2,
        )

        # 4. Validate data quality
        validation = data_standardization_service.validate_pair_data_quality(
            pair_df=pair_df, min_records=min(60, request.lookback_days // 2)
        )

        if not validation["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Data quality validation failed: {validation['issues']}",
            )

        # 5. Run cointegration tests
        result = cointegration_service.test_pair(
            asset1_symbol=request.asset1,
            asset2_symbol=request.asset2,
            prices_df=pair_df,
            granularity=request.granularity,
            lookback_days=request.lookback_days,
        )

        # 6. Store results in database
        test_id = await _store_test_result(result)

        # 7. Return simplified response with converted values
        # Prepare sharpe ratio safely
        _sharpe_raw = convert_value(result.sharpe_ratio)
        _sharpe_cast = (
            float(_sharpe_raw)
            if isinstance(_sharpe_raw, (int, float)) and _sharpe_raw is not None
            else None
        )

        return TestPairResponse(
            test_id=str(test_id),
            asset1_symbol=result.asset1_symbol,
            asset2_symbol=result.asset2_symbol,
            test_date=result.test_date,
            granularity=result.granularity,
            lookback_days=int(convert_value(result.lookback_days) or 0),
            sample_size=int(convert_value(result.sample_size) or 0),
            overall_score=float(convert_value(result.overall_score) or 0.0),
            cointegration_strength=result.cointegration_strength,
            trading_suitability=result.trading_suitability,
            risk_level=result.risk_level,
            eg_is_cointegrated=bool(convert_value(result.eg_is_cointegrated)),
            eg_pvalue=float(convert_value(result.eg_pvalue) or 0.0),
            beta_coefficient=float(convert_value(result.beta_coefficient) or 0.0),
            half_life_days=float(convert_value(result.half_life_days) or 0.0),
            sharpe_ratio=_sharpe_cast,
            computation_time_ms=int(convert_value(result.computation_time_ms) or 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing pair: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{test_id}")
async def get_test_results(test_id: str):
    """
    Get complete test results by test ID.

    Returns all fields from the cointegration_scores table.
    """
    try:
        # Query from database
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        response = (
            supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
            .select("*")
            .eq("id", test_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail=f"Test result {test_id} not found"
            )

        return response.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/pair/{asset1}/{asset2}")
async def get_pair_history(
    asset1: str,
    asset2: str,
    granularity: str = Query(default="daily", description="Data granularity"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of results"),
):
    """
    Get historical test results for a specific pair.

    Returns the most recent test results sorted by test_date descending.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        response = (
            supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
            .select("*")
            .eq("asset1_symbol", asset1)
            .eq("asset2_symbol", asset2)
            .eq("granularity", granularity)
            .order("test_date", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "asset1": asset1,
            "asset2": asset2,
            "granularity": granularity,
            "count": len(response.data),
            "results": response.data,
        }

    except Exception as e:
        logger.error(f"Error fetching pair history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS: TOP PAIRS & SCREENING
# ============================================================================


# MOVED: This functionality is now at /api/screener/cointegration/top-pairs
# Kept here for backward compatibility but marked deprecated
@router.get(
    "/unified/top-pairs", response_model=UnifiedScreenerResponse, deprecated=True
)
async def get_unified_top_pairs_deprecated(
    limit: int = Query(default=20, ge=1, le=100, description="Number of pairs"),
    granularity: str = Query(default="daily", description="Data granularity"),
    min_score: float = Query(
        default=60.0, ge=0.0, le=100.0, description="Minimum overall score"
    ),
):
    """DEPRECATED: Use /api/screener/cointegration/top-pairs instead."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=f"/api/screener/cointegration/top-pairs?limit={limit}&granularity={granularity}&min_score={min_score}",
        status_code=308,
    )
    try:
        # Use helper function from database
        response = supabase.client.rpc(
            "get_top_cointegrated_pairs",
            {"p_limit": limit, "p_granularity": granularity, "p_min_score": min_score},
        ).execute()

        # Convert to unified format
        unified_pairs: List[UnifiedScreenerPair] = []
        for pair in response.data:
            unified_pairs.append(
                UnifiedScreenerPair(
                    asset1=pair.get("asset1_symbol", pair.get("asset1", "")),
                    asset2=pair.get("asset2_symbol", pair.get("asset2", "")),
                    screener_type="cointegration",
                    primary_metric_name="Cointegration Score",
                    primary_metric_value=float(pair.get("overall_score", 0.0)),
                    secondary_metric_name="Half-Life (days)",
                    secondary_metric_value=(
                        float(pair.get("half_life_days"))
                        if pair.get("half_life_days")
                        else None
                    ),
                    is_cointegrated=bool(pair.get("eg_is_cointegrated", False)),
                    last_updated=pair.get("test_date"),
                )
            )

        logger.info(f"Retrieved {len(unified_pairs)} unified cointegrated pairs")

        return UnifiedScreenerResponse(
            pairs=unified_pairs[:limit],
            total_pairs=len(unified_pairs),
            screener_type="cointegration",
            data_age_hours=0.0,  # Computed from materialized view
            cache_status="materialized_view",
            granularity=granularity,
            filters_applied={
                "min_score": min_score,
            },
        )

    except Exception as e:
        logger.error(f"Error fetching unified top pairs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# NOTE: /pairs/top removed - use /api/screener/cointegration/top-pairs instead
# Provides same data in unified format compatible with all screener types


@router.get("/pairs/latest")
async def get_latest_scores(
    granularity: str = Query(default="daily", description="Data granularity"),
    cointegrated_only: bool = Query(
        default=True, description="Only cointegrated pairs"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Number of results"),
):
    """
    Get latest cointegration scores from materialized view.

    Optimized for fast queries with pre-computed latest results.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        query = (
            supabase.client.table("cointegration_scores_latest")  # type: ignore[union-attr]
            .select("*")
            .eq("granularity", granularity)
        )

        if cointegrated_only:
            query = query.eq("eg_is_cointegrated", 1)

        response = query.order("overall_score", desc=True).limit(limit).execute()

        return {
            "granularity": granularity,
            "cointegrated_only": cointegrated_only,
            "count": len(response.data),
            "results": response.data,
        }

    except Exception as e:
        logger.error(f"Error fetching latest scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS: SPREAD & SIGNALS
# ============================================================================


@router.get("/pairs/{asset1}/{asset2}/spread")
async def get_spread_history(
    asset1: str,
    asset2: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of records"),
    granularity: str = Query(default="daily", description="Data granularity"),
):
    """
    Get historical spread data for a pair.

    Returns spread values, z-scores, and trading signals.
    """
    try:
        # Find pair_trade_id
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        pair_response = (
            supabase.client.table("pair_trades")  # type: ignore[union-attr]
            .select("id")
            .eq("long_asset_symbol", asset1)
            .eq("short_asset_symbol", asset2)
            .eq("granularity", granularity)
            .single()
            .execute()
        )

        if not pair_response.data:
            raise HTTPException(
                status_code=404, detail=f"No pair trade found for {asset1}-{asset2}"
            )

        pair_id = pair_response.data["id"]

        # Fetch spread history
        spread_response = (
            supabase.client.table("pair_spread_history")  # type: ignore[union-attr]
            .select("*")
            .eq("pair_trade_id", pair_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "asset1": asset1,
            "asset2": asset2,
            "pair_id": pair_id,
            "granularity": granularity,
            "count": len(spread_response.data),
            "spread_data": spread_response.data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching spread history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/active")
async def get_active_signals(
    granularity: str = Query(default="daily", description="Data granularity"),
    signal_type: Optional[str] = Query(
        default=None, description="Filter by signal type"
    ),
):
    """
    Get current active trading signals.

    Returns signals with entry/exit recommendations.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        query = (
            supabase.client.table("cointegration_signals")  # type: ignore[union-attr]
            .select("*")
            .eq("granularity", granularity)
            .eq("status", "active")
        )

        if signal_type:
            query = query.eq("signal_type", signal_type)

        response = query.order("signal_strength", desc=True).execute()

        return {
            "granularity": granularity,
            "signal_type": signal_type,
            "count": len(response.data),
            "signals": response.data,
        }

    except Exception as e:
        logger.error(f"Error fetching active signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/{signal_id}/update")
async def update_signal(
    signal_id: str,
    status: str = Query(..., description="New status (filled/exited/cancelled)"),
    fill_price: Optional[float] = Query(default=None, description="Fill price"),
    exit_price: Optional[float] = Query(default=None, description="Exit price"),
):
    """
    Update a trading signal status.

    Used to track signal execution and performance.
    """
    try:
        update_data: dict[str, Any] = {"status": status, "updated_at": datetime.utcnow().isoformat()}

        if fill_price is not None:
            update_data["fill_price"] = fill_price
            update_data["filled_at"] = datetime.utcnow().isoformat()

        if exit_price is not None:
            update_data["exit_price"] = exit_price
            update_data["exited_at"] = datetime.utcnow().isoformat()

            # Calculate P&L if both prices available
            if fill_price is not None:
                update_data["realized_pnl"] = exit_price - fill_price

        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        response = (
            supabase.client.table("cointegration_signals")  # type: ignore[union-attr]
            .update(update_data)
            .eq("id", signal_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

        return {
            "signal_id": signal_id,
            "status": status,
            "updated": True,
            "data": response.data[0],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating signal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS: MAINTENANCE & UTILITIES
# ============================================================================


@router.post("/refresh-scores")
async def refresh_materialized_view():
    """
    Refresh the cointegration_scores_latest materialized view.

    Call this after batch screening completes.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        supabase.client.rpc("refresh_cointegration_scores_latest").execute()  # type: ignore[union-attr]

        return {
            "status": "success",
            "message": "Materialized view refreshed",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error refreshing view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/results/{test_id}")
async def delete_test_result(test_id: str):
    """
    Delete a test result by ID.

    Use for cleaning up old or invalid results.
    """
    try:
        if not supabase:
            raise HTTPException(status_code=503, detail="Database unavailable")
        response = (
            supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
            .delete()
            .eq("id", test_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404, detail=f"Test result {test_id} not found"
            )

        return {"deleted": True, "test_id": test_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def _fetch_price_data(
    symbol: str, start_date: str, end_date: str, granularity: str
):
    """Fetch price data from database"""
    import pandas as pd
    from api.utils.datetime_normalization import normalize_datetime_iso

    try:
        table = "price_history" if granularity == "daily" else "intraday_price_history"

        # Get asset_id
        if not supabase:
            return pd.DataFrame()
        asset_response = (
            supabase.client.table("assets")  # type: ignore[union-attr]
            .select("id")
            .eq("symbol", symbol)
            .single()
            .execute()
        )

        if not asset_response.data:
            return pd.DataFrame()

        asset_id = asset_response.data["id"]

        # Normalize query bounds
        start_iso = normalize_datetime_iso(start_date, assume="start") or str(start_date)
        end_iso = normalize_datetime_iso(end_date, assume="end") or str(end_date)

        # Fetch price data
        price_response = (
            supabase.client.table(table)  # type: ignore[union-attr]
            .select("timestamp, open, high, low, close, volume, adjusted_close")
            .eq("asset_id", asset_id)
            .gte("timestamp", start_iso)
            .lte("timestamp", end_iso)
            .order("timestamp")
            .execute()
        )

        if not price_response.data:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(price_response.data)
        df["date"] = pd.to_datetime(df["timestamp"])
        df["symbol"] = symbol

        return df

    except Exception as e:
        logger.error(f"Error fetching price data for {symbol}: {e}")
        return pd.DataFrame()


async def _store_test_result(result, max_retries: int = 3) -> str:
    """
    Store test result in database with retry logic and deduplication.

    Features:
    - Automatic retry with exponential backoff (3 attempts)
    - Upsert to prevent duplicates (same assets + date + granularity)
    - Pre-check for existing tests to avoid redundant computation
    - Comprehensive error handling with fallback
    - Transaction-safe operations

    Args:
        result: CointegrationTestResult object
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        str: Test ID (UUID) from database

    Raises:
        Exception: If all retry attempts fail
    """
    import time

    # Main storage logic with comprehensive error handling
    try:
        # Create simplified dict matching cointegration_scores table schema
        result_dict = {
            # Pair identification
            "asset1_symbol": result.asset1_symbol,
            "asset2_symbol": result.asset2_symbol,
            "test_date": result.test_date,
            "granularity": result.granularity,
            "lookback_days": convert_value(result.lookback_days),
            # Overall scoring
            "overall_score": convert_value(result.overall_score),
            # Engle-Granger (main columns)
            "eg_is_cointegrated": convert_value(result.eg_is_cointegrated),
            "eg_pvalue": convert_value(result.eg_pvalue),
            "eg_test_statistic": convert_value(result.eg_test_statistic),
            "eg_critical_value_1pct": convert_value(result.eg_critical_value_1pct),
            "eg_critical_value_5pct": convert_value(result.eg_critical_value_5pct),
            "eg_critical_value_10pct": convert_value(result.eg_critical_value_10pct),
            "eg_significance_level": result.eg_significance_level,
            # Johansen (simplified to match schema)
            "johansen_is_cointegrated": convert_value(result.johansen_is_cointegrated),
            "johansen_test_statistic": convert_value(result.johansen_trace_stat),
            "johansen_critical_value": convert_value(result.johansen_trace_crit_95),
            # ADF (simplified)
            "adf_is_stationary": convert_value(result.adf_is_stationary),
            "adf_pvalue": convert_value(result.adf_pvalue),
            "adf_test_statistic": convert_value(result.adf_test_statistic),
            # Spread characteristics
            "half_life_days": convert_value(result.half_life_days),
            "hurst_exponent": convert_value(result.hurst_exponent),
            # Regression metrics
            "hedge_ratio": convert_value(result.beta_coefficient),  # Beta is hedge ratio
            "beta_coefficient": convert_value(result.beta_coefficient),
            "alpha_intercept": convert_value(result.alpha_intercept),
            "r_squared": convert_value(result.regression_r_squared),
            "regression_std_error": convert_value(result.regression_std_error),
            # Full test results in JSONB (all 69 fields)
            "test_results": {
                "sample_size": convert_value(result.sample_size),
                # Correlation
                "pearson_correlation": convert_value(result.pearson_correlation),
                "spearman_correlation": convert_value(result.spearman_correlation),
                "kendall_tau": convert_value(result.kendall_tau),
                "correlation_pvalue": convert_value(result.correlation_pvalue),
                "correlation_significance": convert_value(result.correlation_significance),
                # Johansen (all critical values)
                "johansen_trace_stat": convert_value(result.johansen_trace_stat),
                "johansen_trace_crit_90": convert_value(result.johansen_trace_crit_90),
                "johansen_trace_crit_95": convert_value(result.johansen_trace_crit_95),
                "johansen_trace_crit_99": convert_value(result.johansen_trace_crit_99),
                "johansen_eigen_stat": convert_value(result.johansen_eigen_stat),
                "johansen_eigen_crit_90": convert_value(result.johansen_eigen_crit_90),
                "johansen_eigen_crit_95": convert_value(result.johansen_eigen_crit_95),
                "johansen_eigen_crit_99": convert_value(result.johansen_eigen_crit_99),
                "johansen_rank": convert_value(result.johansen_rank),
                # ADF (all fields)
                "adf_critical_value_1pct": convert_value(result.adf_critical_value_1pct),
                "adf_critical_value_5pct": convert_value(result.adf_critical_value_5pct),
                "adf_critical_value_10pct": convert_value(result.adf_critical_value_10pct),
                "adf_used_lag": convert_value(result.adf_used_lag),
                # Phillips-Perron
                "pp_test_statistic": convert_value(result.pp_test_statistic),
                "pp_pvalue": convert_value(result.pp_pvalue),
                "pp_critical_value_1pct": convert_value(result.pp_critical_value_1pct),
                "pp_critical_value_5pct": convert_value(result.pp_critical_value_5pct),
                "pp_critical_value_10pct": convert_value(result.pp_critical_value_10pct),
                "pp_is_stationary": convert_value(result.pp_is_stationary),
                # KPSS
                "kpss_test_statistic": convert_value(result.kpss_test_statistic),
                "kpss_pvalue": convert_value(result.kpss_pvalue),
                "kpss_critical_value_1pct": convert_value(result.kpss_critical_value_1pct),
                "kpss_critical_value_5pct": convert_value(result.kpss_critical_value_5pct),
                "kpss_critical_value_10pct": convert_value(result.kpss_critical_value_10pct),
                "kpss_is_stationary": convert_value(result.kpss_is_stationary),
                # Regression (full details)
                "regression_adj_r_squared": convert_value(result.regression_adj_r_squared),
                "regression_f_statistic": convert_value(result.regression_f_statistic),
                "regression_f_pvalue": convert_value(result.regression_f_pvalue),
                "regression_durbin_watson": convert_value(result.regression_durbin_watson),
                # Mean reversion
                "mean_reversion_speed": convert_value(result.mean_reversion_speed),
                # Spread stats
                "spread_current": convert_value(result.spread_current),
                "spread_mean": convert_value(result.spread_mean),
                "spread_std": convert_value(result.spread_std),
                "spread_min": convert_value(result.spread_min),
                "spread_max": convert_value(result.spread_max),
                "spread_skewness": convert_value(result.spread_skewness),
                "spread_kurtosis": convert_value(result.spread_kurtosis),
                # Z-score
                "zscore_current": convert_value(result.zscore_current),
                "zscore_mean": convert_value(result.zscore_mean),
                "zscore_std": convert_value(result.zscore_std),
                "zscore_entry_threshold": convert_value(result.zscore_entry_threshold),
                "zscore_exit_threshold": convert_value(result.zscore_exit_threshold),
                "zscore_stop_loss": convert_value(result.zscore_stop_loss),
                # Trading quality
                "signal_quality_score": convert_value(result.signal_quality_score),
                "sharpe_ratio": convert_value(result.sharpe_ratio),
                "profit_factor": convert_value(result.profit_factor),
                "win_rate": convert_value(result.win_rate),
                "max_drawdown_pct": convert_value(result.max_drawdown_pct),
                "avg_trade_duration_days": convert_value(result.avg_trade_duration_days),
                # Assessment
                "cointegration_strength": result.cointegration_strength,
                "trading_suitability": result.trading_suitability,
                "risk_level": result.risk_level,
                # Metadata
                "data_quality_score": convert_value(result.data_quality_score),
                "computation_time_ms": convert_value(result.computation_time_ms),
                "error_message": result.error_message,
            }
        }
        
        # Recursively convert all values in test_results to ensure JSON serialization
        result_dict["test_results"] = convert_dict_values(result_dict["test_results"])

        # STEP 1: Check for existing test to avoid redundant computation
        # Query by unique constraint fields
        existing_check = None
        try:
            if not supabase:
                raise HTTPException(status_code=503, detail="Database unavailable")
            existing_check = (
                supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
                .select("id, created_at")
                .eq("asset1_symbol", result.asset1_symbol)
                .eq("asset2_symbol", result.asset2_symbol)
                .eq("test_date", result.test_date)
                .eq("granularity", result.granularity)
                .execute()
            )

            if existing_check.data:
                existing_id = existing_check.data[0]["id"]
                logger.info(f"Test already exists (ID: {existing_id}), updating...")
        except Exception as check_error:
            logger.warning(f"Could not check for existing test: {check_error}")

        # STEP 2: Insert or update with retry logic
        # NOTE: We use INSERT/UPDATE pattern instead of upsert+on_conflict to avoid
        # requiring a unique constraint on (asset1_symbol, asset2_symbol, test_date, granularity).
        last_error = None
        existing_id = existing_check.data[0]["id"] if (existing_check and existing_check.data) else None
        for attempt in range(max_retries):
            try:
                logger.debug(f"Store attempt {attempt + 1}/{max_retries} (existing_id={existing_id})")

                if not supabase:
                    raise HTTPException(status_code=503, detail="Database unavailable")

                if existing_id:
                    # UPDATE the existing record by primary key
                    response = (
                        supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
                        .update(result_dict)
                        .eq("id", existing_id)
                        .execute()
                    )
                else:
                    # INSERT new record
                    response = (
                        supabase.client.table("cointegration_scores")  # type: ignore[union-attr]
                        .insert(result_dict)
                        .execute()
                    )

                # Validate response
                if response.data and len(response.data) > 0:
                    test_id = response.data[0]["id"]
                    logger.info(f"✅ Successfully stored test result (ID: {test_id})")
                    return test_id
                elif existing_id and response is not None:
                    # UPDATE returns empty data on success in some clients
                    logger.info(f"✅ Successfully updated test result (ID: {existing_id})")
                    return str(existing_id)
                else:
                    raise Exception("Store operation returned no data")

            except Exception as upsert_error:
                last_error = upsert_error
                logger.warning(f"Upsert attempt {attempt + 1} failed: {upsert_error}")

                # Exponential backoff: 1s, 2s, 4s
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} upsert attempts failed")

        # STEP 3: Fallback - if store failed but test exists, return existing ID
        if existing_id:
            logger.warning(
                f"Store failed but test exists, returning existing ID: {existing_id}"
            )
            return str(existing_id)

        # STEP 4: All attempts failed
        error_msg = (
            f"Failed to store test result after {max_retries} attempts: {last_error}"
        )
        logger.error(error_msg)
        raise Exception(error_msg)

    except Exception as e:
        logger.error(f"Error in _store_test_result: {e}", exc_info=True)
        raise
