"""Broker endpoints (local paper by default, optional CCXT)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from hedgevision.broker import get_broker
from hedgevision.models import BrokerQuotePayload

router = APIRouter(prefix="/broker", tags=["broker"])


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    backend: str | None = Query(None, description="paper|ccxt"),
    exchange: str | None = Query(None, description="CCXT exchange id"),
) -> BrokerQuotePayload:
    try:
        broker = get_broker(backend=backend, exchange=exchange)
        return broker.get_quote(symbol)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
