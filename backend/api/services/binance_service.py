"""
Enhanced Binance and Crypto Market Data Service

Provides comprehensive crypto market data including:
- Real-time prices and OHLCV data via Binance API
- Funding rates and open interest
- Order book depth and liquidity metrics
- On-chain metrics integration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import os

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import ccxt

    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT not available. Install with: pip install ccxt")
    ccxt = None


class BinanceService:
    """Enhanced Binance integration with advanced metrics."""

    def __init__(self, testnet: bool = False):
        """
        Initialize Binance service.

        Args:
            testnet: Use testnet instead of mainnet
        """
        if not CCXT_AVAILABLE:
            raise RuntimeError("CCXT not available. Install with: pip install ccxt")

        self.testnet = testnet

        # Initialize Binance futures exchange
        self.exchange = ccxt.binance(
            {
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",  # Use USDT-M futures
                    "testnet": testnet,
                },
            }
        )

        # Set API credentials if available
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if api_key and api_secret:
            self.exchange.apiKey = api_key
            self.exchange.secret = api_secret
            logger.info("Binance API credentials loaded")
        else:
            logger.warning("Binance API credentials not found - some features limited")

        self.rate_limit_delay = 0.1  # 100ms between requests

    async def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Dict with price data or None
        """
        try:
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_ticker(symbol)
            )

            return {
                "symbol": symbol,
                "price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "volume": ticker["baseVolume"],
                "quoteVolume": ticker["quoteVolume"],
                "timestamp": ticker["timestamp"],
                "datetime": ticker["datetime"],
                "change": ticker.get("change"),
                "percentage": ticker.get("percentage"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
            }

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            limit: Number of candles
            since: Timestamp in milliseconds

        Returns:
            DataFrame with OHLCV data
        """
        try:
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.exchange.fetch_ohlcv(symbol, timeframe, since, limit),
            )

            if not ohlcv:
                return pd.DataFrame()

            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current and historical funding rates.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Dict with funding rate data or None
        """
        try:
            # Current funding rate
            funding_rate = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_funding_rate(symbol)
            )

            # Historical funding rates (last 7 days)
            now = int(datetime.now().timestamp() * 1000)
            since = now - (7 * 24 * 60 * 60 * 1000)

            funding_history = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.exchange.fetch_funding_rate_history(
                    symbol, since=since, limit=56
                ),  # 8 hour intervals for 7 days
            )

            # Calculate average funding rate
            if funding_history:
                rates = [f["fundingRate"] for f in funding_history]
                avg_rate = sum(rates) / len(rates)
            else:
                avg_rate = 0

            return {
                "symbol": symbol,
                "fundingRate": funding_rate.get("fundingRate", 0),
                "fundingTimestamp": funding_rate.get("fundingTimestamp"),
                "fundingDatetime": funding_rate.get("fundingDatetime"),
                "nextFundingTime": funding_rate.get("nextFundingTime"),
                "averageRate7d": avg_rate,
                "history": funding_history[-24:],  # Last 24 funding periods
            }

        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return None

    async def get_open_interest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get open interest data.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Dict with open interest data or None
        """
        try:
            # Fetch open interest
            oi = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_open_interest(symbol)
            )

            # Historical OI (last 30 days if available)
            try:
                now = int(datetime.now().timestamp() * 1000)
                since = now - (30 * 24 * 60 * 60 * 1000)

                oi_history = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.exchange.fetch_open_interest_history(
                        symbol, timeframe="1d", since=since, limit=30
                    ),
                )
            except Exception:
                oi_history = []

            return {
                "symbol": symbol,
                "openInterest": oi.get("openInterestAmount", 0),
                "openInterestValue": oi.get("openInterestValue", 0),
                "timestamp": oi.get("timestamp"),
                "datetime": oi.get("datetime"),
                "history": oi_history,
            }

        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return None

    async def get_order_book(
        self, symbol: str, limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Get order book depth.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            limit: Depth level (5, 10, 20, 50, 100, 500, 1000)

        Returns:
            Dict with order book data or None
        """
        try:
            order_book = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_order_book(symbol, limit)
            )

            # Calculate liquidity metrics
            bids = order_book["bids"][:limit]
            asks = order_book["asks"][:limit]

            bid_volume = sum([bid[1] for bid in bids])
            ask_volume = sum([ask[1] for ask in asks])
            total_volume = bid_volume + ask_volume

            # Calculate weighted mid price
            if bids and asks:
                best_bid = bids[0][0]
                best_ask = asks[0][0]
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
                spread_pct = (spread / mid_price) * 100
            else:
                mid_price = 0
                spread = 0
                spread_pct = 0

            return {
                "symbol": symbol,
                "timestamp": order_book["timestamp"],
                "datetime": order_book["datetime"],
                "bids": bids,
                "asks": asks,
                "midPrice": mid_price,
                "spread": spread,
                "spreadPercent": spread_pct,
                "bidVolume": bid_volume,
                "askVolume": ask_volume,
                "totalVolume": total_volume,
                "bidAskRatio": bid_volume / ask_volume if ask_volume > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return None

    async def get_liquidations(
        self, symbol: str, timeframe: str = "1h"
    ) -> Optional[Dict[str, Any]]:
        """
        Get liquidation data (if available).

        Note: Binance doesn't provide direct liquidation data via API.
        This is a placeholder for future Coinglass integration.

        Args:
            symbol: Trading pair
            timeframe: Timeframe for aggregation

        Returns:
            Dict with liquidation data or None
        """
        # This would be populated by Coinglass service
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "longLiquidations": 0,
            "shortLiquidations": 0,
            "totalLiquidations": 0,
            "note": "Use Coinglass service for detailed liquidation data",
        }

    async def get_market_overview(
        self, symbols: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get market overview for multiple symbols.

        Args:
            symbols: List of symbols (None = top symbols)

        Returns:
            List of market data for each symbol
        """
        if symbols is None:
            # Default top crypto pairs
            symbols = [
                "BTC/USDT",
                "ETH/USDT",
                "BNB/USDT",
                "SOL/USDT",
                "XRP/USDT",
                "ADA/USDT",
                "AVAX/USDT",
                "DOGE/USDT",
                "DOT/USDT",
                "MATIC/USDT",
            ]

        results = []
        for symbol in symbols:
            try:
                price_data = await self.get_price(symbol)
                if price_data:
                    # Add funding rate if available
                    try:
                        funding = await self.get_funding_rate(symbol)
                        price_data["fundingRate"] = funding.get("fundingRate", 0) if funding else 0
                    except Exception:
                        price_data["fundingRate"] = 0

                    results.append(price_data)

                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Error fetching overview for {symbol}: {e}")

        return results

    async def get_top_gainers_losers(
        self, limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get top gainers and losers.

        Args:
            limit: Number of symbols per category

        Returns:
            Dict with 'gainers' and 'losers' lists
        """
        try:
            # Fetch all USDT perpetual tickers
            tickers = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.exchange.fetch_tickers()
            )

            # Filter USDT pairs and calculate percentage change
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if "/USDT" in symbol and ticker.get("percentage") is not None:
                    usdt_pairs.append(
                        {
                            "symbol": symbol,
                            "price": ticker["last"],
                            "change": ticker.get("change", 0),
                            "percentage": ticker.get("percentage", 0),
                            "volume": ticker.get("quoteVolume", 0),
                        }
                    )

            # Sort by percentage change
            gainers = sorted(
                usdt_pairs, key=lambda x: x["percentage"], reverse=True
            )[:limit]
            losers = sorted(usdt_pairs, key=lambda x: x["percentage"])[:limit]

            return {"gainers": gainers, "losers": losers}

        except Exception as e:
            logger.error(f"Error fetching gainers/losers: {e}")
            return {"gainers": [], "losers": []}


# Global instance
_binance_service: Optional[BinanceService] = None


def get_binance_service(testnet: bool = False) -> BinanceService:
    """Get or create global BinanceService instance."""
    global _binance_service
    if _binance_service is None:
        _binance_service = BinanceService(testnet=testnet)
    return _binance_service
