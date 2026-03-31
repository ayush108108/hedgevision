"""Broker router for local-first runtime."""

from __future__ import annotations

from typing import Any

from hedgevision.broker.ccxt import CCXTBroker
from hedgevision.broker.paper import PaperBroker
from hedgevision.config import SecureConfig


def get_broker(
    *,
    backend: str | None = None,
    exchange: str | None = None,
    config: SecureConfig | None = None,
) -> Any:
    cfg = config or SecureConfig.from_env()
    selected_backend = (backend or cfg.broker_backend or "paper").strip().lower()

    if selected_backend == "paper":
        return PaperBroker()
    if selected_backend == "ccxt":
        return CCXTBroker(
            exchange_id=(exchange or cfg.ccxt_exchange or "binance").strip().lower(),
            api_key=cfg.ccxt_api_key,
            api_secret=cfg.ccxt_api_secret,
        )

    raise ValueError(
        f"Unsupported broker backend '{selected_backend}'. Expected one of: paper, ccxt"
    )
