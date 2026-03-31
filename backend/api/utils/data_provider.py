"""
Data provider module for fetching market data.

This module provides utilities for fetching market data from
various sources and caching the results.
"""

import logging
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List, Union

import pandas as pd

# Add parent directory to path to import from parent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logger = logging.getLogger(__name__)


class DataProvider:
    """
    Data provider for fetching market data with caching.

    This class provides a simple interface for fetching market data
    and caching the results to avoid unnecessary API calls.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize the data provider.

        Args:
            db_path: Path to the SQLite database file for caching.
                    If None, will use '../prices.db' relative to this file.
        """
        if db_path is None:
            # Use the prices.db in the parent directory
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prices.db"
            )

        self.db_path = db_path
        logger.info(f"Initialized DataProvider with database: {db_path}")

    def get_daily_prices(
        self,
        symbols: List[str],
        start_date: Union[str, datetime, pd.Timestamp],
        end_date: Union[str, datetime, pd.Timestamp],
    ) -> pd.DataFrame:
        """
        Get daily price data for a list of symbols.

        Args:
            symbols: List of ticker symbols.
            start_date: Start date for the data.
            end_date: End date for the data.

        Returns:
            DataFrame with price data.
        """
        # Convert dates to datetime objects if they're strings
        if isinstance(start_date, str):
            start_date = pd.Timestamp(start_date)
        if isinstance(end_date, str):
            end_date = pd.Timestamp(end_date)

        # Format dates for SQLite query
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Create a connection to the database
        try:
            conn = sqlite3.connect(self.db_path)

            # Build query to fetch prices for all symbols
            symbols_str = ", ".join(f"'{s}'" for s in symbols)
            query = f"""
            SELECT date, symbol, close
            FROM daily_prices
            WHERE symbol IN ({symbols_str})
            AND date BETWEEN '{start_str}' AND '{end_str}'
            ORDER BY date, symbol
            """

            # Execute query and load results into DataFrame
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                logger.warning(f"No price data found for symbols {symbols}")
                return pd.DataFrame()

            # Pivot the DataFrame to have symbols as columns and dates as index
            price_df = df.pivot(index="date", columns="symbol", values="close")
            price_df.index = pd.to_datetime(price_df.index)

            logger.info(
                f"Retrieved prices for {len(symbols)} symbols from {start_str} to {end_str}"
            )
            return price_df

        except Exception as e:
            logger.error(f"Error fetching price data: {str(e)}", exc_info=True)
            return pd.DataFrame()

    def get_symbol_metadata(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for a list of symbols.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Dictionary mapping symbols to their metadata.
        """
        result = {}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for symbol in symbols:
                query = f"""
                SELECT 
                    symbol, 
                    name, 
                    exchange, 
                    sector, 
                    industry
                FROM 
                    symbols 
                WHERE 
                    symbol = '{symbol}'
                """

                cursor.execute(query)
                row = cursor.fetchone()

                if row:
                    result[symbol] = {
                        "symbol": row[0],
                        "name": row[1],
                        "exchange": row[2],
                        "sector": row[3],
                        "industry": row[4],
                    }
                else:
                    result[symbol] = {
                        "symbol": symbol,
                        "name": "Unknown",
                        "exchange": "Unknown",
                        "sector": "Unknown",
                        "industry": "Unknown",
                    }

            conn.close()

        except Exception as e:
            logger.error(f"Error fetching symbol metadata: {str(e)}", exc_info=True)

        return result
