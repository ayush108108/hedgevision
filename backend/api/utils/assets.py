"""
Asset data for the financial dashboard application.
Centralizes all asset-related constants used throughout the application.
"""

from typing import Dict, List, Set, Tuple

# Asset categories organized by sector (using descriptive display names)
asset_sectors: Dict[str, List[str]] = {
    "US Stocks": [
        "Apple",
        "Microsoft",
        "Tesla",
        "NVIDIA",
        "Meta Platforms",
        "Alphabet",
        "Amazon",
        "Netflix",
        "MicroStrategy",
        "C3.ai",
    ],
    "US ETFs": [
        "S&P 500 ETF",
        "Nasdaq 100 ETF",
        "Dow Jones ETF",
        "7-10Y Treasury ETF",
        "20Y+ Treasury ETF",
        "1-3Y Treasury ETF",
        "Tech Sector ETF",
        "Financials Sector ETF",
        "Energy Sector ETF",
        "Cons. Disc. Sector ETF",
        "Cons. Staples Sector ETF",
        "Industrials Sector ETF",
        "Healthcare Sector ETF",
        "Materials Sector ETF",
        "Utilities Sector ETF",
        "US REIT Sector ETF",
        "VIX Volatility Proxy ETF",
        "US TIPS Inflation ETF",
        "US Dollar Index ETF",
    ],
    "Global ETFs": [
        "Emerging Markets ETF",
        "China ETF",
        "Japan ETF",
        "Europe ETF",
        "Gold ETF",
        "Silver ETF",
        "Crude Oil ETF",
        "Steel/Mining ETF",
    ],
    "Forex Pairs": ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF"],
    "Crypto": ["Bitcoin", "Ethereum", "Solana", "XRP"],
    "India Market Proxies": ["NIFTY 50 ETF", "Sensex 30 ETF"],
    "ADRs": ["Infosys ADR", "HDFC Bank ADR"],
}

# Mapping from display names to API tickers (Using EODHD format)
# Used by business logic to get ticker from UI selection
name_to_symbol: Dict[str, str] = {
    # US Stocks
    "Apple": "AAPL.US",
    "Microsoft": "MSFT.US",
    "Tesla": "TSLA.US",
    "NVIDIA": "NVDA.US",
    "Meta Platforms": "META.US",
    "Alphabet": "GOOGL.US",
    "Amazon": "AMZN.US",
    "Netflix": "NFLX.US",
    "MicroStrategy": "MSTR.US",
    "C3.ai": "AI.US",
    # US ETFs
    "S&P 500 ETF": "SPY.US",
    "Nasdaq 100 ETF": "QQQ.US",
    "Dow Jones ETF": "DIA.US",
    "7-10Y Treasury ETF": "IEF.US",
    "20Y+ Treasury ETF": "TLT.US",
    "1-3Y Treasury ETF": "SHY.US",
    "Tech Sector ETF": "XLK.US",
    "Financials Sector ETF": "XLF.US",
    "Energy Sector ETF": "XLE.US",
    "Cons. Disc. Sector ETF": "XLY.US",
    "Cons. Staples Sector ETF": "XLP.US",
    "Industrials Sector ETF": "XLI.US",
    "Healthcare Sector ETF": "XLV.US",
    "Materials Sector ETF": "XLB.US",
    "Utilities Sector ETF": "XLU.US",
    "US REIT Sector ETF": "VNQ.US",
    "VIX Volatility Proxy ETF": "VXX.US",
    "US TIPS Inflation ETF": "TIP.US",
    "US Dollar Index ETF": "UUP.US",
    # Global ETFs (Assuming US listed)
    "Emerging Markets ETF": "EEM.US",
    "China ETF": "FXI.US",
    "Japan ETF": "EWJ.US",
    "Europe ETF": "FEZ.US",
    "Gold ETF": "GLD.US",
    "Silver ETF": "SLV.US",
    "Crude Oil ETF": "USO.US",
    "Steel/Mining ETF": "SLX.US",
    # Forex Pairs (Tentative format)
    "EUR/USD": "EURUSD.FOREX",
    "USD/JPY": "USDJPY.FOREX",
    "GBP/USD": "GBPUSD.FOREX",
    "AUD/USD": "AUDUSD.FOREX",
    "USD/CHF": "USDCHF.FOREX",
    # Crypto
    "Bitcoin": "BTC-USD.CC",
    "Ethereum": "ETH-USD.CC",
    "Solana": "SOL-USD.CC",
    "XRP": "XRP-USD.CC",
    # India Market Proxies (NSE tickers)
    "NIFTY 50 ETF": "SETFNIF50.NSE",
    "Sensex 30 ETF": "SENSEXIETF.NSE",
    # ADRs (Assuming US listed)
    "Infosys ADR": "INFY.US",
    "HDFC Bank ADR": "HDB.US",
}

# Mapping from API tickers (EODHD format) to display names
# Used for validation and potentially logging
symbol_to_name: Dict[str, str] = {
    # US Stocks
    "AAPL.US": "Apple",
    "MSFT.US": "Microsoft",
    "TSLA.US": "Tesla",
    "NVDA.US": "NVIDIA",
    "META.US": "Meta Platforms",
    "GOOGL.US": "Alphabet",
    "AMZN.US": "Amazon",
    "NFLX.US": "Netflix",
    "MSTR.US": "MicroStrategy",
    "AI.US": "C3.ai",
    # US ETFs
    "SPY.US": "S&P 500 ETF",
    "QQQ.US": "Nasdaq 100 ETF",
    "DIA.US": "Dow Jones ETF",
    "IEF.US": "7-10Y Treasury ETF",
    "TLT.US": "20Y+ Treasury ETF",
    "SHY.US": "1-3Y Treasury ETF",
    "XLK.US": "Tech Sector ETF",
    "XLF.US": "Financials Sector ETF",
    "XLE.US": "Energy Sector ETF",
    "XLY.US": "Cons. Disc. Sector ETF",
    "XLP.US": "Cons. Staples Sector ETF",
    "XLI.US": "Industrials Sector ETF",
    "XLV.US": "Healthcare Sector ETF",
    "XLB.US": "Materials Sector ETF",
    "XLU.US": "Utilities Sector ETF",
    "VNQ.US": "US REIT Sector ETF",
    "VXX.US": "VIX Volatility Proxy ETF",
    "TIP.US": "US TIPS Inflation ETF",
    "UUP.US": "US Dollar Index ETF",
    # Global ETFs
    "EEM.US": "Emerging Markets ETF",
    "FXI.US": "China ETF",
    "EWJ.US": "Japan ETF",
    "FEZ.US": "Europe ETF",
    "GLD.US": "Gold ETF",
    "SLV.US": "Silver ETF",
    "USO.US": "Crude Oil ETF",
    "SLX.US": "Steel/Mining ETF",
    # Forex Pairs
    "EURUSD.FOREX": "EUR/USD",
    "USDJPY.FOREX": "USD/JPY",
    "GBPUSD.FOREX": "GBP/USD",
    "AUDUSD.FOREX": "AUD/USD",
    "USDCHF.FOREX": "USD/CHF",
    # Crypto
    "BTC-USD.CC": "Bitcoin",
    "ETH-USD.CC": "Ethereum",
    "SOL-USD.CC": "Solana",
    "XRP-USD.CC": "XRP",
    # India Market Proxies
    "SETFNIF50.NSE": "NIFTY 50 ETF",
    "SENSEXIETF.NSE": "Sensex 30 ETF",
    # ADRs
    "INFY.US": "Infosys ADR",
    "HDB.US": "HDFC Bank ADR",
}


# Validate data consistency between mappings
def validate_mappings() -> Tuple[bool, Set[str]]:
    """
    Validates consistency between name_to_symbol and symbol_to_name mappings.

    Returns:
        Tuple containing:
        - Boolean indicating if mappings are consistent
        - Set of any inconsistent keys found
    """
    # Check if all names in name_to_symbol have corresponding entries in symbol_to_name
    inconsistencies = set()

    for name, symbol in name_to_symbol.items():
        if symbol not in symbol_to_name:
            inconsistencies.add(
                f"Symbol '{symbol}' from name_to_symbol not in symbol_to_name"
            )
        elif symbol_to_name[symbol] != name:
            inconsistencies.add(
                f"Mismatch: name_to_symbol['{name}'] = '{symbol}' but symbol_to_name['{symbol}'] = '{symbol_to_name[symbol]}'"
            )

    for symbol, name in symbol_to_name.items():
        if name not in name_to_symbol:
            inconsistencies.add(
                f"Name '{name}' from symbol_to_name not in name_to_symbol"
            )
        elif name_to_symbol[name] != symbol:
            inconsistencies.add(
                f"Mismatch: symbol_to_name['{symbol}'] = '{name}' but name_to_symbol['{name}'] = '{name_to_symbol[name]}'"
            )

    return len(inconsistencies) == 0, inconsistencies


# Run validation when module is imported
is_valid, issues = validate_mappings()
if not is_valid:
    import logging

    logger = logging.getLogger(__name__)
    for issue in issues:
        logger.warning(f"Asset mapping inconsistency: {issue}")


def get_all_symbols() -> List[str]:
    """Get all available asset symbols."""
    return list(name_to_symbol.values())


def get_all_names() -> List[str]:
    """Get all available asset names."""
    return list(name_to_symbol.keys())


def get_symbols_by_sector(sector: str) -> List[str]:
    """Get asset symbols for a specific sector."""
    if sector not in asset_sectors:
        return []

    symbols = []
    for name in asset_sectors[sector]:
        if name in name_to_symbol:
            symbols.append(name_to_symbol[name])

    return symbols


def get_sector_for_symbol(symbol: str) -> str:
    """Get the sector for a given symbol."""
    if symbol not in symbol_to_name:
        return "Unknown"

    name = symbol_to_name[symbol]
    for sector, names in asset_sectors.items():
        if name in names:
            return sector

    return "Unknown"
