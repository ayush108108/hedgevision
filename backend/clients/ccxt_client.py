"""
CCXT Client for crypto exchange data (Binance).

Provides unified interface for fetching crypto price data from Binance via CCXT.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import time

import pandas as pd
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT not available. Install with: pip install ccxt")
    ccxt = None


class CCXTClient:
    """
    CCXT client for fetching crypto data from Binance.

    Handles:
    - Real-time price data via REST API
    - Historical OHLCV data
    - Rate limiting and error handling
    """

    def __init__(self, exchange_id: str = 'binance'):
        if not CCXT_AVAILABLE:
            raise RuntimeError("CCXT not available. Install with: pip install ccxt")

        self.exchange_id = exchange_id
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Use futures for USDT-M pairs
            }
        })

        # Set API credentials if available
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        if api_key and api_secret:
            self.exchange.apiKey = api_key
            self.exchange.secret = api_secret

        self.rate_limit_delay = 0.1  # 100ms between requests

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1d',
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1d', '4h', '1h')
            since: Timestamp in milliseconds
            limit: Number of candles to fetch

        Returns:
            List of OHLCV data [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            # Convert symbol format if needed (BTC-USD -> BTC/USDT)
            ccxt_symbol = symbol.replace('-', '/')
            if not ccxt_symbol.endswith('/USDT'):
                ccxt_symbol = ccxt_symbol + ':USDT' if ':' not in ccxt_symbol else ccxt_symbol

            logger.info(f"Fetching {ccxt_symbol} {timeframe} data from {self.exchange_id}")

            # Fetch data
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, since, limit)
            )

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

            return ohlcv

        except Exception as e:
            logger.error(f"Error fetching {symbol} from {self.exchange_id}: {e}")
            return []

    def fetch_ohlcv_sync(
        self,
        symbol: str,
        timeframe: str = '1d',
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[List]:
        """
        Synchronous version of fetch_ohlcv.
        """
        try:
            # Convert symbol format
            ccxt_symbol = symbol.replace('-', '/')
            if not ccxt_symbol.endswith('/USDT'):
                ccxt_symbol = ccxt_symbol + ':USDT' if ':' not in ccxt_symbol else ccxt_symbol

            logger.info(f"Fetching {ccxt_symbol} {timeframe} data from {self.exchange_id}")

            ohlcv = self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, since, limit)

            # Rate limiting
            time.sleep(self.rate_limit_delay)

            return ohlcv

        except Exception as e:
            logger.error(f"Error fetching {symbol} from {self.exchange_id}: {e}")
            return []

    def convert_to_dataframe(self, ohlcv_data: List[List]) -> pd.DataFrame:
        """
        Convert CCXT OHLCV data to pandas DataFrame.

        Args:
            ohlcv_data: List of [timestamp, open, high, low, close, volume]

        Returns:
            DataFrame with datetime index and OHLCV columns
        """
        if not ohlcv_data:
            return pd.DataFrame()

        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def get_available_symbols(self) -> List[str]:
        """
        Get list of available trading pairs on the exchange.
        """
        try:
            markets = self.exchange.load_markets()
            return list(markets.keys())
        except Exception as e:
            logger.error(f"Error loading markets from {self.exchange_id}: {e}")
            return []


# Global client instance
_ccxt_client = None

def get_ccxt_client(exchange_id: str = 'binance') -> CCXTClient:
    """Get or create CCXT client instance."""
    global _ccxt_client
    if _ccxt_client is None or _ccxt_client.exchange_id != exchange_id:
        _ccxt_client = CCXTClient(exchange_id)
    return _ccxt_client