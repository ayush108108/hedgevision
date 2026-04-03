"""
Metrics Router - Rolling Financial Metrics API

Exposes pre-computed rolling metrics from the rolling_metrics table.
Supports both SQLite and Supabase backends.
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from api.utils.error_handlers import DatabaseError, ValidationError
from api.utils.supabase_client import get_supabase_client
from api.utils.config import config
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


class RollingMetric(BaseModel):
    """Rolling metric response model."""

    id: int
    asset_id: int
    asset_symbol: Optional[str] = None
    benchmark_id: Optional[int] = None
    benchmark_symbol: Optional[str] = None
    window_days: int
    start_date: str
    end_date: str
    rolling_beta: Optional[float] = None
    rolling_volatility: Optional[float] = None
    rolling_sharpe: Optional[float] = None
    rolling_sortino: Optional[float] = None
    max_drawdown: Optional[float] = None
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    hurst_exponent: Optional[float] = None
    alpha: Optional[float] = None
    treynor: Optional[float] = None
    information_ratio: Optional[float] = None
    data_quality: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None


class RollingMetricsResponse(BaseModel):
    """Response model for rolling metrics."""

    status: str
    asset_symbol: str
    metrics: List[RollingMetric]
    windows_available: List[int]
    count: int


def _get_rolling_metrics_sqlite(
    symbol: str,
    window: Optional[int] = None,
    benchmark: Optional[str] = None,
) -> RollingMetricsResponse:
    """Get rolling metrics from SQLite database."""
    db_path = config.get("DB_PATH")
    
    try:
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get asset ID
            cursor.execute("SELECT id FROM assets WHERE symbol = ?", (symbol,))
            asset_row = cursor.fetchone()
            if not asset_row:
                raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")
            
            asset_id = asset_row["id"]
            
            # Get benchmark ID if specified
            benchmark_id = None
            if benchmark:
                cursor.execute("SELECT id FROM assets WHERE symbol = ?", (benchmark,))
                bench_row = cursor.fetchone()
                if bench_row:
                    benchmark_id = bench_row["id"]
            
            # Build query
            query = """
                SELECT 
                    rm.*,
                    a.symbol as asset_symbol,
                    b.symbol as benchmark_symbol
                FROM rolling_metrics rm
                JOIN assets a ON rm.asset_id = a.id
                LEFT JOIN assets b ON rm.benchmark_id = b.id
                WHERE rm.asset_id = ?
            """
            params: List[Any] = [asset_id]
            
            if benchmark_id is not None:
                query += " AND rm.benchmark_id = ?"
                params.append(benchmark_id)
            
            if window is not None:
                # Validate window
                valid_windows = [30, 60, 90, 180, 252]
                if window not in valid_windows:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid window {window}. Must be one of: {valid_windows}"
                    )
                query += " AND rm.window_days = ?"
                params.append(window)
            
            query += " ORDER BY rm.end_date DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return RollingMetricsResponse(
                    status="success",
                    asset_symbol=symbol,
                    metrics=[],
                    windows_available=[],
                    count=0,
                )
            
            # Convert rows to metrics
            metrics = []
            for row in rows:
                metric = RollingMetric(
                    id=row["id"],
                    asset_id=row["asset_id"],
                    asset_symbol=row["asset_symbol"],
                    benchmark_id=row["benchmark_id"],
                    benchmark_symbol=row["benchmark_symbol"],
                    window_days=row["window_days"],
                    start_date=row["start_date"],
                    end_date=row["end_date"],
                    rolling_beta=row["rolling_beta"],
                    rolling_volatility=row["rolling_volatility"],
                    rolling_sharpe=row["rolling_sharpe"],
                    rolling_sortino=row["rolling_sortino"],
                    max_drawdown=row["max_drawdown"],
                    var_95=row["var_95"],
                    cvar_95=row["cvar_95"],
                    hurst_exponent=row["hurst_exponent"],
                    alpha=row["alpha"],
                    treynor=row["treynor"],
                    information_ratio=row["information_ratio"],
                    data_quality=row["data_quality"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                metrics.append(metric)
            
            # Get unique windows available
            windows_available = sorted(list(set(m.window_days for m in metrics)))
            
            return RollingMetricsResponse(
                status="success",
                asset_symbol=symbol,
                metrics=metrics,
                windows_available=windows_available,
                count=len(metrics),
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rolling metrics from SQLite for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve rolling metrics: {str(e)}"
        )


@router.get("/rolling/{symbol}", response_model=RollingMetricsResponse)
async def get_rolling_metrics(
    symbol: str,
    window: Optional[int] = Query(
        None, description="Specific window (30, 60, 90, 180, 252)"
    ),
    benchmark: Optional[str] = Query(
        "SPY.US", description="Benchmark symbol (e.g. SPY.US, GLD.US, BTC-USD.CC)"
    ),
) -> RollingMetricsResponse:
    """
    Get rolling financial metrics for an asset.

    Returns pre-computed rolling metrics including:
    - Rolling Beta vs benchmark
    - Rolling Volatility (annualized)
    - Sharpe Ratio
    - Sortino Ratio
    - Maximum Drawdown
    - VaR and CVaR (95%)
    - Hurst Exponent
    - Alpha, Treynor, Information Ratio

    Args:
        symbol: Asset symbol (e.g., 'AAPL.US')
        window: Specific window in days (30, 60, 90, 180, 252). If None, returns all windows.
        benchmark: Benchmark symbol for beta calculation (default: SPY.US)

    Returns:
        Rolling metrics data

    Example:
        GET /api/metrics/rolling/AAPL.US?window=252&benchmark=SPY.US
    """
    # Check which backend to use
    data_backend = config.get("DATA_BACKEND", "sqlite")
    
    # Use SQLite if configured or if Supabase is not available
    if data_backend == "sqlite":
        return _get_rolling_metrics_sqlite(symbol, window, benchmark)
    
    # Otherwise use Supabase
    try:
        supabase = get_supabase_client()
        if not supabase:
            # Fall back to SQLite if Supabase is not available
            logger.warning("Supabase not available, falling back to SQLite")
            return _get_rolling_metrics_sqlite(symbol, window, benchmark)

        # Get asset ID from symbol
        asset_response = (
            supabase.client.table("assets")
            .select("id")
            .eq("symbol", symbol)
            .single()
            .execute()
        )

        if not asset_response.data:
            raise HTTPException(status_code=404, detail=f"Asset {symbol} not found")

        asset_id = asset_response.data["id"]

        # Get benchmark ID if specified
        benchmark_id = None
        if benchmark:
            benchmark_response = (
                supabase.client.table("assets")
                .select("id")
                .eq("symbol", benchmark)
                .single()
                .execute()
            )

            if benchmark_response.data:
                benchmark_id = benchmark_response.data["id"]

        # Build query for rolling metrics
        query = (
            supabase.client.table("rolling_metrics")
            .select(
                "*, assets!rolling_metrics_asset_id_fkey(symbol), benchmark:assets!rolling_metrics_benchmark_id_fkey(symbol)"
            )
            .eq("asset_id", asset_id)
        )

        if benchmark_id:
            query = query.eq("benchmark_id", benchmark_id)

        if window:
            # Validate window value
            valid_windows = [30, 60, 90, 180, 252]
            if window not in valid_windows:
                raise ValidationError(
                    f"Invalid window {window}. Must be one of: {valid_windows}"
                )
            query = query.eq("window_days", window)

        # Order by end_date descending to get latest first
        query = query.order("end_date", desc=True)

        response = query.execute()

        if not response.data:
            return RollingMetricsResponse(
                status="success",
                asset_symbol=symbol,
                metrics=[],
                windows_available=[],
                count=0,
            )

        # Get unique windows available
        windows_available = sorted(list(set(m["window_days"] for m in response.data)))

        # Transform response data
        metrics = []
        for item in response.data:
            metric = RollingMetric(
                id=item["id"],
                asset_id=item["asset_id"],
                asset_symbol=symbol,
                benchmark_id=item.get("benchmark_id"),
                benchmark_symbol=(
                    item.get("benchmark", {}).get("symbol")
                    if item.get("benchmark")
                    else None
                ),
                window_days=item["window_days"],
                start_date=item["start_date"],
                end_date=item["end_date"],
                rolling_beta=item.get("rolling_beta"),
                rolling_volatility=item.get("rolling_volatility"),
                rolling_sharpe=item.get("rolling_sharpe_ratio"),  # DB col is rolling_sharpe_ratio
                rolling_sortino=item.get("rolling_sortino"),
                max_drawdown=item.get("max_drawdown"),
                var_95=item.get("var_95"),
                cvar_95=item.get("cvar_95"),
                hurst_exponent=item.get("hurst_exponent"),
                alpha=item.get("alpha"),
                treynor=item.get("treynor"),
                information_ratio=item.get("information_ratio"),
                data_quality=item.get("data_quality"),
                created_at=item["created_at"],
                updated_at=item.get("updated_at"),
            )
            metrics.append(metric)

        return RollingMetricsResponse(
            status="success",
            asset_symbol=symbol,
            metrics=metrics,
            windows_available=windows_available,
            count=len(metrics),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rolling metrics for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve rolling metrics: {str(e)}"
        )


@router.get("/rolling", response_model=Dict[str, Any])
async def get_latest_rolling_metrics(
    limit: int = Query(50, ge=1, le=100, description="Number of assets to return"),
    window: int = Query(252, description="Rolling window (30, 60, 90, 180, 252)"),
    benchmark: str = Query("SPY.US", description="Benchmark symbol (e.g. SPY.US, GLD.US)"),
    order_by: str = Query("rolling_sharpe_ratio", description="Metric to sort by (use DB column name)"),
    ascending: bool = Query(False, description="Sort direction"),
) -> Dict[str, Any]:
    """
    Get latest rolling metrics for multiple assets.

    Useful for screening/filtering assets by rolling metrics.

    Args:
        limit: Number of assets to return (1-100)
        window: Rolling window in days
        benchmark: Benchmark symbol
        order_by: Metric to sort by (e.g., 'rolling_sharpe', 'rolling_beta')
        ascending: Sort direction (False = descending)

    Returns:
        List of latest rolling metrics for multiple assets

    Example:
        GET /api/metrics/rolling?window=252&order_by=rolling_sharpe&ascending=false&limit=20
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return {
                "status": "unavailable",
                "window": window,
                "benchmark": benchmark,
                "order_by": order_by,
                "metrics": [],
                "count": 0,
            }

        # Validate window
        valid_windows = [30, 60, 90, 180, 252]
        if window not in valid_windows:
            raise ValidationError(
                f"Invalid window {window}. Must be one of: {valid_windows}"
            )

        # Get benchmark ID
        benchmark_response = (
            supabase.client.table("assets")
            .select("id")
            .eq("symbol", benchmark)
            .single()
            .execute()
        )

        benchmark_id = (
            benchmark_response.data["id"] if benchmark_response.data else None
        )

        # Build query
        query = (
            supabase.client.table("rolling_metrics")
            .select("*, assets!rolling_metrics_asset_id_fkey(symbol, name, exchange)")
            .eq("window_days", window)
        )

        if benchmark_id:
            query = query.eq("benchmark_id", benchmark_id)

        # Order by specified metric
        query = query.order(order_by, desc=not ascending).limit(limit)

        response = query.execute()

        return {
            "status": "success",
            "window": window,
            "benchmark": benchmark,
            "order_by": order_by,
            "count": len(response.data) if response.data else 0,
            "metrics": response.data if response.data else [],
        }

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error getting latest rolling metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve rolling metrics: {str(e)}"
        )
