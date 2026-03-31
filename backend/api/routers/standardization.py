from __future__ import annotations

from fastapi import APIRouter, Query

from ..services.standardization_service import get_standardization_service


router = APIRouter(prefix="/standardize", tags=["standardize"])


@router.get("/pair")
def canonical_pair(asset1: str = Query(...), asset2: str = Query(...), delimiter: str = Query("-")):
    svc = get_standardization_service()
    return {"pair": svc.canonical_pair(asset1, asset2, delimiter)}


@router.get("/split")
def split_pair(pair: str = Query(...)):
    svc = get_standardization_service()
    a1, a2 = svc.split_pair(pair)
    return {"asset1": a1, "asset2": a2}


@router.get("/binance")
def to_binance(asset: str = Query(...)):
    svc = get_standardization_service()
    return {"asset": asset, "binance_symbol": svc.to_binance(asset)}


@router.get("/coinglass")
def to_coinglass(asset: str = Query(...)):
    svc = get_standardization_service()
    return {"asset": asset, "coinglass_symbol": svc.to_coinglass(asset)}


@router.get("/yfi")
def to_yfinance(asset: str = Query(...)):
    svc = get_standardization_service()
    return {"asset": asset, "yfinance_symbol": svc.to_yfinance(asset)}
