"""
Coinglass API Integration Service

Provides on-chain and derivatives market data including:
- Liquidation data (long/short liquidations)
- Open interest across exchanges
- Funding rates aggregated
- Long/short ratio
- Fear & Greed index
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
import os

import aiohttp

logger = logging.getLogger(__name__)


class CoinglassService:
    """
    Coinglass API integration for advanced crypto market metrics.

    Requires Coinglass API key (get from https://www.coinglass.com/pricing)
    """

    BASE_URL = "https://open-api.coinglass.com/public/v2"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Coinglass service.

        Args:
            api_key: Coinglass API key (or use COINGLASS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("COINGLASS_API_KEY")
        if not self.api_key:
            logger.warning(
                "Coinglass API key not provided - service will return mock data"
            )

        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make API request to Coinglass.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data or None
        """
        if not self.api_key:
            logger.warning("Coinglass API key not configured - returning None")
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"coinglassSecret": self.api_key}

        try:
            session = await self._get_session()
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(
                        f"Coinglass API error: {response.status} - {await response.text()}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error making request to Coinglass: {e}")
            return None

    async def get_liquidations(
        self, symbol: str = "BTC", timeframe: str = "1h"
    ) -> Optional[Dict[str, Any]]:
        """
        Get liquidation data for a symbol.

        Args:
            symbol: Symbol (BTC, ETH, etc.)
            timeframe: Timeframe (1h, 4h, 12h, 24h)

        Returns:
            Dict with liquidation data
        """
        endpoint = "liquidation"
        params = {"symbol": symbol, "timeType": timeframe}

        data = await self._make_request(endpoint, params)

        if not data:
            # Return mock data if API not available
            return self._mock_liquidations(symbol, timeframe)

        return data

    async def get_open_interest(
        self, symbol: str = "BTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Get open interest aggregated across exchanges.

        Args:
            symbol: Symbol (BTC, ETH, etc.)

        Returns:
            Dict with open interest data
        """
        endpoint = "openInterest"
        params = {"symbol": symbol}

        data = await self._make_request(endpoint, params)

        if not data:
            return self._mock_open_interest(symbol)

        return data

    async def get_funding_rates(
        self, symbol: str = "BTC"
    ) -> Optional[Dict[str, Any]]:
        """
        Get funding rates aggregated across exchanges.

        Args:
            symbol: Symbol (BTC, ETH, etc.)

        Returns:
            Dict with funding rate data
        """
        endpoint = "fundingRate"
        params = {"symbol": symbol}

        data = await self._make_request(endpoint, params)

        if not data:
            return self._mock_funding_rates(symbol)

        return data

    async def get_long_short_ratio(
        self, symbol: str = "BTC", exchange: str = "Binance"
    ) -> Optional[Dict[str, Any]]:
        """
        Get long/short account ratio.

        Args:
            symbol: Symbol (BTC, ETH, etc.)
            exchange: Exchange name

        Returns:
            Dict with long/short ratio data
        """
        endpoint = "longShortRatio"
        params = {"symbol": symbol, "exchange": exchange}

        data = await self._make_request(endpoint, params)

        if not data:
            return self._mock_long_short_ratio(symbol)

        return data

    async def get_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """
        Get crypto Fear & Greed index.

        Returns:
            Dict with fear & greed index data
        """
        endpoint = "fearGreed"

        data = await self._make_request(endpoint)

        if not data:
            return self._mock_fear_greed()

        return data

    async def get_market_metrics(self, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Get comprehensive market metrics for a symbol.

        Args:
            symbol: Symbol (BTC, ETH, etc.)

        Returns:
            Dict with all available metrics
        """
        # Fetch all metrics concurrently
        liquidations_task = self.get_liquidations(symbol, "24h")
        oi_task = self.get_open_interest(symbol)
        funding_task = self.get_funding_rates(symbol)
        ls_ratio_task = self.get_long_short_ratio(symbol)
        fg_task = self.get_fear_greed_index()

        liquidations, oi, funding, ls_ratio, fg = await asyncio.gather(
            liquidations_task,
            oi_task,
            funding_task,
            ls_ratio_task,
            fg_task,
            return_exceptions=True,
        )

        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "liquidations": liquidations if not isinstance(liquidations, Exception) else None,
            "openInterest": oi if not isinstance(oi, Exception) else None,
            "fundingRates": funding if not isinstance(funding, Exception) else None,
            "longShortRatio": ls_ratio if not isinstance(ls_ratio, Exception) else None,
            "fearGreedIndex": fg if not isinstance(fg, Exception) else None,
        }

    # Mock data methods (used when API key not available)
    def _mock_liquidations(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate mock liquidation data."""
        import random

        long_liq = random.uniform(10000000, 50000000)
        short_liq = random.uniform(10000000, 50000000)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "longLiquidations": long_liq,
            "shortLiquidations": short_liq,
            "totalLiquidations": long_liq + short_liq,
            "longLiquidationsPercent": (long_liq / (long_liq + short_liq)) * 100,
            "shortLiquidationsPercent": (short_liq / (long_liq + short_liq)) * 100,
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data - Configure COINGLASS_API_KEY for real data",
        }

    def _mock_open_interest(self, symbol: str) -> Dict[str, Any]:
        """Generate mock open interest data."""
        import random

        return {
            "symbol": symbol,
            "totalOpenInterest": random.uniform(5e9, 15e9),
            "exchanges": [
                {"name": "Binance", "openInterest": random.uniform(2e9, 5e9)},
                {"name": "OKX", "openInterest": random.uniform(1e9, 3e9)},
                {"name": "Bybit", "openInterest": random.uniform(1e9, 3e9)},
                {"name": "Deribit", "openInterest": random.uniform(5e8, 2e9)},
            ],
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data - Configure COINGLASS_API_KEY for real data",
        }

    def _mock_funding_rates(self, symbol: str) -> Dict[str, Any]:
        """Generate mock funding rate data."""
        import random

        return {
            "symbol": symbol,
            "averageFundingRate": random.uniform(-0.001, 0.001),
            "exchanges": [
                {"name": "Binance", "fundingRate": random.uniform(-0.001, 0.001)},
                {"name": "OKX", "fundingRate": random.uniform(-0.001, 0.001)},
                {"name": "Bybit", "fundingRate": random.uniform(-0.001, 0.001)},
            ],
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data - Configure COINGLASS_API_KEY for real data",
        }

    def _mock_long_short_ratio(self, symbol: str) -> Dict[str, Any]:
        """Generate mock long/short ratio data."""
        import random

        long_accounts = random.uniform(45, 55)
        short_accounts = 100 - long_accounts

        return {
            "symbol": symbol,
            "longAccountsPercent": long_accounts,
            "shortAccountsPercent": short_accounts,
            "longShortRatio": long_accounts / short_accounts,
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data - Configure COINGLASS_API_KEY for real data",
        }

    def _mock_fear_greed(self) -> Dict[str, Any]:
        """Generate mock fear & greed index."""
        import random

        value = random.randint(20, 80)
        if value < 25:
            classification = "Extreme Fear"
        elif value < 45:
            classification = "Fear"
        elif value < 55:
            classification = "Neutral"
        elif value < 75:
            classification = "Greed"
        else:
            classification = "Extreme Greed"

        return {
            "value": value,
            "classification": classification,
            "timestamp": datetime.now().isoformat(),
            "note": "Mock data - Configure COINGLASS_API_KEY for real data",
        }


# Global instance
_coinglass_service: Optional[CoinglassService] = None


def get_coinglass_service() -> CoinglassService:
    """Get or create global CoinglassService instance."""
    global _coinglass_service
    if _coinglass_service is None:
        _coinglass_service = CoinglassService()
    return _coinglass_service
