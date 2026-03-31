"""Pair trading backtest utilities used by the FastAPI routers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class BacktestConfig:
    """Configuration values for the pair trading backtest."""

    initial_capital: float = 10_000.0
    position_size: float = 1.0
    transaction_cost: float = 0.001
    slippage: float = 0.0005
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    stop_loss_threshold: float = 3.0
    max_holding_period: Optional[int] = None  # Number of bars


class PairBacktester:
    """Run a simple mean-reversion backtest on spread/z-score series."""

    def __init__(self, config: BacktestConfig) -> None:
        self.config = config

    def run_backtest(
        self,
        spread_series: pd.Series,
        zscore_series: pd.Series,
        asset1_name: str,
        asset2_name: str,
    ) -> Dict[str, object]:
        """Execute the backtest and return metrics, trades, and equity curve."""

        if spread_series is None or zscore_series is None:
            raise ValueError("Spread and z-score series must be provided")

        data = (
            pd.DataFrame({"spread": spread_series, "zscore": zscore_series})
            .dropna()
            .sort_index()
        )

        if data.empty:
            raise ValueError(
                "No overlapping spread/z-score data available for backtest"
            )

        trades: List[Dict[str, object]] = []
        equity_history: List[Dict[str, object]] = []

        capital = float(self.config.initial_capital)
        open_position: Optional[Dict[str, object]] = None

        for timestamp, row in data.iterrows():
            zscore = float(row["zscore"])
            spread_value = float(row["spread"])

            if open_position is None:
                if zscore >= self.config.entry_threshold:
                    open_position = {
                        "position_type": "short",
                        "entry_date": timestamp,
                        "entry_spread": spread_value,
                        "entry_zscore": zscore,
                        "bars_held": 0,
                    }
                elif zscore <= -self.config.entry_threshold:
                    open_position = {
                        "position_type": "long",
                        "entry_date": timestamp,
                        "entry_spread": spread_value,
                        "entry_zscore": zscore,
                        "bars_held": 0,
                    }
            else:
                open_position["bars_held"] = int(open_position["bars_held"]) + 1

                exit_reason = None
                if open_position["position_type"] == "short":
                    if zscore <= self.config.exit_threshold:
                        exit_reason = "take_profit"
                    elif zscore >= self.config.stop_loss_threshold:
                        exit_reason = "stop_loss"
                else:
                    if zscore >= -self.config.exit_threshold:
                        exit_reason = "take_profit"
                    elif zscore <= -self.config.stop_loss_threshold:
                        exit_reason = "stop_loss"

                if (
                    exit_reason is None
                    and self.config.max_holding_period is not None
                    and open_position["bars_held"] >= self.config.max_holding_period
                ):
                    exit_reason = "time_exit"

                if exit_reason is not None:
                    pnl = self._calculate_pnl(
                        open_position["position_type"],
                        open_position["entry_spread"],
                        spread_value,
                    )
                    costs = self._estimate_costs()
                    net_pnl = pnl - costs
                    capital += net_pnl

                    trades.append(
                        {
                            "entry_date": open_position["entry_date"],
                            "exit_date": timestamp,
                            "entry_spread": float(open_position["entry_spread"]),
                            "exit_spread": float(spread_value),
                            "entry_zscore": float(open_position["entry_zscore"]),
                            "exit_zscore": zscore,
                            "position_type": open_position["position_type"],
                            "pnl": float(net_pnl),
                            "exit_reason": exit_reason,
                            "duration": int(open_position["bars_held"]),
                        }
                    )

                    open_position = None

            equity_history.append({"date": timestamp, "equity": float(capital)})

        if open_position is not None:
            last_timestamp = data.index[-1]
            last_spread = float(data.iloc[-1]["spread"])
            pnl = self._calculate_pnl(
                open_position["position_type"],
                open_position["entry_spread"],
                last_spread,
            )
            costs = self._estimate_costs()
            net_pnl = pnl - costs
            capital += net_pnl
            trades.append(
                {
                    "entry_date": open_position["entry_date"],
                    "exit_date": last_timestamp,
                    "entry_spread": float(open_position["entry_spread"]),
                    "exit_spread": float(last_spread),
                    "entry_zscore": float(open_position["entry_zscore"]),
                    "exit_zscore": float(data.iloc[-1]["zscore"]),
                    "position_type": open_position["position_type"],
                    "pnl": float(net_pnl),
                    "exit_reason": "forced_exit",
                    "duration": int(open_position["bars_held"]),
                }
            )
            equity_history.append({"date": last_timestamp, "equity": float(capital)})

        equity_df = pd.DataFrame(equity_history).drop_duplicates(subset="date")
        equity_df = equity_df.sort_values("date")

        metrics = self._compute_metrics(capital, equity_df, trades)

        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": {
                self._to_iso(row.date): float(row.equity)
                for row in equity_df.itertuples(index=False)
            },
        }

    def _calculate_pnl(
        self, position_type: str, entry_spread: float, exit_spread: float
    ) -> float:
        """Calculate raw PnL for a trade."""

        spread_diff = exit_spread - entry_spread
        if position_type == "short":
            spread_diff = entry_spread - exit_spread
        return spread_diff * self.config.position_size

    def _estimate_costs(self) -> float:
        """Approximate round-trip trading costs."""

        trade_units = abs(self.config.position_size)
        cost = (self.config.transaction_cost + self.config.slippage) * trade_units
        return float(cost)

    def _compute_metrics(
        self,
        final_capital: float,
        equity_df: pd.DataFrame,
        trades: List[Dict[str, object]],
    ) -> Dict[str, Optional[float]]:
        """Compute summary statistics for the backtest."""

        initial_capital = float(self.config.initial_capital)
        total_return = (final_capital - initial_capital) / initial_capital

        max_drawdown = None
        annualized_return = None

        if len(equity_df) > 1:
            equity_series = equity_df.set_index("date")["equity"].astype(float)
            running_max = equity_series.cummax()
            drawdowns = (equity_series - running_max) / running_max
            max_drawdown = float(drawdowns.min()) if not drawdowns.empty else None

            start = pd.Timestamp(equity_series.index[0])
            end = pd.Timestamp(equity_series.index[-1])
            elapsed_days = max((end - start).total_seconds() / 86400.0, 1 / 365.25)
            annualized_return = (1 + total_return) ** (365.25 / elapsed_days) - 1

        wins = sum(1 for trade in trades if trade["pnl"] > 0)
        trade_count = len(trades)
        win_rate = wins / trade_count if trade_count else None
        avg_trade = (
            sum(trade["pnl"] for trade in trades) / trade_count if trade_count else None
        )

        return {
            "initial_capital": initial_capital,
            "final_capital": float(final_capital),
            "total_return": float(total_return),
            "annualized_return": (
                float(annualized_return) if annualized_return is not None else None
            ),
            "max_drawdown": float(max_drawdown) if max_drawdown is not None else None,
            "trade_count": trade_count,
            "win_rate": float(win_rate) if win_rate is not None else None,
            "average_trade": float(avg_trade) if avg_trade is not None else None,
        }

    @staticmethod
    def _to_iso(value) -> str:
        """Convert timestamps returned by pandas to ISO 8601 strings."""

        if isinstance(value, pd.Timestamp):
            if value.tzinfo is None:
                value = value.tz_localize("UTC")
            return value.isoformat()
        return str(value)
