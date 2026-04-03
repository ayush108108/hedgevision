"""Pair screener endpoints that query pre-computed results via dedicated services."""

import logging
import sqlite3
from typing import Any, Dict, List, Literal, Optional

from api.services import analytics_service
from api.utils.config import config
from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screener", tags=["screener"])

ASSET_PATH_REGEX = r"^[A-Za-z0-9\.\-]+$"


class UnifiedScreenerPair(BaseModel):
    model_config = ConfigDict(extra="allow")
    """
    Unified model for screened pairs across correlation and cointegration methods.

    This model provides a consistent interface for the frontend to consume
    screening results from different sources (correlation matrix, cointegration tests).
    """

    # Asset identifiers
    asset1: str = Field(..., description="First asset symbol")
    asset2: str = Field(..., description="Second asset symbol")

    # Screening metadata
    screener_type: Literal["correlation", "cointegration"] = Field(
        ..., description="Type of screening method used"
    )

    # Primary metric (main ranking criterion)
    primary_metric_name: str = Field(
        ...,
        description="Name of primary metric (e.g., 'Correlation', 'Cointegration Score')",
    )
    primary_metric_value: float = Field(..., description="Value of primary metric")

    # Optional secondary metric
    secondary_metric_name: Optional[str] = Field(
        None, description="Name of secondary metric"
    )
    secondary_metric_value: Optional[float] = Field(
        None, description="Value of secondary metric"
    )

    # Additional metadata
    is_cointegrated: Optional[bool] = Field(
        None, description="Whether pair is cointegrated (for cointegration screener)"
    )
    last_updated: Optional[str] = Field(
        None, description="ISO timestamp of last computation"
    )


class ScreenerPair(BaseModel):
    """Model for a screened pair with metadata."""

    asset1: str
    asset1_symbol: str
    asset2: str
    asset2_symbol: str
    correlation: float
    abs_correlation: float
    last_updated: Optional[str] = Field(
        None, description="ISO timestamp of last computation"
    )


class DetailedPairAnalysis(BaseModel):
    """Model for detailed pair analysis results."""

    asset1: str
    asset2: str
    correlation: Optional[float] = None
    volatility_ratio: Optional[float] = None
    hedge_ratio: Optional[float] = None
    r_squared: Optional[float] = None
    is_cointegrated: Optional[bool] = None
    cointegration_p_value: Optional[float] = None
    half_life: Optional[float] = None
    sample_size: Optional[int] = None
    last_updated: Optional[str] = None


class ScreenerResponse(BaseModel):
    """Response model for screener results."""

    pairs: List[ScreenerPair]
    total_pairs: int
    data_age_hours: float
    cache_status: str
    granularity: str
    method: str


class UnifiedScreenerResponse(BaseModel):
    """Unified response model for all screener types."""

    pairs: List[UnifiedScreenerPair]
    total_pairs: int
    screener_type: Literal["correlation", "cointegration"]
    data_age_hours: float
    cache_status: str
    granularity: str
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters that were applied to generate this result set",
    )


class ScreenerStatus(BaseModel):
    """Status of the screening system."""

    model_config = ConfigDict(extra="allow")

    supabase_available: bool
    correlation_matrix_age_hours: Optional[float] = None
    top_pairs_age_hours: Optional[float] = None
    detailed_analysis_count: Optional[int] = None
    last_precomputation: Optional[str] = None


class PrecomputationRequest(BaseModel):
    """Optional request body for triggering pre-computation."""

    granularity: Literal["daily", "hourly"] = "daily"
    method: Literal["spearman", "pearson"] = "spearman"
    force: bool = False


# DELETED: Redundant with /api/screener/correlation/top-pairs
# Use correlation/top-pairs instead


@router.get("/correlation/top-pairs", response_model=UnifiedScreenerResponse)
async def get_correlation_screener_pairs(
    min_correlation: float = Query(
        0.7, ge=0.0, le=1.0, description="Minimum absolute correlation"
    ),
    limit: int = Query(
        10, ge=1, le=200, description="Maximum number of pairs to return"
    ),
    granularity: Literal["daily", "hourly"] = Query(
        "daily", description="Data granularity"
    ),
    method: Literal["spearman", "pearson"] = Query(
        "spearman", description="Correlation method"
    ),
    max_age_hours: int = Query(24, description="Maximum age of cached data in hours"),
) -> UnifiedScreenerResponse:
    """
    Get top correlated pairs. Canonical endpoint for correlation screening.
    Returns unified format compatible across all screener types.
    """

    try:
        service_payload = analytics_service.get_screener_top_pairs(
            min_correlation=min_correlation,
            limit=limit,
            granularity=granularity,
            method=method,
            max_age_hours=max_age_hours,
        )

        raw_pairs = service_payload.get("pairs", [])
        unified_pairs: List[UnifiedScreenerPair] = []

        for pair in raw_pairs:
            correlation = pair.get("correlation", 0.0)
            unified_pairs.append(
                UnifiedScreenerPair(
                    asset1=pair["asset1"],
                    asset2=pair["asset2"],
                    screener_type="correlation",
                    primary_metric_name="Correlation",
                    primary_metric_value=abs(correlation),
                    secondary_metric_name="Raw Correlation",
                    secondary_metric_value=correlation,
                    is_cointegrated=False,  # Correlation screener doesn't test cointegration
                    last_updated=pair.get("last_updated"),
                )
            )

        logger.info(
            "Retrieved %s unified screened pairs (%s/%s)",
            len(unified_pairs),
            granularity,
            method,
        )

        return UnifiedScreenerResponse(
            pairs=unified_pairs[:limit],
            total_pairs=service_payload.get("total_pairs", len(unified_pairs)),
            screener_type="correlation",
            data_age_hours=service_payload.get("data_age_hours", 0.0),
            cache_status=service_payload.get("cache_status", "unknown"),
            granularity=service_payload.get("granularity", granularity),
            filters_applied={
                "min_correlation": min_correlation,
                "method": method,
                "max_age_hours": max_age_hours,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving unified screened pairs: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve screened pairs: {str(e)}"
        )


# NOTE: /pair-analysis/{asset1}/{asset2} removed - use /api/pair-analysis?asset1=X&asset2=Y
# Provides more comprehensive analysis with flexible params (start_date, end_date, etc.)


@router.get("/status", response_model=ScreenerStatus)
async def get_screener_status() -> ScreenerStatus:
    """Get the current status of the screening system."""

    try:
        status_payload = analytics_service.get_screener_status()
        return ScreenerStatus(**status_payload)

    except Exception as e:
        logger.error(f"Error getting screener status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get screener status: {str(e)}"
        )


@router.post("/trigger-precomputation")
async def trigger_precomputation(
    payload: Optional[PrecomputationRequest] = Body(
        None,
        description="Optional request body overriding query parameters",
    ),
    granularity: Optional[Literal["daily", "hourly"]] = Query(
        None, description="Data granularity"
    ),
    method: Optional[Literal["spearman", "pearson"]] = Query(
        None, description="Correlation method"
    ),
    force: Optional[bool] = Query(
        None, description="Force recomputation even if recent data exists"
    ),
) -> Dict[str, Any]:
    """Manually trigger pre-computation tasks."""

    try:
        request_data = (
            payload.model_dump() if payload else PrecomputationRequest().model_dump()
        )

        if granularity is not None:
            request_data["granularity"] = granularity
        if method is not None:
            request_data["method"] = method
        if force is not None:
            request_data["force"] = force

        response_payload = analytics_service.trigger_precomputation(**request_data)
        logger.info(
            "Triggered pre-computation via service for %s/%s (force=%s)",
            request_data["granularity"],
            request_data["method"],
            request_data.get("force"),
        )

        return response_payload

    except Exception as e:
        logger.error(f"Error triggering pre-computation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to trigger pre-computation: {str(e)}"
        )


@router.get("/cointegration/top-pairs", response_model=UnifiedScreenerResponse)
async def get_cointegration_screener_pairs(
    limit: int = Query(10, ge=1, le=100, description="Number of pairs"),
    granularity: str = Query("daily", description="Data granularity"),
    min_score: float = Query(
        60.0, ge=0.0, le=100.0, description="Minimum overall score"
    ),
) -> UnifiedScreenerResponse:
    """
    Get top cointegrated pairs. Canonical endpoint for cointegration screening.
    Returns unified format compatible across all screener types.
    """
    from api.utils.supabase_client import get_supabase_client

    try:
        supabase = get_supabase_client()
        if supabase is None:
            db_path = str(config.get("DB_PATH", "backend/prices.db"))
            try:
                with sqlite3.connect(db_path, timeout=5.0) as conn:
                    conn.row_factory = sqlite3.Row
                    rows = conn.execute(
                        """
                        SELECT asset1_symbol, asset2_symbol, test_date, overall_score,
                               eg_pvalue, eg_is_cointegrated, beta_coefficient,
                               half_life_days, sharpe_ratio
                        FROM cointegration_scores
                        WHERE granularity = ? AND overall_score >= ?
                        ORDER BY overall_score DESC
                        LIMIT ?
                        """,
                        (granularity, min_score, limit),
                    ).fetchall()
            except sqlite3.OperationalError:
                rows = []

            unified_pairs: List[UnifiedScreenerPair] = []
            for row in rows:
                primary_value = float(row["overall_score"] or 0.0)
                half_life = float(row["half_life_days"] or 0.0)
                pvalue = float(row["eg_pvalue"] or 1.0)

                if primary_value >= 85:
                    strength = "strong"
                elif primary_value >= 70:
                    strength = "moderate"
                else:
                    strength = "weak"

                if primary_value >= 85 and 2 <= half_life <= 10:
                    suitability = "excellent"
                elif primary_value >= 70:
                    suitability = "good"
                elif primary_value >= 60:
                    suitability = "fair"
                else:
                    suitability = "poor"

                if pvalue < 0.01 and half_life < 15:
                    risk = "low"
                elif pvalue < 0.05:
                    risk = "medium"
                else:
                    risk = "high"

                item = UnifiedScreenerPair(
                    asset1=str(row["asset1_symbol"]),
                    asset2=str(row["asset2_symbol"]),
                    screener_type="cointegration",
                    primary_metric_name="Cointegration Score",
                    primary_metric_value=primary_value,
                    secondary_metric_name=None,
                    secondary_metric_value=None,
                    is_cointegrated=bool(row["eg_is_cointegrated"]),
                    last_updated=str(row["test_date"]),
                )
                try:
                    setattr(item, "asset1_symbol", str(row["asset1_symbol"]))
                    setattr(item, "asset2_symbol", str(row["asset2_symbol"]))
                    setattr(item, "overall_score", primary_value)
                    setattr(item, "cointegration_strength", strength)
                    setattr(item, "trading_suitability", suitability)
                    setattr(item, "risk_level", risk)
                    setattr(item, "eg_pvalue", pvalue)
                    setattr(item, "eg_is_cointegrated", bool(row["eg_is_cointegrated"]))
                    setattr(item, "beta_coefficient", row["beta_coefficient"])
                    setattr(item, "half_life_days", half_life)
                    setattr(item, "sharpe_ratio", row["sharpe_ratio"])
                    setattr(item, "test_date", str(row["test_date"]))
                except Exception:
                    pass
                unified_pairs.append(item)

            return UnifiedScreenerResponse(
                pairs=unified_pairs,
                total_pairs=len(unified_pairs),
                screener_type="cointegration",
                data_age_hours=0.0,
                cache_status="sqlite",
                granularity=granularity,
                filters_applied={"min_score": min_score},
            )

        response = supabase.client.rpc(
            "get_top_cointegrated_pairs",
            {"limit_count": limit, "granularity_filter": granularity, "min_score": min_score},
        ).execute()

        # Convert to unified format
        unified_pairs: List[UnifiedScreenerPair] = []
        for pair in (response.data or []):
            # RPC payloads can vary between environments. Support common field variants.
            asset1 = (
                pair.get("asset1")
                or pair.get("asset1_symbol")
                or pair.get("symbol1")
                or pair.get("asset_a")
            )
            asset2 = (
                pair.get("asset2")
                or pair.get("asset2_symbol")
                or pair.get("symbol2")
                or pair.get("asset_b")
            )

            # Skip malformed rows defensively rather than 500-ing
            if not asset1 or not asset2:
                logger.warning("Skipping malformed cointegration row: %s", pair)
                continue

            # Get overall_score and compute derived fields
            primary_value = pair.get("overall_score", 0.0)
            
            # Compute cointegration_strength from score if not provided
            if primary_value >= 85:
                strength = "strong"
            elif primary_value >= 70:
                strength = "moderate"
            else:
                strength = "weak"
            
            # Compute trading_suitability from score and half-life
            half_life = pair.get("half_life_days", 0)
            if primary_value >= 85 and 2 <= half_life <= 10:
                suitability = "excellent"
            elif primary_value >= 70:
                suitability = "good"
            elif primary_value >= 60:
                suitability = "fair"
            else:
                suitability = "poor"
            
            # Compute risk_level from p-value and half-life
            pvalue = pair.get("eg_pvalue", 1.0)
            if pvalue < 0.01 and half_life < 15:
                risk = "low"
            elif pvalue < 0.05:
                risk = "medium"
            else:
                risk = "high"

            last_updated = (
                pair.get("last_updated")
                or pair.get("test_date")
                or pair.get("updated_at")
            )

            item = UnifiedScreenerPair(
                asset1=asset1,
                asset2=asset2,
                screener_type="cointegration",
                primary_metric_name="Cointegration Score",
                primary_metric_value=float(primary_value) if primary_value is not None else 0.0,
                # Secondary metric fields are optional in the model
                secondary_metric_name=None,
                secondary_metric_value=None,
                is_cointegrated=pair.get("is_cointegrated"),
                last_updated=last_updated,
            )

            # --- pass-through fields for UI compatibility (best-effort) ---
            try:
                setattr(item, "asset1_symbol", asset1)
                setattr(item, "asset2_symbol", asset2)
                # Add overall_score as alias for primary_metric_value
                setattr(item, "overall_score", primary_value)
                # Add computed fields
                setattr(item, "cointegration_strength", strength)
                setattr(item, "trading_suitability", suitability)
                setattr(item, "risk_level", risk)
                # Add other fields from database
                for k_src, v in {
                    # cointegration_pvalue is the raw pair_trades column name;
                    # eg_pvalue / p_value are aliases used by other sources
                    "eg_pvalue": (
                        pair.get("eg_pvalue")
                        or pair.get("p_value")
                        or pair.get("cointegration_pvalue")
                    ),
                    "eg_is_cointegrated": pair.get("eg_is_cointegrated") or pair.get("is_cointegrated"),
                    "beta_coefficient": pair.get("beta_coefficient"),
                    "half_life_days": pair.get("half_life_days"),
                    "sharpe_ratio": pair.get("sharpe_ratio") or 0.0,
                    "test_date": last_updated,
                    "pearson_correlation": pair.get("pearson_correlation"),
                }.items():
                    if v is not None:
                        setattr(item, k_src, v)
            except Exception:
                # Ignore pass-through failures; core fields above are sufficient
                pass

            # Only include pairs that have at least a meaningful score
            if primary_value and float(primary_value) > 0:
                unified_pairs.append(item)

        # Sort highest tradability score first
        unified_pairs.sort(key=lambda p: p.primary_metric_value, reverse=True)

        return UnifiedScreenerResponse(
            pairs=unified_pairs,
            total_pairs=len(unified_pairs),
            screener_type="cointegration",
            data_age_hours=0.0,
            cache_status="database",
            granularity=granularity,
            filters_applied={"min_score": min_score},
        )
    except Exception as e:
        logger.error(f"Error retrieving cointegration pairs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache")
async def clear_precomputed_cache() -> Dict[str, Any]:
    """Clear old pre-computed data from Supabase."""

    try:
        response_payload = analytics_service.clear_screener_cache()
        logger.info("Triggered screener cache cleanup via service")
        return response_payload

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
