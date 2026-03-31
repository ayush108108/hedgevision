"""
Portfolio Tracking Service

Manages user portfolios including:
- Position tracking (open, pending, closed)
- P&L calculation and performance metrics
- Risk metrics (Sharpe, max drawdown, win rate)
- Position history and trade analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import uuid

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Trading position."""

    id: str
    user_id: str
    pair: str
    asset1: str
    asset2: str
    type: str  # 'long-short' or 'short-long'
    entry_date: datetime
    entry_spread: float
    current_spread: float
    position_size: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    status: str  # 'open', 'pending', 'closed'
    
    # Optional fields
    exit_date: Optional[datetime] = None
    exit_spread: Optional[float] = None
    realized_pnl: Optional[float] = None
    
    # Trade parameters
    hedge_ratio: float = 1.0
    entry_zscore: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Metadata
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, handling datetime serialization."""
        d = asdict(self)
        d["entry_date"] = self.entry_date.isoformat() if self.entry_date else None
        d["exit_date"] = self.exit_date.isoformat() if self.exit_date else None
        return d


@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics."""

    total_value: float
    cash_balance: float
    invested_capital: float
    total_pnl: float
    total_pnl_percent: float
    number_of_positions: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Additional metrics
    total_return: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        return asdict(self)


class PortfolioService:
    """Service for managing user portfolios and positions."""

    def __init__(self):
        """Initialize portfolio service."""
        # In-memory storage (replace with database in production)
        self.positions: Dict[str, Position] = {}
        self.user_portfolios: Dict[str, Dict[str, Any]] = {}
        self.trade_history: Dict[str, List[Position]] = {}

    def create_position(
        self,
        user_id: str,
        pair: str,
        asset1: str,
        asset2: str,
        position_type: str,
        entry_spread: float,
        position_size: float,
        hedge_ratio: float = 1.0,
        entry_zscore: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Position:
        """
        Create a new position.

        Args:
            user_id: User ID
            pair: Trading pair name
            asset1: First asset symbol
            asset2: Second asset symbol
            position_type: 'long-short' or 'short-long'
            entry_spread: Entry spread value
            position_size: Position size in USD
            hedge_ratio: Hedge ratio between assets
            entry_zscore: Entry z-score
            stop_loss: Stop loss level
            take_profit: Take profit level
            notes: Optional notes

        Returns:
            Created Position object
        """
        position = Position(
            id=str(uuid.uuid4()),
            user_id=user_id,
            pair=pair,
            asset1=asset1,
            asset2=asset2,
            type=position_type,
            entry_date=datetime.now(),
            entry_spread=entry_spread,
            current_spread=entry_spread,
            position_size=position_size,
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            status="open",
            hedge_ratio=hedge_ratio,
            entry_zscore=entry_zscore,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notes=notes,
        )

        self.positions[position.id] = position
        logger.info(f"Created position {position.id} for user {user_id}: {pair}")

        return position

    def update_position(
        self, position_id: str, current_spread: float
    ) -> Optional[Position]:
        """
        Update position with current spread and recalculate P&L.

        Args:
            position_id: Position ID
            current_spread: Current spread value

        Returns:
            Updated Position or None
        """
        position = self.positions.get(position_id)
        if not position:
            logger.warning(f"Position {position_id} not found")
            return None

        position.current_spread = current_spread

        # Calculate P&L based on spread change
        spread_change = current_spread - position.entry_spread

        # For long-short: profit when spread narrows
        # For short-long: profit when spread widens
        if position.type == "long-short":
            pnl = -spread_change * position.position_size
        else:  # short-long
            pnl = spread_change * position.position_size

        position.unrealized_pnl = pnl
        position.unrealized_pnl_percent = (pnl / position.position_size) * 100

        logger.debug(
            f"Updated position {position_id}: spread={current_spread:.3f}, P&L={pnl:.2f}"
        )

        return position

    def close_position(
        self, position_id: str, exit_spread: float, notes: Optional[str] = None
    ) -> Optional[Position]:
        """
        Close a position.

        Args:
            position_id: Position ID
            exit_spread: Exit spread value
            notes: Optional closing notes

        Returns:
            Closed Position or None
        """
        position = self.positions.get(position_id)
        if not position:
            logger.warning(f"Position {position_id} not found")
            return None

        # Update final values
        position.exit_date = datetime.now()
        position.exit_spread = exit_spread
        position.current_spread = exit_spread
        position.status = "closed"

        # Calculate final P&L
        spread_change = exit_spread - position.entry_spread
        if position.type == "long-short":
            pnl = -spread_change * position.position_size
        else:
            pnl = spread_change * position.position_size

        position.realized_pnl = pnl
        position.unrealized_pnl = 0.0
        position.unrealized_pnl_percent = 0.0

        if notes:
            position.notes = f"{position.notes}\n{notes}" if position.notes else notes

        # Add to trade history
        user_history = self.trade_history.get(position.user_id, [])
        user_history.append(position)
        self.trade_history[position.user_id] = user_history

        logger.info(
            f"Closed position {position_id}: P&L={pnl:.2f} ({(pnl/position.position_size)*100:.2f}%)"
        )

        return position

    def get_user_positions(
        self, user_id: str, status: Optional[str] = None
    ) -> List[Position]:
        """
        Get all positions for a user.

        Args:
            user_id: User ID
            status: Filter by status ('open', 'pending', 'closed', None=all)

        Returns:
            List of positions
        """
        positions = [p for p in self.positions.values() if p.user_id == user_id]

        if status:
            positions = [p for p in positions if p.status == status]

        return positions

    def calculate_portfolio_metrics(self, user_id: str) -> PortfolioMetrics:
        """
        Calculate portfolio metrics for a user.

        Args:
            user_id: User ID

        Returns:
            PortfolioMetrics object
        """
        open_positions = self.get_user_positions(user_id, status="open")
        closed_positions = self.trade_history.get(user_id, [])

        # Calculate basic metrics
        invested_capital = sum([p.position_size for p in open_positions])
        unrealized_pnl = sum([p.unrealized_pnl for p in open_positions])

        # Get starting capital (would be from user account in production)
        starting_capital = 10000.0  # Default
        cash_balance = starting_capital - invested_capital + unrealized_pnl

        total_value = cash_balance + invested_capital + unrealized_pnl
        total_pnl = total_value - starting_capital
        total_pnl_percent = (total_pnl / starting_capital) * 100

        # Win rate calculation
        if closed_positions:
            wins = [p for p in closed_positions if (p.realized_pnl or 0) > 0]
            win_rate = (len(wins) / len(closed_positions)) * 100

            # Average win/loss
            win_amounts = [p.realized_pnl for p in wins if p.realized_pnl]
            loss_amounts = [
                p.realized_pnl
                for p in closed_positions
                if p.realized_pnl and p.realized_pnl < 0
            ]

            avg_win = np.mean(win_amounts) if win_amounts else 0.0
            avg_loss = abs(np.mean(loss_amounts)) if loss_amounts else 0.0

            # Profit factor
            total_wins = sum(win_amounts) if win_amounts else 0.0
            total_losses = abs(sum(loss_amounts)) if loss_amounts else 0.0
            profit_factor = (
                total_wins / total_losses if total_losses > 0 else 0.0
            )
        else:
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            profit_factor = 0.0

        # Calculate Sharpe ratio (simplified)
        if closed_positions:
            returns = [
                (p.realized_pnl or 0) / p.position_size for p in closed_positions
            ]
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns) if len(returns) > 1 else 0.01
                sharpe_ratio = (avg_return / std_return) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Calculate max drawdown (simplified)
        if closed_positions:
            equity_curve = [starting_capital]
            for pos in closed_positions:
                equity_curve.append(equity_curve[-1] + (pos.realized_pnl or 0))

            peak = equity_curve[0]
            max_dd = 0.0
            for value in equity_curve:
                if value > peak:
                    peak = value
                dd = ((peak - value) / peak) * 100
                if dd > max_dd:
                    max_dd = dd
        else:
            max_dd = 0.0

        # Sortino ratio (downside deviation)
        if closed_positions:
            returns = [
                (p.realized_pnl or 0) / p.position_size for p in closed_positions
            ]
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = np.std(negative_returns)
                avg_return = np.mean(returns)
                sortino_ratio = (avg_return / downside_std) * np.sqrt(252)
            else:
                sortino_ratio = sharpe_ratio
        else:
            sortino_ratio = 0.0

        # Calmar ratio (return / max drawdown)
        calmar_ratio = (
            (total_pnl_percent / max_dd) if max_dd > 0 else 0.0
        )

        return PortfolioMetrics(
            total_value=total_value,
            cash_balance=cash_balance,
            invested_capital=invested_capital,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            number_of_positions=len(open_positions),
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            total_return=total_pnl_percent,
            average_win=avg_win,
            average_loss=avg_loss,
            profit_factor=profit_factor,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
        )

    def get_trade_history(
        self, user_id: str, limit: Optional[int] = None
    ) -> List[Position]:
        """
        Get trade history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of trades to return

        Returns:
            List of closed positions
        """
        history = self.trade_history.get(user_id, [])

        # Sort by exit date (most recent first)
        history.sort(
            key=lambda p: p.exit_date or datetime.min, reverse=True
        )

        if limit:
            history = history[:limit]

        return history

    def delete_position(self, position_id: str) -> bool:
        """
        Delete a position.

        Args:
            position_id: Position ID

        Returns:
            True if deleted, False if not found
        """
        if position_id in self.positions:
            del self.positions[position_id]
            logger.info(f"Deleted position {position_id}")
            return True
        return False


# Global instance
_portfolio_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create global PortfolioService instance."""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service
