"""
Unit tests for api.services.backtest_service.

Tests cover the two pure-function helpers:
  - get_default_config()  — returns sensible defaults
  - _normalise_config()   — merges caller config with defaults

No network or database access required.
"""

import sys
from pathlib import Path

import pytest

# Ensure backend package is importable when running from repo root.
_BACKEND = Path(__file__).parent.parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


# ---------------------------------------------------------------------------
# get_default_config
# ---------------------------------------------------------------------------

class TestGetDefaultConfig:
    """
    Tests for api.services.backtest_service.get_default_config.
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from api.services.backtest_service import get_default_config
        self.get_default_config = get_default_config

    def test_returns_dict(self):
        result = self.get_default_config()
        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        result = self.get_default_config()
        required = {
            "initial_capital",
            "position_size",
            "transaction_cost",
            "slippage",
            "entry_threshold",
            "exit_threshold",
            "stop_loss_threshold",
            "max_holding_period",
            "lookback_days",
            "granularity",
        }
        assert required.issubset(result.keys())

    def test_entry_threshold_greater_than_exit(self):
        result = self.get_default_config()
        assert result["entry_threshold"] > result["exit_threshold"]

    def test_stop_loss_greater_than_entry(self):
        result = self.get_default_config()
        assert result["stop_loss_threshold"] > result["entry_threshold"]

    def test_initial_capital_positive(self):
        assert self.get_default_config()["initial_capital"] > 0

    def test_lookback_days_positive(self):
        assert self.get_default_config()["lookback_days"] > 0

    def test_granularity_is_string(self):
        assert isinstance(self.get_default_config()["granularity"], str)

    def test_position_size_between_zero_and_one(self):
        ps = self.get_default_config()["position_size"]
        assert 0 < ps <= 1


# ---------------------------------------------------------------------------
# _normalise_config
# ---------------------------------------------------------------------------

class TestNormaliseConfig:
    """
    Tests for api.services.backtest_service._normalise_config.
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from api.services.backtest_service import _normalise_config  # noqa: PLC2701
        self._normalise_config = _normalise_config

    def test_missing_both_symbols_raises(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            self._normalise_config({})

    def test_missing_symbol2_raises(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            self._normalise_config({"symbol1": "AAPL"})

    def test_valid_minimal_config_succeeds(self):
        result = self._normalise_config({"symbol1": "AAPL", "symbol2": "MSFT"})
        assert result["symbol1"] == "AAPL"
        assert result["symbol2"] == "MSFT"

    def test_defaults_are_applied_for_missing_fields(self):
        result = self._normalise_config({"symbol1": "AAPL", "symbol2": "MSFT"})
        from api.services.backtest_service import _BACKTEST_DEFAULTS
        for key, default_value in _BACKTEST_DEFAULTS.items():
            assert result[key] == default_value, f"Default not applied for {key!r}"

    def test_caller_value_overrides_default(self):
        result = self._normalise_config(
            {"symbol1": "GLD", "symbol2": "SLV", "lookback_days": 90}
        )
        assert result["lookback_days"] == 90

    def test_extra_keys_are_preserved(self):
        result = self._normalise_config(
            {"symbol1": "GLD", "symbol2": "SLV", "custom_param": "foo"}
        )
        assert result["custom_param"] == "foo"

    def test_none_raw_config_raises(self):
        with pytest.raises((ValueError, TypeError)):
            self._normalise_config(None)  # type: ignore[arg-type]
