"""API endpoints for backtesting pair trading strategies."""

import logging
from typing import Any, Dict, Optional

from api.utils.auth_middleware import AuthUser, get_authenticated_user
from api.utils.cache_adapter import get_cache_adapter
from api.utils.config import config
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/backtest", tags=["backtest"], responses={404: {"description": "Not found"}}
)

cache = get_cache_adapter(default_ttl=config["REDIS_TTL"])


class BacktestRequest(BaseModel):
    symbol1: str = Field(..., description="First symbol in the pair")
    symbol2: str = Field(..., description="Second symbol in the pair")
    lookback_days: int = Field(365, gt=0, description="Lookback period in days")
    initial_capital: float = Field(
        10_000.0, gt=0, description="Initial capital for the backtest"
    )
    position_size: float = Field(0.1, gt=0, description="Position size multiplier")
    transaction_cost: float = Field(
        0.001, ge=0, description="Per-trade transaction cost"
    )
    slippage: float = Field(0.0005, ge=0, description="Slippage assumption")
    entry_threshold: float = Field(2.0, gt=0, description="Z-score entry threshold")
    exit_threshold: float = Field(0.5, ge=0, description="Z-score exit threshold")
    stop_loss_threshold: float = Field(
        3.0, gt=0, description="Z-score stop loss threshold"
    )
    max_holding_period: Optional[int] = Field(
        30, gt=0, description="Maximum holding period in bars"
    )
    granularity: str = Field("daily", description="Data frequency (daily|hourly)")

    @validator("symbol1", "symbol2")
    def _validate_symbol(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Symbol must be provided")
        return value

    class Config:
        extra = "allow"


class ParameterRange(BaseModel):
    min: float
    max: float
    step: float = Field(..., gt=0)

    @validator("max")
    def _validate_bounds(cls, value: float, values: Dict[str, Any]) -> float:
        if "min" in values and value <= values["min"]:
            raise ValueError("Parameter max must be greater than min")
        return value


class OptimizationRequest(BaseModel):
    symbol1: str
    symbol2: str
    parameters: Dict[str, ParameterRange]
    objective: Optional[str] = Field(default="sharpe_ratio")
    lookback_days: Optional[int] = Field(default=365, gt=0)
    granularity: Optional[str] = Field(default="daily")

    @validator("symbol1", "symbol2")
    def _validate_symbol(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Symbol must be provided")
        return value

    class Config:
        extra = "allow"


@router.post("/run")
async def run_backtest(
    request: BacktestRequest, current_user: AuthUser = Depends(get_authenticated_user)
):
    """
    Run a synchronous backtest for a pair.

    This endpoint executes the backtest immediately and returns results.
    For long-running backtests, use the /async endpoint instead.

    Requires authentication with 'run_basic_backtests' permission.
    """
    # Check permission
    if not current_user.has_permission("run_basic_backtests"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to run backtests",
        )
    try:
        from datetime import datetime, timedelta

        from api.services.analytics_service import AnalyticsService
        from api.services.backtest_engine import BacktestConfig, PairBacktester

        # Calculate date range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=request.lookback_days)

        # Get pair analysis using analytics service
        analytics_service = AnalyticsService()
        
        pair_report = await analytics_service.get_full_pair_report(
            asset1=request.symbol1,
            asset2=request.symbol2,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            granularity=request.granularity,
            lookback_days=request.lookback_days,
            use_precomputed=False,  # Force fresh computation for backtesting
            include_price_data=True,
            include_spread_data=True,
        )

        if not pair_report or not pair_report.get("spread_data"):
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data for pair {request.symbol1}/{request.symbol2}",
            )

        # Extract spread and z-score series from pair report
        import pandas as pd

        spread_data = pair_report.get("spread_data", [])
        if not spread_data:
            raise HTTPException(
                status_code=400,
                detail="No spread data available for backtesting",
            )
        
        # Convert spread data to DataFrame
        spread_df = pd.DataFrame(spread_data)
        if "date" in spread_df.columns:
            spread_df["Date"] = pd.to_datetime(spread_df["date"])
        
        spread_series: pd.Series = spread_df.set_index("Date")["spread"].dropna()
        zscore_series: pd.Series = spread_df.set_index("Date")["zscore"].dropna()

        if len(spread_series) < 30:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data points (<30) for reliable backtest",
            )

        # Configure and run backtest
        cfg = BacktestConfig(
            initial_capital=request.initial_capital,
            position_size=request.position_size,
            transaction_cost=request.transaction_cost,
            slippage=request.slippage,
            entry_threshold=request.entry_threshold,
            exit_threshold=request.exit_threshold,
            stop_loss_threshold=request.stop_loss_threshold,
            max_holding_period=request.max_holding_period,
        )

        backtester = PairBacktester(cfg)
        results = backtester.run_backtest(
            spread_series=spread_series,
            zscore_series=zscore_series,
            asset1_name=request.symbol1,
            asset2_name=request.symbol2,
        )

        logger.info(
            f"Backtest completed for {request.symbol1}/{request.symbol2}: "
            f"{results['metrics']['trade_count']} trades, "
            f"return: {results['metrics']['total_return']:.2%}"
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/config/default")
async def get_default_config():
    """
    Get the default backtest configuration parameters.

    Returns recommended starting values for backtesting parameters.
    """
    from api.services.backtest_engine import BacktestConfig

    default_config = BacktestConfig()

    return {
        "initial_capital": default_config.initial_capital,
        "position_size": default_config.position_size,
        "transaction_cost": default_config.transaction_cost,
        "slippage": default_config.slippage,
        "entry_threshold": default_config.entry_threshold,
        "exit_threshold": default_config.exit_threshold,
        "stop_loss_threshold": default_config.stop_loss_threshold,
        "max_holding_period": default_config.max_holding_period,
        "lookback_days": 365,
        "granularity": "daily",
    }


@router.post("/config/validate")
async def validate_config(request: BacktestRequest):
    """
    Validate backtest configuration parameters.

    Checks if the provided parameters are within acceptable ranges
    and flags potential issues.
    """
    warnings = []
    errors = []

    # Validate thresholds
    if request.entry_threshold <= request.exit_threshold:
        errors.append("entry_threshold must be greater than exit_threshold")

    if request.stop_loss_threshold <= request.entry_threshold:
        warnings.append(
            "stop_loss_threshold should typically be greater than entry_threshold"
        )

    # Validate costs
    if request.transaction_cost + request.slippage > 0.01:
        warnings.append(
            "Combined transaction costs exceed 1% - results may be overly pessimistic"
        )

    # Validate position sizing
    if request.position_size > request.initial_capital * 0.5:
        warnings.append("Position size exceeds 50% of capital - high risk")

    # Validate lookback period
    if request.lookback_days < 90:
        warnings.append("Lookback period < 90 days may not provide reliable results")

    if request.lookback_days > 730:
        warnings.append("Lookback period > 2 years may include outdated market regimes")

    # Validate holding period
    if request.max_holding_period and request.max_holding_period < 5:
        warnings.append("Very short max_holding_period may force exits prematurely")

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "config": request.dict(),
    }


# NOTE: Parameter optimization endpoint removed in production rigor cleanup.
# Stub implementation was misleading. Will be re-implemented properly in v2.1.0
# with scikit-learn GridSearchCV or similar production-grade optimization.
# For now, use /run endpoint with manual parameter testing.
