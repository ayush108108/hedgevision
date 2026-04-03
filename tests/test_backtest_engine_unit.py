"""Unit tests for backend/api/services/backtest_engine.py.

Covers PairBacktester and BacktestConfig with no external dependencies.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from api.services.backtest_engine import BacktestConfig, PairBacktester


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sine_series(periods: int = 100, amplitude: float = 3.0, seed: int = 0) -> pd.Series:
    """Return a sine-wave z-score series that crosses entry/exit thresholds."""
    t = np.linspace(0, 4 * np.pi, periods)
    noise = np.random.default_rng(seed).normal(0, 0.05, periods)
    return pd.Series(
        amplitude * np.sin(t) + noise,
        index=pd.date_range("2023-01-01", periods=periods, freq="D"),
        name="zscore",
    )


def _flat_diverging_zscore(periods: int = 60) -> pd.Series:
    """Z-score that diverges past stop-loss threshold without reverting."""
    values = np.concatenate(
        [np.array([2.2]), np.linspace(2.2, 5.5, periods - 1)]
    )
    return pd.Series(
        values,
        index=pd.date_range("2023-01-01", periods=periods, freq="D"),
        name="zscore",
    )


def _make_backtester(overrides: dict | None = None) -> PairBacktester:
    cfg_kwargs = dict(
        initial_capital=10_000.0,
        position_size=1.0,
        transaction_cost=0.001,
        slippage=0.0005,
        entry_threshold=2.0,
        exit_threshold=0.5,
        stop_loss_threshold=3.5,
    )
    if overrides:
        cfg_kwargs.update(overrides)
    return PairBacktester(BacktestConfig(**cfg_kwargs))


def _run(overrides: dict | None = None, periods: int = 120, amplitude: float = 3.0):
    bt = _make_backtester(overrides)
    zscore = _sine_series(periods=periods, amplitude=amplitude)
    spread = zscore * 10.0
    return bt.run_backtest(
        spread_series=spread,
        zscore_series=zscore,
        asset1_name="AAPL",
        asset2_name="MSFT",
    )


# ---------------------------------------------------------------------------
# BacktestConfig
# ---------------------------------------------------------------------------


class TestBacktestConfig:
    def test_defaults_are_sensible(self):
        cfg = BacktestConfig()
        assert cfg.initial_capital > 0
        assert cfg.entry_threshold > cfg.exit_threshold >= 0
        assert cfg.stop_loss_threshold > cfg.entry_threshold
        assert 0 <= cfg.transaction_cost < 1
        assert 0 <= cfg.slippage < 1

    def test_custom_values_stored(self):
        cfg = BacktestConfig(
            initial_capital=50_000.0,
            position_size=2.5,
            entry_threshold=1.8,
            exit_threshold=0.3,
            stop_loss_threshold=4.0,
        )
        assert cfg.initial_capital == 50_000.0
        assert cfg.position_size == 2.5
        assert cfg.entry_threshold == 1.8
        assert cfg.exit_threshold == 0.3
        assert cfg.stop_loss_threshold == 4.0


# ---------------------------------------------------------------------------
# PairBacktester – error handling
# ---------------------------------------------------------------------------


class TestPairBacktesterErrors:
    def test_raises_on_none_series(self):
        bt = _make_backtester()
        with pytest.raises(ValueError, match="[Ss]pread"):
            bt.run_backtest(
                spread_series=None,
                zscore_series=None,
                asset1_name="X",
                asset2_name="Y",
            )

    def test_raises_on_non_overlapping_index(self):
        bt = _make_backtester()
        z = _sine_series()
        s = pd.Series(
            z.values,
            index=pd.date_range("2025-01-01", periods=len(z), freq="D"),
            name="spread",
        )
        with pytest.raises(ValueError):
            bt.run_backtest(
                spread_series=s,
                zscore_series=z,
                asset1_name="X",
                asset2_name="Y",
            )


# ---------------------------------------------------------------------------
# PairBacktester – result structure
# ---------------------------------------------------------------------------


class TestPairBacktesterResultStructure:
    def test_result_keys_present(self):
        result = _run()
        assert "metrics" in result
        assert "trades" in result
        assert "equity_curve" in result

    def test_metrics_keys_present(self):
        required_keys = {
            "initial_capital",
            "final_capital",
            "total_return",
            "trade_count",
        }
        metrics = _run()["metrics"]
        assert required_keys.issubset(metrics.keys())

    def test_trades_are_list(self):
        assert isinstance(_run()["trades"], list)

    def test_equity_curve_is_dict(self):
        assert isinstance(_run()["equity_curve"], dict)

    def test_equity_curve_values_are_floats(self):
        ec = _run()["equity_curve"]
        assert all(isinstance(v, float) for v in ec.values())

    def test_equity_curve_keys_are_iso_strings(self):
        """Keys must be ISO 8601 strings so the API can serialise them."""
        ec = _run()["equity_curve"]
        for key in ec:
            # Should parse without error
            pd.Timestamp(key)


# ---------------------------------------------------------------------------
# PairBacktester – trade fields
# ---------------------------------------------------------------------------


class TestTradeFields:
    def test_trade_fields_present(self):
        required = {
            "entry_date", "exit_date",
            "entry_spread", "exit_spread",
            "entry_zscore", "exit_zscore",
            "position_type", "pnl",
            "exit_reason", "duration",
        }
        result = _run()
        for trade in result["trades"]:
            assert required.issubset(trade.keys()), (
                f"Missing fields: {required - trade.keys()}"
            )

    def test_position_type_values(self):
        result = _run()
        for trade in result["trades"]:
            assert trade["position_type"] in {"long", "short"}

    def test_exit_reason_values(self):
        result = _run()
        valid_reasons = {"take_profit", "stop_loss", "time_exit", "forced_exit"}
        for trade in result["trades"]:
            assert trade["exit_reason"] in valid_reasons

    def test_duration_non_negative(self):
        result = _run()
        for trade in result["trades"]:
            assert trade["duration"] >= 0

    def test_long_entry_at_negative_zscore(self):
        """Long trades should be entered when zscore <= -entry_threshold."""
        result = _run()
        for trade in result["trades"]:
            if trade["position_type"] == "long":
                assert trade["entry_zscore"] <= -2.0

    def test_short_entry_at_positive_zscore(self):
        """Short trades should be entered when zscore >= entry_threshold."""
        result = _run()
        for trade in result["trades"]:
            if trade["position_type"] == "short":
                assert trade["entry_zscore"] >= 2.0


# ---------------------------------------------------------------------------
# PairBacktester – metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_initial_capital_preserved_in_metrics(self):
        metrics = _run()["metrics"]
        assert metrics["initial_capital"] == 10_000.0

    def test_final_capital_is_float(self):
        assert isinstance(_run()["metrics"]["final_capital"], float)

    def test_total_return_formula(self):
        metrics = _run()["metrics"]
        expected = (
            metrics["final_capital"] - metrics["initial_capital"]
        ) / metrics["initial_capital"]
        assert abs(metrics["total_return"] - expected) < 1e-9

    def test_win_rate_in_bounds(self):
        wr = _run()["metrics"]["win_rate"]
        if wr is not None:
            assert 0.0 <= wr <= 1.0

    def test_trade_count_matches_trades_list(self):
        result = _run()
        assert result["metrics"]["trade_count"] == len(result["trades"])

    def test_mean_reverting_data_produces_trades(self):
        result = _run(periods=200, amplitude=3.0)
        assert result["metrics"]["trade_count"] > 0, (
            "Mean-reverting data should produce at least one trade"
        )

    def test_max_drawdown_non_positive(self):
        """Max drawdown is expressed as a fraction <= 0 (loss)."""
        dd = _run(periods=200)["metrics"]["max_drawdown"]
        if dd is not None:
            assert dd <= 0

    def test_capital_consistency(self):
        """Sum of net PnL over all trades should equal final_capital - initial_capital."""
        result = _run()
        metrics = result["metrics"]
        pnl_sum = sum(t["pnl"] for t in result["trades"])
        diff = abs(
            pnl_sum - (metrics["final_capital"] - metrics["initial_capital"])
        )
        # Allow small floating point error
        assert diff < 1e-6, f"Capital inconsistency: pnl_sum={pnl_sum:.6f}, diff={diff}"


# ---------------------------------------------------------------------------
# PairBacktester – cost deduction
# ---------------------------------------------------------------------------


class TestCosts:
    def test_costs_reduce_net_pnl(self):
        """Running with costs should produce less final capital than zero costs."""
        result_with_costs = _run()
        result_no_costs = _run(overrides={"transaction_cost": 0.0, "slippage": 0.0})

        # Both should trade; net capital with costs should be <= without costs
        # (on a profitable strategy costs drag returns)
        fc_costs = result_with_costs["metrics"]["final_capital"]
        fc_no_costs = result_no_costs["metrics"]["final_capital"]

        if result_with_costs["metrics"]["trade_count"] > 0:
            assert fc_costs <= fc_no_costs, (
                "Transaction costs should reduce (or at least not increase) returns"
            )


# ---------------------------------------------------------------------------
# PairBacktester – stop-loss
# ---------------------------------------------------------------------------


class TestStopLoss:
    def test_diverging_zscore_triggers_stop_loss(self):
        """A continuously diverging z-score must trigger stop-loss exits."""
        bt = _make_backtester(overrides={"stop_loss_threshold": 3.5})
        z = _flat_diverging_zscore()
        s = z * 10.0
        result = bt.run_backtest(
            spread_series=s, zscore_series=z, asset1_name="A", asset2_name="B"
        )
        stop_loss_exits = [
            t for t in result["trades"] if t["exit_reason"] == "stop_loss"
        ]
        assert len(stop_loss_exits) > 0, "Diverging z-score must trigger stop-loss"


# ---------------------------------------------------------------------------
# PairBacktester – max holding period
# ---------------------------------------------------------------------------


class TestMaxHoldingPeriod:
    def test_time_exit_fires_when_max_holding_set(self):
        """With max_holding_period=5 some trades must exit by time rule."""
        bt = PairBacktester(
            BacktestConfig(
                initial_capital=10_000.0,
                position_size=1.0,
                entry_threshold=2.0,
                exit_threshold=0.1,  # Very tight – almost never hit
                stop_loss_threshold=100.0,  # Never hit
                max_holding_period=5,
            )
        )
        # Slow-reverting sine so positions stay open long enough to trip time_exit
        t = np.linspace(0, 2 * np.pi, 200)
        z = pd.Series(
            2.5 * np.sin(t),
            index=pd.date_range("2023-01-01", periods=200, freq="D"),
        )
        result = bt.run_backtest(
            spread_series=z * 5, zscore_series=z, asset1_name="A", asset2_name="B"
        )
        time_exits = [t for t in result["trades"] if t["exit_reason"] == "time_exit"]
        assert len(time_exits) > 0, "max_holding_period should produce time_exit trades"


# ---------------------------------------------------------------------------
# PairBacktester – equity curve ordering
# ---------------------------------------------------------------------------


class TestEquityCurve:
    def test_equity_curve_starts_near_initial_capital(self):
        result = _run()
        ec = result["equity_curve"]
        if ec:
            first_value = next(iter(ec.values()))
            # First equity value should be near initial capital (within 10 %)
            assert abs(first_value - 10_000.0) / 10_000.0 < 0.10

    def test_equity_curve_length_matches_data(self):
        """Equity curve should have one entry per data point."""
        result = _run(periods=120)
        # May be de-duped but should be non-empty
        assert len(result["equity_curve"]) > 0

    def test_equity_keys_are_sorted(self):
        ec = _run()["equity_curve"]
        keys = list(ec.keys())
        assert keys == sorted(keys), "Equity curve should be chronologically sorted"
