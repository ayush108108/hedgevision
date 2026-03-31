"""
Portfolio API Router

Endpoints for managing user portfolios and positions.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from api.services.portfolio_service import get_portfolio_service, Position, PortfolioMetrics
from api.services.standardization_service import get_standardization_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# Request/Response models
class CreatePositionRequest(BaseModel):
    """Request to create a new position."""

    pair: str = Field(..., description="Trading pair name (e.g., SPY/QQQ)")
    asset1: str = Field(..., description="First asset symbol")
    asset2: str = Field(..., description="Second asset symbol")
    type: str = Field(..., description="Position type: 'long-short' or 'short-long'")
    entry_spread: float = Field(..., description="Entry spread value")
    position_size: float = Field(..., description="Position size in USD", gt=0)
    hedge_ratio: float = Field(1.0, description="Hedge ratio between assets")
    entry_zscore: Optional[float] = Field(None, description="Entry z-score")
    stop_loss: Optional[float] = Field(None, description="Stop loss level")
    take_profit: Optional[float] = Field(None, description="Take profit level")
    notes: Optional[str] = Field(None, description="Optional notes")


class UpdateSpreadRequest(BaseModel):
    """Request to update position spread."""

    current_spread: float = Field(..., description="Current spread value")


class ClosePositionRequest(BaseModel):
    """Request to close a position."""

    exit_spread: float = Field(..., description="Exit spread value")
    notes: Optional[str] = Field(None, description="Optional closing notes")


class PositionResponse(BaseModel):
    """Position response model."""

    id: str
    user_id: str
    pair: str
    asset1: str
    asset2: str
    type: str
    entry_date: str
    entry_spread: float
    current_spread: float
    position_size: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    status: str
    exit_date: Optional[str] = None
    exit_spread: Optional[float] = None
    realized_pnl: Optional[float] = None
    hedge_ratio: float = 1.0
    entry_zscore: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    notes: Optional[str] = None


class PortfolioMetricsResponse(BaseModel):
    """Portfolio metrics response."""

    total_value: float
    cash_balance: float
    invested_capital: float
    total_pnl: float
    total_pnl_percent: float
    number_of_positions: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0


# Dependency to get user_id (replace with actual auth later)
async def get_current_user_id() -> str:
    """Get current user ID (mock for now)."""
    # TODO: Implement actual authentication
    return "demo_user"


@router.post("/positions", response_model=PositionResponse)
async def create_position(
    request: CreatePositionRequest, user_id: str = Depends(get_current_user_id)
):
    """
    Create a new trading position.

    Args:
        request: Position creation request
        user_id: Current user ID

    Returns:
        Created position
    """
    try:
        portfolio_service = get_portfolio_service()

        position = portfolio_service.create_position(
            user_id=user_id,
            pair=request.pair,
            asset1=request.asset1,
            asset2=request.asset2,
            position_type=request.type,
            entry_spread=request.entry_spread,
            position_size=request.position_size,
            hedge_ratio=request.hedge_ratio,
            entry_zscore=request.entry_zscore,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            notes=request.notes,
        )

        return position.to_dict()

    except Exception as e:
        logger.error(f"Error creating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    status: Optional[str] = Query(None, description="Filter by status: open, pending, closed"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get all positions for the current user.

    Args:
        status: Optional status filter
        user_id: Current user ID

    Returns:
        List of positions
    """
    try:
        portfolio_service = get_portfolio_service()
        positions = portfolio_service.get_user_positions(user_id=user_id, status=status)

        return [p.to_dict() for p in positions]

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str, user_id: str = Depends(get_current_user_id)
):
    """
    Get a specific position by ID.

    Args:
        position_id: Position ID
        user_id: Current user ID

    Returns:
        Position details
    """
    try:
        portfolio_service = get_portfolio_service()
        position = portfolio_service.positions.get(position_id)

        if not position or position.user_id != user_id:
            raise HTTPException(status_code=404, detail="Position not found")

        return position.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}/standardized")
async def get_position_standardized(
    position_id: str, user_id: str = Depends(get_current_user_id)
):
    """
    Return the position along with standardized pair and provider-specific symbols.

    This ensures all flows go through the central StandardizationService.
    """
    try:
        portfolio_service = get_portfolio_service()
        std = get_standardization_service()

        position = portfolio_service.positions.get(position_id)
        if not position or position.user_id != user_id:
            raise HTTPException(status_code=404, detail="Position not found")

        a1 = position.asset1
        a2 = position.asset2
        pair_canonical = std.canonical_pair(a1, a2)

        binance_a1 = std.to_binance(a1)
        binance_a2 = std.to_binance(a2)
        coinglass_a1 = std.to_coinglass(a1)
        coinglass_a2 = std.to_coinglass(a2)
        yfi_a1 = std.to_yfinance(a1)
        yfi_a2 = std.to_yfinance(a2)

        return {
            "position": position.to_dict(),
            "standardized": {
                "pair": pair_canonical,
                "assets": {"asset1": a1, "asset2": a2},
                "providers": {
                    "binance": {"asset1": binance_a1, "asset2": binance_a2},
                    "coinglass": {"asset1": coinglass_a1, "asset2": coinglass_a2},
                    "yfinance": {"asset1": yfi_a1, "asset2": yfi_a2},
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error standardizing position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/positions/{position_id}/spread", response_model=PositionResponse)
async def update_position_spread(
    position_id: str,
    request: UpdateSpreadRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Update a position with current spread value.

    Args:
        position_id: Position ID
        request: Spread update request
        user_id: Current user ID

    Returns:
        Updated position
    """
    try:
        portfolio_service = get_portfolio_service()

        # Verify ownership
        position = portfolio_service.positions.get(position_id)
        if not position or position.user_id != user_id:
            raise HTTPException(status_code=404, detail="Position not found")

        # Update position
        updated = portfolio_service.update_position(
            position_id=position_id, current_spread=request.current_spread
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Position not found")

        return updated.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/{position_id}/close", response_model=PositionResponse)
async def close_position(
    position_id: str,
    request: ClosePositionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Close a trading position.

    Args:
        position_id: Position ID
        request: Close position request
        user_id: Current user ID

    Returns:
        Closed position with final P&L
    """
    try:
        portfolio_service = get_portfolio_service()

        # Verify ownership
        position = portfolio_service.positions.get(position_id)
        if not position or position.user_id != user_id:
            raise HTTPException(status_code=404, detail="Position not found")

        # Close position
        closed = portfolio_service.close_position(
            position_id=position_id,
            exit_spread=request.exit_spread,
            notes=request.notes,
        )

        if not closed:
            raise HTTPException(status_code=404, detail="Position not found")

        return closed.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/positions/{position_id}")
async def delete_position(
    position_id: str, user_id: str = Depends(get_current_user_id)
):
    """
    Delete a position.

    Args:
        position_id: Position ID
        user_id: Current user ID

    Returns:
        Success message
    """
    try:
        portfolio_service = get_portfolio_service()

        # Verify ownership
        position = portfolio_service.positions.get(position_id)
        if not position or position.user_id != user_id:
            raise HTTPException(status_code=404, detail="Position not found")

        # Delete
        deleted = portfolio_service.delete_position(position_id=position_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Position not found")

        return {"message": "Position deleted successfully", "id": position_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting position {position_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=PortfolioMetricsResponse)
async def get_portfolio_metrics(user_id: str = Depends(get_current_user_id)):
    """
    Get portfolio performance metrics.

    Args:
        user_id: Current user ID

    Returns:
        Portfolio metrics including P&L, win rate, Sharpe ratio, etc.
    """
    try:
        portfolio_service = get_portfolio_service()
        metrics = portfolio_service.calculate_portfolio_metrics(user_id=user_id)

        return metrics.to_dict()

    except Exception as e:
        logger.error(f"Error calculating portfolio metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[PositionResponse])
async def get_trade_history(
    limit: int = Query(50, ge=1, le=500, description="Maximum trades to return"),
    user_id: str = Depends(get_current_user_id),
):
    """
    Get trade history (closed positions).

    Args:
        limit: Maximum trades to return
        user_id: Current user ID

    Returns:
        List of closed positions
    """
    try:
        portfolio_service = get_portfolio_service()
        history = portfolio_service.get_trade_history(user_id=user_id, limit=limit)

        return [p.to_dict() for p in history]

    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
