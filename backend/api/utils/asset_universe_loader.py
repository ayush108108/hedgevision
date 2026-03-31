"""
Asset universe loader from YAML configuration.

Loads the master asset universe from config/asset_universe_master.yaml
and provides categorized asset lists for ingestion and logic services.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Set


# Mapping from yfinance ticker to display name for compatibility
TICKER_TO_NAME_MAPPING = {
    # Crypto Core
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum',
    'SOL-USD': 'Solana',
    'BNB-USD': 'BNB',
    'ADA-USD': 'Cardano',
    'XRP-USD': 'XRP',
    'AVAX-USD': 'Avalanche',
    'DOT-USD': 'Polkadot',
    'TRX-USD': 'TRON',
    'NEAR-USD': 'NEAR Protocol',
    'ATOM-USD': 'Cosmos',
    'SUI-USD': 'Sui',
    'APT-USD': 'Aptos',
    'SEI-USD': 'Sei',
    'TIA-USD': 'Celestia',
    'KAS-USD': 'Kaspa',
    'FTM-USD': 'Fantom',
    'INJ-USD': 'Injective',
    'HBAR-USD': 'Hedera',
    'ALGO-USD': 'Algorand',
    'ARB-USD': 'Arbitrum',
    'OP-USD': 'Optimism',
    'MATIC-USD': 'Polygon',
    'IMX-USD': 'Immutable X',
    'STRK-USD': 'Starknet',
    'MANTLE-USD': 'Mantle',
    'STX-USD': 'Stacks',
    'UNI-USD': 'Uniswap',
    'AAVE-USD': 'Aave',
    'MKR-USD': 'Maker',
    'LINK-USD': 'Chainlink',
    'SNX-USD': 'Synthetix',
    'CRV-USD': 'Curve DAO Token',
    'LDO-USD': 'Lido DAO',
    'DYDX-USD': 'dYdX',
    'GMX-USD': 'GMX',
    'JUP-USD': 'Jupiter',
    'RUNE-USD': 'THORChain',
    'PYTH-USD': 'Pyth Network',
    'ENA-USD': 'Ethena',
    'RNDR-USD': 'Render Token',
    'FET-USD': 'Fetch.ai',
    'AGIX-USD': 'SingularityNET',
    'GRT-USD': 'The Graph',
    'WLD-USD': 'Worldcoin',
    'OCEAN-USD': 'Ocean Protocol',
    'DOGE-USD': 'Dogecoin',
    'SHIB-USD': 'Shiba Inu',
    'PEPE-USD': 'Pepe',
    'WIF-USD': 'dogwifhat',
    'BONK-USD': 'Bonk',
    'FLOKI-USD': 'Floki',
    'LTC-USD': 'Litecoin',
    'BCH-USD': 'Bitcoin Cash',
    'ETC-USD': 'Ethereum Classic',
    'XLM-USD': 'Stellar',
    
    # Macro Monitor
    'SPY': 'S&P 500 ETF',
    'QQQ': 'Nasdaq 100 ETF',
    'IWM': 'Russell 2000 ETF',
    'NVDA': 'NVIDIA',
    'MSTR': 'MicroStrategy',
    'COIN': 'Coinbase Global',
    'VXX': 'VIX Volatility Proxy ETF',
    'EEM': 'Emerging Markets ETF',
    'KWEB': 'KraneShares CSI China Internet ETF',
    'GLD': 'Gold ETF',
    'SLV': 'Silver ETF',
    'USO': 'United States Oil Fund',
    'UNG': 'United States Natural Gas Fund',
    'DBA': 'Invesco Optimum Yield Diversified Commodity Strategy No K-1 ETF',
    'CPER': 'United States Copper Index Fund',
    'LIT': 'Global X Lithium & Battery Tech ETF',
    'UUP': 'US Dollar Index ETF',
    'FXE': 'Invesco CurrencyShares Euro Trust',
    'FXY': 'Invesco CurrencyShares Japanese Yen Trust',
    'TLT': '20Y+ Treasury ETF',
    'HYG': 'High Yield Corp Bond ETF',
    'USDT-USD': 'Tether',
    'USDC-USD': 'USD Coin',
    'ARKK': 'ARK Innovation ETF',
    'TSLA': 'Tesla',
    
    # Gap Assets
    'BTC=F': 'CME Bitcoin Futures',
    'ETH=F': 'CME Ether Futures',
    'ES=F': 'E-mini S&P 500 Futures',
    'NQ=F': 'E-mini Nasdaq 100 Futures',
    'GC=F': 'Gold Futures',
    'CL=F': 'Crude Oil Futures',
}


class AssetUniverseLoader:
    """Loads and provides access to the master asset universe configuration."""

    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config/asset_universe_master.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "asset_universe_master.yaml"

        self.config_path = Path(config_path)
        self._config = None

    @property
    def config(self) -> Dict:
        """Lazy load the configuration."""
        if self._config is None:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        return self._config

    def get_crypto_core_assets(self) -> List[str]:
        """Get all crypto core trading assets (Section A) as display names."""
        crypto_core = self.config.get('crypto_core', {})
        assets = []
        for category in crypto_core.values():
            for ticker in category:
                name = TICKER_TO_NAME_MAPPING.get(ticker, ticker)
                assets.append(name)
        return assets

    def get_macro_monitor_assets(self) -> List[str]:
        """Get all macro monitoring assets (Section B) as display names."""
        macro_monitor = self.config.get('macro_monitor', {})
        assets = []
        for category in macro_monitor.values():
            # Handle comments in YAML (strip after #)
            for asset in category:
                if isinstance(asset, str):
                    # Remove inline comments
                    ticker = asset.split('#')[0].strip()
                    if ticker:
                        name = TICKER_TO_NAME_MAPPING.get(ticker, ticker)
                        assets.append(name)
        return assets

    def get_crypto_core_tickers(self) -> List[str]:
        """Get all crypto core trading assets (Section A) as yfinance tickers."""
        crypto_core = self.config.get('crypto_core', {})
        assets = []
        for category in crypto_core.values():
            assets.extend(category)
        return assets

    def get_macro_monitor_tickers(self) -> List[str]:
        """Get all macro monitoring assets (Section B) as yfinance tickers."""
        macro_monitor = self.config.get('macro_monitor', {})
        assets = []
        for category in macro_monitor.values():
            # Handle comments in YAML (strip after #)
            for asset in category:
                if isinstance(asset, str):
                    # Remove inline comments
                    ticker = asset.split('#')[0].strip()
                    if ticker:
                        assets.append(ticker)
        return assets

    def get_gap_assets_tickers(self) -> List[str]:
        """Get all gap detection assets (Section C) as yfinance tickers."""
        gap_assets = self.config.get('gap_assets', {})
        assets = []
        for category in gap_assets.values():
            for asset in category:
                if isinstance(asset, str):
                    # Remove inline comments
                    ticker = asset.split('#')[0].strip()
                    if ticker:
                        assets.append(ticker)
        return assets

    def get_gap_assets(self) -> List[str]:
        """Get all gap detection assets (Section C) as display names."""
        gap_assets = self.config.get('gap_assets', {})
        assets = []
        for category in gap_assets.values():
            for asset in category:
                if isinstance(asset, str):
                    # Remove inline comments
                    ticker = asset.split('#')[0].strip()
                    if ticker:
                        name = TICKER_TO_NAME_MAPPING.get(ticker, ticker)
                        assets.append(name)
        return assets

    def get_all_trading_assets(self) -> List[str]:
        """Get all assets used for trading (crypto core)."""
        return self.get_crypto_core_assets()

    def get_all_monitoring_assets(self) -> List[str]:
        """Get all assets used for monitoring (macro + gap)."""
        return self.get_macro_monitor_assets() + self.get_gap_assets()

    def get_all_assets(self) -> List[str]:
        """Get all assets from all sections."""
        return self.get_crypto_core_assets() + self.get_macro_monitor_assets() + self.get_gap_assets()

    def get_crypto_core_by_category(self) -> Dict[str, List[str]]:
        """Get crypto core assets organized by category."""
        return self.config.get('crypto_core', {})

    def get_macro_monitor_by_category(self) -> Dict[str, List[str]]:
        """Get macro monitor assets organized by category."""
        macro = self.config.get('macro_monitor', {})
        # Clean comments
        cleaned = {}
        for key, assets in macro.items():
            cleaned[key] = []
            for asset in assets:
                if isinstance(asset, str):
                    asset = asset.split('#')[0].strip()
                    if asset:
                        cleaned[key].append(asset)
        return cleaned

    def get_gap_assets_by_category(self) -> Dict[str, List[str]]:
        """Get gap assets organized by category."""
        gap = self.config.get('gap_assets', {})
        # Clean comments
        cleaned = {}
        for key, assets in gap.items():
            cleaned[key] = []
            for asset in assets:
                if isinstance(asset, str):
                    asset = asset.split('#')[0].strip()
                    if asset:
                        cleaned[key].append(asset)
        return cleaned


# Global instance for easy access
asset_universe = AssetUniverseLoader()


def get_crypto_core_assets() -> List[str]:
    """Convenience function to get crypto core assets (names)."""
    return asset_universe.get_crypto_core_assets()


def get_macro_monitor_assets() -> List[str]:
    """Convenience function to get macro monitor assets (names)."""
    return asset_universe.get_macro_monitor_assets()


def get_gap_assets() -> List[str]:
    """Convenience function to get gap assets (names)."""
    return asset_universe.get_gap_assets()


def get_crypto_core_tickers() -> List[str]:
    """Convenience function to get crypto core tickers."""
    return asset_universe.get_crypto_core_tickers()


def get_macro_monitor_tickers() -> List[str]:
    """Convenience function to get macro monitor tickers."""
    return asset_universe.get_macro_monitor_tickers()


def get_gap_assets_tickers() -> List[str]:
    """Convenience function to get gap assets tickers."""
    return asset_universe.get_gap_assets_tickers()


def get_all_trading_assets() -> List[str]:
    """Convenience function to get all trading assets (names)."""
    return asset_universe.get_all_trading_assets()


def get_all_monitoring_assets() -> List[str]:
    """Convenience function to get all monitoring assets (names)."""
    return asset_universe.get_all_monitoring_assets()


def get_all_assets() -> List[str]:
    """Convenience function to get all assets (names)."""
    return asset_universe.get_all_assets()