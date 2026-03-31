"""
Crypto Market Data API Router

Endpoints for Binance and Coinglass data (prices, funding, OI, liquidations, etc.)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.binance_service import get_binance_service
from api.services.coinglass_service import get_coinglass_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crypto", tags=["crypto"])


# Response models
class PriceData(BaseModel):
    """Price data model."""

    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    quoteVolume: Optional[float] = None
    change: Optional[float] = None
    percentage: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    timestamp: Optional[int] = None
    fundingRate: Optional[float] = None


class FundingRateData(BaseModel):
    """Funding rate model."""

    symbol: str
    fundingRate: float
    fundingTimestamp: Optional[int] = None
    nextFundingTime: Optional[int] = None
    averageRate7d: Optional[float] = None


class OpenInterestData(BaseModel):
    """Open interest model."""

    symbol: str
    openInterest: float
    openInterestValue: Optional[float] = None
    timestamp: Optional[int] = None


class LiquidationData(BaseModel):
    """Liquidation data model."""

    symbol: str
    timeframe: str
    longLiquidations: float
    shortLiquidations: float
    totalLiquidations: float
    longLiquidationsPercent: Optional[float] = None
    shortLiquidationsPercent: Optional[float] = None


# Binance endpoints
@router.get("/price/{symbol}", response_model=PriceData)
async def get_price(symbol: str):
    """
    Get current price for a crypto symbol.

    Args:
        symbol: Trading pair (e.g., BTC/USDT, ETH/USDT)

    Returns:
        Current price data
    """
    try:
        binance = get_binance_service()
        data = await binance.get_price(symbol)

        if not data:
            raise HTTPException(status_code=404, detail=f"Price data not found for {symbol}")

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices", response_model=List[PriceData])
async def get_prices(
    symbols: Optional[str] = Query(
        None, description="Comma-separated list of symbols"
    )
):
    """
    Get prices for multiple symbols.

    Args:
        symbols: Comma-separated symbols (None = top 10 crypto)

    Returns:
        List of price data
    """
    try:
        binance = get_binance_service()

        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]

        data = await binance.get_market_overview(symbols=symbol_list)
        return data

    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funding/{symbol}", response_model=FundingRateData)
async def get_funding_rate(symbol: str):
    """
    Get funding rate for a symbol.

    Args:
        symbol: Trading pair (e.g., BTC/USDT)

    Returns:
        Funding rate data
    """
    try:
        binance = get_binance_service()
        data = await binance.get_funding_rate(symbol)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Funding rate not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching funding rate for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/openinterest/{symbol}", response_model=OpenInterestData)
async def get_open_interest(symbol: str):
    """
    Get open interest for a symbol.

    Args:
        symbol: Trading pair (e.g., BTC/USDT)

    Returns:
        Open interest data
    """
    try:
        binance = get_binance_service()
        data = await binance.get_open_interest(symbol)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Open interest not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching open interest for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orderbook/{symbol}")
async def get_order_book(
    symbol: str, limit: int = Query(20, ge=5, le=100, description="Order book depth")
):
    """
    Get order book for a symbol.

    Args:
        symbol: Trading pair (e.g., BTC/USDT)
        limit: Order book depth (5, 10, 20, 50, 100)

    Returns:
        Order book with bids and asks
    """
    try:
        binance = get_binance_service()
        data = await binance.get_order_book(symbol, limit=limit)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Order book not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order book for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gainers-losers")
async def get_gainers_losers(limit: int = Query(10, ge=5, le=50)):
    """
    Get top gainers and losers.

    Args:
        limit: Number of symbols per category

    Returns:
        Top gainers and losers
    """
    try:
        binance = get_binance_service()
        data = await binance.get_top_gainers_losers(limit=limit)
        return data

    except Exception as e:
        logger.error(f"Error fetching gainers/losers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Coinglass endpoints
@router.get("/liquidations/{symbol}", response_model=LiquidationData)
async def get_liquidations(
    symbol: str = "BTC",
    timeframe: str = Query("24h", description="Timeframe: 1h, 4h, 12h, 24h"),
):
    """
    Get liquidation data from Coinglass.

    Args:
        symbol: Symbol (BTC, ETH, etc.)
        timeframe: Timeframe for liquidations

    Returns:
        Liquidation data
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_liquidations(symbol=symbol, timeframe=timeframe)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Liquidation data not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching liquidations for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coinglass/openinterest/{symbol}")
async def get_coinglass_oi(symbol: str = "BTC"):
    """
    Get aggregated open interest from Coinglass.

    Args:
        symbol: Symbol (BTC, ETH, etc.)

    Returns:
        Aggregated OI across exchanges
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_open_interest(symbol=symbol)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"OI data not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Coinglass OI for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coinglass/funding/{symbol}")
async def get_coinglass_funding(symbol: str = "BTC"):
    """
    Get aggregated funding rates from Coinglass.

    Args:
        symbol: Symbol (BTC, ETH, etc.)

    Returns:
        Aggregated funding rates across exchanges
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_funding_rates(symbol=symbol)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Funding data not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Coinglass funding for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coinglass/longshort/{symbol}")
async def get_long_short_ratio(symbol: str = "BTC", exchange: str = "Binance"):
    """
    Get long/short account ratio from Coinglass.

    Args:
        symbol: Symbol (BTC, ETH, etc.)
        exchange: Exchange name

    Returns:
        Long/short ratio data
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_long_short_ratio(symbol=symbol, exchange=exchange)

        if not data:
            raise HTTPException(
                status_code=404, detail=f"Long/short data not found for {symbol}"
            )

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching long/short ratio for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fear-greed")
async def get_fear_greed():
    """
    Get crypto Fear & Greed index.

    Returns:
        Fear & Greed index data
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_fear_greed_index()

        if not data:
            raise HTTPException(status_code=404, detail="Fear & Greed data not found")

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Fear & Greed index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-metrics/{symbol}")
async def get_market_metrics(symbol: str = "BTC"):
    """
    Get comprehensive market metrics for a symbol.

    Includes: liquidations, OI, funding, long/short ratio, Fear & Greed.

    Args:
        symbol: Symbol (BTC, ETH, etc.)

    Returns:
        Comprehensive market metrics
    """
    try:
        coinglass = get_coinglass_service()
        data = await coinglass.get_market_metrics(symbol=symbol)
        return data

    except Exception as e:
        logger.error(f"Error fetching market metrics for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
