from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


class StandardizationService:
    """Centralized normalization and mapping service.

    Responsibilities:
    - Normalize pair keys (canonical order, delimiter)
    - Map assets to provider-specific tickers (Binance, Coinglass, YFinance)
    - Provide bi-directional conversions between internal asset codes and provider symbols
    - Validate and sanitize inputs
    """

    def __init__(self) -> None:
        # Simple in-memory mappings; in production, load from DB or config file
        # Internal code is upper snake without suffixes (e.g., BTC, ETH, SPY)
        self.binance_map: Dict[str, str] = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
            "SOL": "SOLUSDT",
            "AVAX": "AVAXUSDT",
            "ADA": "ADAUSDT",
            "DOT": "DOTUSDT",
        }
        self.coinglass_map: Dict[str, str] = {
            # Coinglass typically uses plain asset codes
            "BTC": "BTC",
            "ETH": "ETH",
            "SOL": "SOL",
            "AVAX": "AVAX",
            "ADA": "ADA",
            "DOT": "DOT",
        }
        self.yfi_map: Dict[str, str] = {
            # For equities/ETFs extend as needed
            "SPY": "SPY",
            "TLT": "TLT",
        }

    @staticmethod
    def _sanitize_asset(asset: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", asset).upper()

    def canonical_pair(self, asset1: str, asset2: str, delimiter: str = "-") -> str:
        a1 = self._sanitize_asset(asset1)
        a2 = self._sanitize_asset(asset2)
        # Lexicographic ordering to maintain canonical form
        ordered = tuple(sorted([a1, a2]))
        return f"{ordered[0]}{delimiter}{ordered[1]}"

    def split_pair(self, pair: str) -> Tuple[str, str]:
        parts = re.split(r"[-_/]", pair)
        if len(parts) != 2:
            raise ValueError(f"Invalid pair format: {pair}")
        a1, a2 = self._sanitize_asset(parts[0]), self._sanitize_asset(parts[1])
        # Re-apply canonical ordering
        ordered = tuple(sorted([a1, a2]))
        return ordered[0], ordered[1]

    def to_binance(self, asset: str) -> Optional[str]:
        return self.binance_map.get(self._sanitize_asset(asset))

    def from_binance(self, symbol: str) -> Optional[str]:
        # Reverse map
        rev = {v: k for k, v in self.binance_map.items()}
        return rev.get(symbol.upper())

    def to_coinglass(self, asset: str) -> Optional[str]:
        return self.coinglass_map.get(self._sanitize_asset(asset))

    def from_coinglass(self, symbol: str) -> Optional[str]:
        rev = {v: k for k, v in self.coinglass_map.items()}
        return rev.get(symbol.upper())

    def to_yfinance(self, asset: str) -> Optional[str]:
        return self.yfi_map.get(self._sanitize_asset(asset))


_std_service: Optional[StandardizationService] = None


def get_standardization_service() -> StandardizationService:
    global _std_service
    if _std_service is None:
        _std_service = StandardizationService()
    return _std_service
