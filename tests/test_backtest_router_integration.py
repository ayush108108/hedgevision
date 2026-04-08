"""
Integration tests for the backtest router.

These tests verify the API contract (request validation,
response shape, error handling) without hitting real databases.
The AnalyticsService.get_full_pair_report call is mocked so the
suite runs offline and fast.
"""

import math
import os
from datetime import date, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

# Ensure the optional backtest router is loaded before *any* import of
# api.main so the routes exist when sync_client builds its TestClient.
os.environ.setdefault("ENABLE_BACKTEST", "true")


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_START = date(2021, 1, 1)
_N = 500  # >30 points — enough for a reliable backtest


def _make_spread_data(n: int = _N) -> List[Dict[str, Any]]:
    """Generate synthetic spread / z-score series."""
    return [
        {
            "date": (_START + timedelta(days=i)).isoformat(),
            "spread": math.sin(i * 0.05) * 3.0,
            "zscore": math.sin(i * 0.05) * 2.5,
        }
        for i in range(n)
    ]


MOCK_PAIR_REPORT: Dict[str, Any] = {"spread_data": _make_spread_data()}

_VALID_PAYLOAD: Dict[str, Any] = {
    "symbol1": "AAPL",
    "symbol2": "MSFT",
    "lookback_days": 365,
    "initial_capital": 10000.0,
    "position_size": 0.1,
    "transaction_cost": 0.001,
    "slippage": 0.0005,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss_threshold": 3.0,
    "max_holding_period": 30,
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _patch_analytics(mock_report: Dict[str, Any] = MOCK_PAIR_REPORT):
    """Return a context manager that mocks AnalyticsService."""
    mock_instance = AsyncMock()
    mock_instance.get_full_pair_report = AsyncMock(return_value=mock_report)
    return patch(
        "api.services.analytics_service.AnalyticsService",
        return_value=mock_instance,
    )


# ---------------------------------------------------------------------------
# /backtest/config/default
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    """Tests for GET /api/backtest/config/default."""

    def test_returns_200(self, sync_client):
        resp = sync_client.get("/api/backtest/config/default")
        assert resp.status_code == 200

    def test_contains_required_keys(self, sync_client):
        resp = sync_client.get("/api/backtest/config/default")
        body = resp.json()
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
        assert required.issubset(body.keys())

    def test_sensible_defaults(self, sync_client):
        body = sync_client.get("/api/backtest/config/default").json()
        assert body["entry_threshold"] > body["exit_threshold"]
        assert body["stop_loss_threshold"] > body["entry_threshold"]
        assert body["initial_capital"] > 0
        assert body["lookback_days"] > 0


# ---------------------------------------------------------------------------
# /backtest/config/validate
# ---------------------------------------------------------------------------

class TestValidateConfig:
    """Tests for POST /api/backtest/config/validate."""

    def test_valid_config_returns_is_valid_true(self, sync_client):
        resp = sync_client.post("/api/backtest/config/validate", json=_VALID_PAYLOAD)
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_valid"] is True
        assert body["errors"] == []

    def test_entry_lte_exit_threshold_is_error(self, sync_client):
        payload = {**_VALID_PAYLOAD, "entry_threshold": 0.5, "exit_threshold": 0.5}
        resp = sync_client.post("/api/backtest/config/validate", json=payload)
        body = resp.json()
        assert body["is_valid"] is False
        assert any("entry_threshold" in e for e in body["errors"])

    def test_high_transaction_cost_triggers_warning(self, sync_client):
        payload = {**_VALID_PAYLOAD, "transaction_cost": 0.009, "slippage": 0.009}
        resp = sync_client.post("/api/backtest/config/validate", json=payload)
        body = resp.json()
        assert any("cost" in w.lower() for w in body["warnings"])

    def test_missing_symbols_returns_422(self, sync_client):
        resp = sync_client.post("/api/backtest/config/validate", json={"symbol1": "AAPL"})
        assert resp.status_code == 422

    def test_response_contains_config_echo(self, sync_client):
        resp = sync_client.post("/api/backtest/config/validate", json=_VALID_PAYLOAD)
        body = resp.json()
        assert "config" in body
        assert body["config"]["symbol1"] == "AAPL"


# ---------------------------------------------------------------------------
# /backtest/run
# ---------------------------------------------------------------------------

class TestRunBacktest:
    """Tests for POST /api/backtest/run."""

    def test_returns_200_with_valid_payload(self, sync_client):
        with _patch_analytics():
            resp = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD)
        assert resp.status_code == 200

    def test_response_shape(self, sync_client):
        with _patch_analytics():
            body = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD).json()
        assert {"metrics", "trades", "equity_curve"}.issubset(body.keys())

    def test_metrics_keys(self, sync_client):
        with _patch_analytics():
            body = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD).json()
        metrics = body["metrics"]
        required_keys = {
            "initial_capital",
            "final_capital",
            "total_return",
            "trade_count",
        }
        assert required_keys.issubset(metrics.keys())

    def test_trade_count_matches_trades_list(self, sync_client):
        with _patch_analytics():
            body = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD).json()
        assert body["metrics"]["trade_count"] == len(body["trades"])

    def test_missing_symbol2_returns_422(self, sync_client):
        payload = {"symbol1": "AAPL", "lookback_days": 365}
        resp = sync_client.post("/api/backtest/run", json=payload)
        assert resp.status_code == 422

    def test_empty_spread_data_returns_error(self, sync_client):
        empty_report: Dict[str, Any] = {"spread_data": []}
        with _patch_analytics(empty_report):
            resp = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD)
        assert resp.status_code in (400, 404)

    def test_insufficient_data_returns_400(self, sync_client):
        short_report: Dict[str, Any] = {"spread_data": _make_spread_data(n=10)}
        with _patch_analytics(short_report):
            resp = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD)
        assert resp.status_code == 400

    def test_trades_have_expected_fields(self, sync_client):
        with _patch_analytics():
            body = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD).json()
        trades = body["trades"]
        if trades:
            trade = trades[0]
            expected = {"entry_date", "exit_date", "pnl", "position_type"}
            assert expected.issubset(trade.keys())

    def test_equity_curve_non_empty(self, sync_client):
        with _patch_analytics():
            body = sync_client.post("/api/backtest/run", json=_VALID_PAYLOAD).json()
        assert isinstance(body["equity_curve"], dict)
        assert len(body["equity_curve"]) > 0

    def test_blank_symbol_returns_422(self, sync_client):
        payload = {**_VALID_PAYLOAD, "symbol1": "   "}
        resp = sync_client.post("/api/backtest/run", json=payload)
        assert resp.status_code == 422
