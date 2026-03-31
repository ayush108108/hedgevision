"""
Backtest service providing orchestration helpers for the API layer.

This module centralises backtest-related operations so that routing code can
remain thin and the unit-test suite can patch the legacy import path
(`api.services.backtest_service`).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from api.services.backtest_engine import BacktestConfig

# REMOVED: Celery imports (GitHub Actions handles scheduling)
# from celery.result import AsyncResult
# from api.tasks.celery_app import celery_app
# from api.tasks.backtest_runner import run_pair_backtest


logger = logging.getLogger(__name__)

# Default configuration used when callers omit optional settings
_BACKTEST_DEFAULTS: Dict[str, Any] = {
    "lookback_days": 365,
    "initial_capital": 10_000.0,
    "position_size": 0.1,
    "transaction_cost": 0.001,
    "slippage": 0.0005,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss_threshold": 3.0,
    "max_holding_period": 30,
    "granularity": "daily",
}


def get_default_config() -> Dict[str, Any]:
    """Return a serialisable default backtest configuration."""

    defaults = BacktestConfig(
        initial_capital=_BACKTEST_DEFAULTS["initial_capital"],
        position_size=_BACKTEST_DEFAULTS["position_size"],
        transaction_cost=_BACKTEST_DEFAULTS["transaction_cost"],
        slippage=_BACKTEST_DEFAULTS["slippage"],
        entry_threshold=_BACKTEST_DEFAULTS["entry_threshold"],
        exit_threshold=_BACKTEST_DEFAULTS["exit_threshold"],
        stop_loss_threshold=_BACKTEST_DEFAULTS["stop_loss_threshold"],
        max_holding_period=_BACKTEST_DEFAULTS["max_holding_period"],
    )
    return {
        "lookback_days": _BACKTEST_DEFAULTS["lookback_days"],
        "initial_capital": defaults.initial_capital,
        "position_size": defaults.position_size,
        "transaction_cost": defaults.transaction_cost,
        "slippage": defaults.slippage,
        "entry_threshold": defaults.entry_threshold,
        "exit_threshold": defaults.exit_threshold,
        "stop_loss_threshold": defaults.stop_loss_threshold,
        "max_holding_period": defaults.max_holding_period,
        "granularity": _BACKTEST_DEFAULTS["granularity"],
    }


def _normalise_config(raw_config: Dict[str, Any]) -> Dict[str, Any]:
    """Merge caller supplied config with defaults."""

    merged = {**_BACKTEST_DEFAULTS, **(raw_config or {})}
    required = ["symbol1", "symbol2"]
    missing = [field for field in required if not merged.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    return merged


def run_backtest(cache, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Execute a synchronous backtest and return results.

    Args:
    """
    # Backtest service is currently disabled. This module is not available.
    """

    def disabled_backtest_service(*args, **kwargs):
        raise NotImplementedError("Backtest functionality is currently disabled. Coming soon.")
        logger.warning("Price dataframe missing spread/zscore columns for %s/%s", symbol1, symbol2)
        return None

    spread_series = price_df.set_index("Date")["spread"].dropna()
    zscore_series = price_df.set_index("Date")["zscore"].dropna()

    if len(spread_series) < 30 or len(zscore_series) < 30:
        logger.warning("Not enough data points to run backtest for %s/%s", symbol1, symbol2)
        return None

    bt_config = BacktestConfig(
        initial_capital=float(params.get("initial_capital", _BACKTEST_DEFAULTS["initial_capital"])),
        position_size=float(params.get("position_size", _BACKTEST_DEFAULTS["position_size"])),
        transaction_cost=float(params.get("transaction_cost", _BACKTEST_DEFAULTS["transaction_cost"])),
        slippage=float(params.get("slippage", _BACKTEST_DEFAULTS["slippage"])),
        entry_threshold=float(params.get("entry_threshold", _BACKTEST_DEFAULTS["entry_threshold"])),
        exit_threshold=float(params.get("exit_threshold", _BACKTEST_DEFAULTS["exit_threshold"])),
        stop_loss_threshold=float(params.get("stop_loss_threshold", _BACKTEST_DEFAULTS["stop_loss_threshold"])),
        max_holding_period=params.get("max_holding_period"),
    )

    backtester = PairBacktester(bt_config)
    results = backtester.run_backtest(
        spread_series=spread_series,
        zscore_series=zscore_series,
        asset1_name=symbol1,
        asset2_name=symbol2,
    )

    trades: List[Dict[str, Any]] = []
    for trade in results.get("trades", []):
        formatted = dict(trade)
        entry_date = formatted.get("entry_date")
        exit_date = formatted.get("exit_date")
        if hasattr(entry_date, "isoformat"):
            formatted["entry_date"] = entry_date.isoformat()
        if hasattr(exit_date, "isoformat"):
            formatted["exit_date"] = exit_date.isoformat()
        trades.append(formatted)

    equity_curve = {
        str(key): float(value) for key, value in dict(results.get("equity_curve", {})).items()
    }

    response: Dict[str, Any] = {
        "metrics": results.get("metrics", {}),
        "trades": trades,
        "equity_curve": equity_curve,
        "config_used": {
            "symbol1": symbol1,
            "symbol2": symbol2,
            "lookback_days": lookback_days,
            "granularity": granularity,
        },
    }
    return response


def enqueue_backtest(config: Dict[str, Any]) -> Dict[str, str]:
#     Submit an asynchronous backtest task and return the Celery task id.

#     params = _normalise_config(config)
#     task = run_pair_backtest.delay(
#         params["symbol1"],
#         params["symbol2"],
#         lookback_days=int(params.get("lookback_days", _BACKTEST_DEFAULTS["lookback_days"])),
#         backtest_params={
#             "initial_capital": params.get("initial_capital", _BACKTEST_DEFAULTS["initial_capital"]),
#             "position_size": params.get("position_size", _BACKTEST_DEFAULTS["position_size"]),
#             "transaction_cost": params.get("transaction_cost", _BACKTEST_DEFAULTS["transaction_cost"]),
#             "slippage": params.get("slippage", _BACKTEST_DEFAULTS["slippage"]),
#             "entry_threshold": params.get("entry_threshold", _BACKTEST_DEFAULTS["entry_threshold"]),
#             "exit_threshold": params.get("exit_threshold", _BACKTEST_DEFAULTS["exit_threshold"]),
#             "stop_loss_threshold": params.get("stop_loss_threshold", _BACKTEST_DEFAULTS["stop_loss_threshold"]),
#             "max_holding_period": params.get("max_holding_period", _BACKTEST_DEFAULTS["max_holding_period"]),
#         },
#     )
#     return {"task_id": task.id}


# def get_backtest_status(task_id: str) -> Optional[Dict[str, Any]]:
#     Retrieve Celery task status for a backtest job.

#     if not task_id:
#         return None

#     result = AsyncResult(task_id, app=celery_app)
#     payload: Dict[str, Any] = {"state": result.state}

#     if result.state == "PENDING":
#         return payload
#     if result.state == "PROGRESS":
#         payload["meta"] = result.info
#         return payload
#     if result.state == "SUCCESS":
#         payload["result"] = result.result
#         return payload
#     if result.state == "FAILURE":
#         payload["error"] = str(result.result)
#         return payload

#     payload["meta"] = result.info
#     return payload


# def validate_backtest_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
#     Validate a backtest configuration and return errors, if any.

#     errors: List[str] = []
#     try:
#         params = _normalise_config(config)
#     except ValueError as exc:
#         return False, [str(exc)]

#     if params.get("initial_capital", 0) <= 0:
#         errors.append("Initial capital must be positive")
#     if params.get("position_size", 0) <= 0:
#         errors.append("Position size must be positive")
#     if params.get("entry_threshold", 0) <= 0:
#         errors.append("Entry threshold must be positive")
#     if params.get("exit_threshold", 0) < 0:
#         errors.append("Exit threshold cannot be negative")
#     if params.get("stop_loss_threshold", 0) <= 0:
#         errors.append("Stop loss threshold must be positive")
#     if params.get("entry_threshold", 0) <= params.get("exit_threshold", 0):
#         errors.append("Entry threshold must be greater than exit threshold")

#     return len(errors) == 0, errors


# def optimize_parameters(cache, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
#     Placeholder optimisation helper used by the API.

#     The comprehensive optimisation logic lives in dedicated research notebooks.
#     For API use we provide a simple hook that can be patched in tests or extend
#     in the future. Returning ``None`` indicates no viable optimisation result.
#     """


#     logger.info("Optimization request received for %s/%s", request.get("symbol1"), request.get("symbol2"))
#     return None
